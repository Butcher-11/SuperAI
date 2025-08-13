import asyncio
import json
from typing import Dict, List, Any, Optional, AsyncGenerator
from datetime import datetime
import httpx
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic

from app.core.config import settings
from app.models.chat import ThinkingMode, MessageRole
from app.models.integration import IntegrationType
from app.db.mongodb import get_database
from app.services.integration_service import integration_service

class AIService:
    def __init__(self):
        self.db = None
        self.openai_client = None
        self.anthropic_client = None
        self.emergent_client = None
        
        # Initialize clients based on available keys
        if settings.OPENAI_API_KEY:
            self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        
        if settings.ANTHROPIC_API_KEY:
            self.anthropic_client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        
        if settings.EMERGENT_LLM_KEY:
            self.emergent_client = self._init_emergent_client()
    
    def _get_db(self):
        if not self.db:
            self.db = get_database()
        return self.db
    
    def _init_emergent_client(self):
        """Initialize Emergent LLM client"""
        # This would integrate with Emergent's LLM service
        return httpx.AsyncClient(
            base_url="https://api.emergent.sh/v1",
            headers={"Authorization": f"Bearer {settings.EMERGENT_LLM_KEY}"}
        )
    
    async def process_message(
        self,
        user_id: str,
        conversation_id: str,
        message_content: str,
        thinking_mode: ThinkingMode = ThinkingMode.MEDIUM,
        model: str = "gpt-4"
    ) -> Dict[str, Any]:
        """Process user message and generate AI response"""
        
        # Get conversation context
        context = await self._get_conversation_context(conversation_id)
        
        # Get active integrations for the user
        active_integrations = await self._get_user_integrations(user_id)
        
        # Build system prompt based on integrations and context
        system_prompt = self._build_system_prompt(active_integrations, thinking_mode)
        
        # Prepare messages for AI
        messages = await self._prepare_messages(conversation_id, message_content, context)
        
        # Generate response based on model
        if model.startswith("gpt-") and self.openai_client:
            response = await self._generate_openai_response(messages, system_prompt, model, thinking_mode)
        elif model.startswith("claude-") and self.anthropic_client:
            response = await self._generate_anthropic_response(messages, system_prompt, model)
        elif self.emergent_client:
            response = await self._generate_emergent_response(messages, system_prompt, model)
        else:
            raise Exception("No AI client available")
        
        # Process tool calls if any
        if response.get("tool_calls"):
            tool_results = await self._execute_tool_calls(user_id, response["tool_calls"])
            response["tool_results"] = tool_results
        
        # Save messages to database
        await self._save_messages(conversation_id, message_content, response)
        
        return response
    
    async def _generate_openai_response(
        self, 
        messages: List[Dict],
        system_prompt: str,
        model: str,
        thinking_mode: ThinkingMode
    ) -> Dict[str, Any]:
        """Generate response using OpenAI"""
        
        # Configure model parameters based on thinking mode
        model_params = self._get_model_params(thinking_mode)
        
        # Add system message
        full_messages = [{"role": "system", "content": system_prompt}] + messages
        
        try:
            response = await self.openai_client.chat.completions.create(
                model=model,
                messages=full_messages,
                **model_params,
                tools=self._get_available_tools()
            )
            
            message = response.choices[0].message
            
            return {
                "content": message.content,
                "role": MessageRole.ASSISTANT,
                "tool_calls": [tool_call.dict() for tool_call in (message.tool_calls or [])],
                "model": model,
                "usage": response.usage.dict() if response.usage else None
            }
        except Exception as e:
            raise Exception(f"OpenAI API error: {str(e)}")
    
    async def _generate_anthropic_response(
        self,
        messages: List[Dict],
        system_prompt: str,
        model: str
    ) -> Dict[str, Any]:
        """Generate response using Anthropic"""
        try:
            response = await self.anthropic_client.messages.create(
                model=model,
                system=system_prompt,
                messages=messages,
                max_tokens=1024,
                tools=self._get_available_tools()
            )
            
            return {
                "content": response.content[0].text if response.content else "",
                "role": MessageRole.ASSISTANT,
                "tool_calls": [],
                "model": model,
                "usage": {"input_tokens": response.usage.input_tokens, "output_tokens": response.usage.output_tokens}
            }
        except Exception as e:
            raise Exception(f"Anthropic API error: {str(e)}")
    
    async def _generate_emergent_response(
        self,
        messages: List[Dict],
        system_prompt: str,
        model: str
    ) -> Dict[str, Any]:
        """Generate response using Emergent LLM"""
        try:
            payload = {
                "model": model,
                "messages": [{"role": "system", "content": system_prompt}] + messages,
                "tools": self._get_available_tools()
            }
            
            response = await self.emergent_client.post("/chat/completions", json=payload)
            response.raise_for_status()
            
            data = response.json()
            message = data["choices"][0]["message"]
            
            return {
                "content": message.get("content", ""),
                "role": MessageRole.ASSISTANT,
                "tool_calls": message.get("tool_calls", []),
                "model": model,
                "usage": data.get("usage")
            }
        except Exception as e:
            raise Exception(f"Emergent LLM API error: {str(e)}")
    
    def _get_model_params(self, thinking_mode: ThinkingMode) -> Dict[str, Any]:
        """Get model parameters based on thinking mode"""
        params = {
            ThinkingMode.QUICK: {
                "temperature": 0.3,
                "max_tokens": 512
            },
            ThinkingMode.MEDIUM: {
                "temperature": 0.7,
                "max_tokens": 1024
            },
            ThinkingMode.DEEP: {
                "temperature": 0.9,
                "max_tokens": 2048
            }
        }
        return params.get(thinking_mode, params[ThinkingMode.MEDIUM])
    
    def _build_system_prompt(self, integrations: List[Dict], thinking_mode: ThinkingMode) -> str:
        """Build system prompt based on user's integrations"""
        base_prompt = """You are Loki, an AI productivity assistant that helps users accomplish tasks across multiple integrated tools and platforms.

Your capabilities include:
- Analyzing and processing information across connected services
- Executing actions in integrated tools (Slack, Google Workspace, GitHub, etc.)
- Creating workflows and automations
- Providing insights and recommendations

"""
        
        if integrations:
            integration_names = [integration["integration_type"] for integration in integrations]
            base_prompt += f"\nYou currently have access to these integrations: {', '.join(integration_names)}\n"
            base_prompt += "You can perform actions in these tools when requested by the user.\n"
        
        thinking_mode_prompts = {
            ThinkingMode.QUICK: "Provide quick, concise responses. Focus on efficiency.",
            ThinkingMode.MEDIUM: "Provide balanced responses with sufficient detail and reasoning.",
            ThinkingMode.DEEP: "Provide thorough, comprehensive responses with detailed analysis and reasoning."
        }
        
        base_prompt += f"\nThinking mode: {thinking_mode_prompts[thinking_mode]}\n"
        
        return base_prompt
    
    def _get_available_tools(self) -> List[Dict[str, Any]]:
        """Get available tools based on integrations"""
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "execute_integration_action",
                    "description": "Execute an action in an integrated service",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "integration_type": {
                                "type": "string",
                                "enum": [integration.value for integration in IntegrationType],
                                "description": "The type of integration to use"
                            },
                            "action": {
                                "type": "string",
                                "description": "The action to perform"
                            },
                            "parameters": {
                                "type": "object",
                                "description": "Parameters for the action"
                            }
                        },
                        "required": ["integration_type", "action", "parameters"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "create_workflow",
                    "description": "Create a new workflow automation",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "Workflow name"},
                            "description": {"type": "string", "description": "Workflow description"},
                            "trigger_type": {"type": "string", "description": "How the workflow is triggered"},
                            "steps": {
                                "type": "array",
                                "description": "Workflow steps",
                                "items": {"type": "object"}
                            }
                        },
                        "required": ["name", "trigger_type", "steps"]
                    }
                }
            }
        ]
        
        return tools
    
    async def _execute_tool_calls(self, user_id: str, tool_calls: List[Dict]) -> List[Dict]:
        """Execute tool calls and return results"""
        results = []
        
        for tool_call in tool_calls:
            function_name = tool_call["function"]["name"]
            parameters = json.loads(tool_call["function"]["arguments"])
            
            try:
                if function_name == "execute_integration_action":
                    result = await integration_service.execute_action(
                        user_id,
                        parameters["integration_type"],
                        parameters["action"],
                        parameters["parameters"]
                    )
                elif function_name == "create_workflow":
                    # This would integrate with workflow service
                    result = {"status": "workflow_created", "id": "workflow_123"}
                else:
                    result = {"error": f"Unknown function: {function_name}"}
                
                results.append({
                    "tool_call_id": tool_call["id"],
                    "result": result
                })
            except Exception as e:
                results.append({
                    "tool_call_id": tool_call["id"],
                    "error": str(e)
                })
        
        return results
    
    async def _get_conversation_context(self, conversation_id: str) -> Dict[str, Any]:
        """Get conversation context"""
        conversation = await self.db.conversations.find_one({"id": conversation_id})
        return conversation.get("context", {}) if conversation else {}
    
    async def _get_user_integrations(self, user_id: str) -> List[Dict]:
        """Get user's active integrations"""
        integrations = await self.db.integrations.find({
            "user_id": user_id,
            "status": "active"
        }).to_list(100)
        return integrations
    
    async def _prepare_messages(
        self, 
        conversation_id: str, 
        new_message: str, 
        context: Dict
    ) -> List[Dict]:
        """Prepare message history for AI"""
        # Get recent messages from conversation
        messages = await self.db.messages.find(
            {"conversation_id": conversation_id}
        ).sort("created_at", 1).limit(20).to_list(20)
        
        formatted_messages = []
        for msg in messages:
            formatted_messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        # Add new user message
        formatted_messages.append({
            "role": "user",
            "content": new_message
        })
        
        return formatted_messages
    
    async def _save_messages(
        self, 
        conversation_id: str, 
        user_message: str, 
        ai_response: Dict
    ):
        """Save messages to database"""
        # Save user message
        user_msg = {
            "id": f"msg_{datetime.utcnow().timestamp()}",
            "conversation_id": conversation_id,
            "role": MessageRole.USER,
            "content": user_message,
            "tool_calls": [],
            "tool_results": [],
            "metadata": {},
            "created_at": datetime.utcnow()
        }
        
        # Save AI response
        ai_msg = {
            "id": f"msg_{datetime.utcnow().timestamp()}_ai",
            "conversation_id": conversation_id,
            "role": ai_response["role"],
            "content": ai_response["content"],
            "tool_calls": ai_response.get("tool_calls", []),
            "tool_results": ai_response.get("tool_results", []),
            "metadata": {
                "model": ai_response.get("model"),
                "usage": ai_response.get("usage")
            },
            "created_at": datetime.utcnow()
        }
        
        await self.db.messages.insert_many([user_msg, ai_msg])
        
        # Update conversation last activity
        await self.db.conversations.update_one(
            {"id": conversation_id},
            {"$set": {"last_activity": datetime.utcnow()}}
        )

ai_service = AIService()