import json
from typing import Dict, List, Any, Optional
import httpx
from datetime import datetime

from app.core.config import settings
from app.models.workflow import Workflow, WorkflowExecution, WorkflowStep, ActionType, ExecutionStatus, TriggerType
from app.db.mongodb import get_database

class N8NService:
    def __init__(self):
        self.base_url = settings.N8N_BASE_URL
        self.api_key = settings.N8N_API_KEY
        self.webhook_url = settings.N8N_WEBHOOK_URL
        self.db = get_database()
        
        self.http_client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {self.api_key}"} if self.api_key else {},
            timeout=30.0
        )
    
    async def create_n8n_workflow(self, workflow: Workflow) -> str:
        """Create workflow in n8n and return n8n workflow ID"""
        n8n_workflow_data = self._convert_to_n8n_format(workflow)
        
        try:
            response = await self.http_client.post("/api/v1/workflows", json=n8n_workflow_data)
            response.raise_for_status()
            
            result = response.json()
            n8n_workflow_id = result["data"]["id"]
            
            # Activate the workflow
            await self._activate_n8n_workflow(n8n_workflow_id)
            
            return str(n8n_workflow_id)
        except Exception as e:
            raise Exception(f"Failed to create n8n workflow: {str(e)}")
    
    def _convert_to_n8n_format(self, workflow: Workflow) -> Dict[str, Any]:
        """Convert Loki workflow to n8n format"""
        nodes = []
        connections = {}
        
        # Create trigger node
        trigger_node = self._create_trigger_node(workflow.trigger_type, workflow.trigger_config)
        nodes.append(trigger_node)
        
        # Create step nodes
        previous_node = trigger_node["name"]
        for i, step in enumerate(workflow.steps):
            step_node = self._create_step_node(step, i)
            nodes.append(step_node)
            
            # Connect to previous node
            if previous_node not in connections:
                connections[previous_node] = {"main": [[]]}
            
            connections[previous_node]["main"][0].append({
                "node": step_node["name"],
                "type": "main",
                "index": 0
            })
            
            previous_node = step_node["name"]
        
        return {
            "name": workflow.name,
            "active": True,
            "nodes": nodes,
            "connections": connections,
            "settings": {
                "executionOrder": "v1"
            },
            "tags": workflow.tags
        }
    
    def _create_trigger_node(self, trigger_type: TriggerType, trigger_config: Dict[str, Any]) -> Dict[str, Any]:
        """Create n8n trigger node based on trigger type"""
        if trigger_type == TriggerType.WEBHOOK:
            return {
                "parameters": {
                    "httpMethod": trigger_config.get("method", "POST"),
                    "path": trigger_config.get("path", "webhook"),
                    "responseMode": "responseNode",
                    "options": {}
                },
                "id": "trigger-webhook",
                "name": "Webhook Trigger",
                "type": "n8n-nodes-base.webhook",
                "typeVersion": 1,
                "position": [250, 300]
            }
        elif trigger_type == TriggerType.SCHEDULE:
            return {
                "parameters": {
                    "rule": {
                        "interval": trigger_config.get("interval", [{"field": "cronExpression", "expression": "0 9 * * *"}])
                    }
                },
                "id": "trigger-schedule",
                "name": "Schedule Trigger",
                "type": "n8n-nodes-base.cron",
                "typeVersion": 1,
                "position": [250, 300]
            }
        else:
            # Manual trigger
            return {
                "parameters": {},
                "id": "trigger-manual",
                "name": "Manual Trigger",
                "type": "n8n-nodes-base.manualTrigger",
                "typeVersion": 1,
                "position": [250, 300]
            }
    
    def _create_step_node(self, step: WorkflowStep, index: int) -> Dict[str, Any]:
        """Create n8n node for workflow step"""
        node_id = f"step-{index}-{step.id}"
        position_y = 300 + (index + 1) * 180
        
        if step.action_type == ActionType.API_CALL:
            return {
                "parameters": {
                    "url": step.config.get("url", ""),
                    "requestMethod": step.config.get("method", "GET"),
                    "sendHeaders": True,
                    "headerParameters": {
                        "parameters": step.config.get("headers", [])
                    },
                    "sendBody": step.config.get("method", "GET") in ["POST", "PUT", "PATCH"],
                    "bodyParameters": {
                        "parameters": step.config.get("body", [])
                    }
                },
                "id": node_id,
                "name": step.name,
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 4.1,
                "position": [450, position_y]
            }
        elif step.action_type == ActionType.INTEGRATION_ACTION:
            return self._create_integration_node(step, node_id, position_y)
        elif step.action_type == ActionType.AI_PROCESS:
            return {
                "parameters": {
                    "model": step.config.get("model", "gpt-4"),
                    "messages": {
                        "values": [
                            {
                                "role": "user",
                                "content": step.config.get("prompt", "")
                            }
                        ]
                    }
                },
                "id": node_id,
                "name": step.name,
                "type": "n8n-nodes-base.openAi",
                "typeVersion": 1.3,
                "position": [450, position_y]
            }
        else:
            # Default function node for custom logic
            return {
                "parameters": {
                    "functionCode": step.config.get("code", "return items;")
                },
                "id": node_id,
                "name": step.name,
                "type": "n8n-nodes-base.function",
                "typeVersion": 1,
                "position": [450, position_y]
            }
    
    def _create_integration_node(self, step: WorkflowStep, node_id: str, position_y: int) -> Dict[str, Any]:
        """Create integration-specific n8n node"""
        integration_type = step.config.get("integration_type", "")
        
        if integration_type == "slack":
            return {
                "parameters": {
                    "authentication": "oAuth2",
                    "resource": "message",
                    "operation": step.config.get("operation", "post"),
                    "channel": step.config.get("channel", ""),
                    "text": step.config.get("text", "")
                },
                "id": node_id,
                "name": step.name,
                "type": "n8n-nodes-base.slack",
                "typeVersion": 2.1,
                "position": [450, position_y]
            }
        elif integration_type == "github":
            return {
                "parameters": {
                    "authentication": "oAuth2",
                    "resource": "issue",
                    "operation": step.config.get("operation", "create"),
                    "owner": step.config.get("owner", ""),
                    "repository": step.config.get("repository", ""),
                    "title": step.config.get("title", ""),
                    "body": step.config.get("body", "")
                },
                "id": node_id,
                "name": step.name,
                "type": "n8n-nodes-base.github",
                "typeVersion": 1.2,
                "position": [450, position_y]
            }
        else:
            # Generic HTTP request for other integrations
            return {
                "parameters": {
                    "url": step.config.get("url", ""),
                    "requestMethod": step.config.get("method", "POST")
                },
                "id": node_id,
                "name": step.name,
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 4.1,
                "position": [450, position_y]
            }
    
    async def _activate_n8n_workflow(self, n8n_workflow_id: str):
        """Activate n8n workflow"""
        try:
            await self.http_client.patch(
                f"/api/v1/workflows/{n8n_workflow_id}/activate",
                json={"active": True}
            )
        except Exception as e:
            raise Exception(f"Failed to activate n8n workflow: {str(e)}")
    
    async def execute_workflow(self, workflow_id: str, trigger_data: Dict[str, Any] = None) -> str:
        """Execute n8n workflow and return execution ID"""
        workflow_doc = await self.db.workflows.find_one({"id": workflow_id})
        if not workflow_doc:
            raise Exception("Workflow not found")
        
        workflow = Workflow(**workflow_doc)
        
        if not workflow.n8n_workflow_id:
            raise Exception("Workflow not deployed to n8n")
        
        try:
            response = await self.http_client.post(
                f"/api/v1/workflows/{workflow.n8n_workflow_id}/execute",
                json={"triggerData": trigger_data or {}}
            )
            response.raise_for_status()
            
            result = response.json()
            n8n_execution_id = result["data"]["id"]
            
            # Create execution record
            execution = WorkflowExecution(
                workflow_id=workflow_id,
                user_id=workflow.user_id,
                status=ExecutionStatus.RUNNING,
                trigger_data=trigger_data or {},
                n8n_execution_id=str(n8n_execution_id)
            )
            
            await self.db.workflow_executions.insert_one(execution.dict())
            
            return execution.id
        except Exception as e:
            raise Exception(f"Failed to execute n8n workflow: {str(e)}")
    
    async def get_execution_status(self, execution_id: str) -> Dict[str, Any]:
        """Get workflow execution status from n8n"""
        execution_doc = await self.db.workflow_executions.find_one({"id": execution_id})
        if not execution_doc:
            raise Exception("Execution not found")
        
        execution = WorkflowExecution(**execution_doc)
        
        if not execution.n8n_execution_id:
            return {"status": execution.status, "error": "No n8n execution ID"}
        
        try:
            response = await self.http_client.get(f"/api/v1/executions/{execution.n8n_execution_id}")
            response.raise_for_status()
            
            n8n_execution = response.json()["data"]
            
            # Map n8n status to our status
            status_mapping = {
                "running": ExecutionStatus.RUNNING,
                "success": ExecutionStatus.SUCCESS,
                "failed": ExecutionStatus.FAILED,
                "canceled": ExecutionStatus.CANCELLED,
                "waiting": ExecutionStatus.PENDING
            }
            
            our_status = status_mapping.get(n8n_execution["status"], ExecutionStatus.FAILED)
            
            # Update our execution record
            update_data = {
                "status": our_status,
                "step_results": n8n_execution.get("data", {}),
                "error_message": n8n_execution.get("error", "")
            }
            
            if n8n_execution.get("finishedAt"):
                update_data["completed_at"] = datetime.fromisoformat(n8n_execution["finishedAt"].replace("Z", "+00:00"))
                if execution.started_at and update_data["completed_at"]:
                    update_data["duration_seconds"] = (update_data["completed_at"] - execution.started_at).total_seconds()
            
            await self.db.workflow_executions.update_one(
                {"id": execution_id},
                {"$set": update_data}
            )
            
            return {
                "status": our_status,
                "step_results": n8n_execution.get("data", {}),
                "error_message": n8n_execution.get("error", ""),
                "started_at": execution.started_at.isoformat(),
                "completed_at": update_data.get("completed_at").isoformat() if update_data.get("completed_at") else None
            }
        except Exception as e:
            return {"status": ExecutionStatus.FAILED, "error": str(e)}
    
    async def delete_n8n_workflow(self, n8n_workflow_id: str):
        """Delete workflow from n8n"""
        try:
            await self.http_client.delete(f"/api/v1/workflows/{n8n_workflow_id}")
        except Exception as e:
            raise Exception(f"Failed to delete n8n workflow: {str(e)}")
    
    async def get_workflow_webhook_url(self, workflow_id: str) -> str:
        """Get webhook URL for workflow trigger"""
        workflow_doc = await self.db.workflows.find_one({"id": workflow_id})
        if not workflow_doc:
            raise Exception("Workflow not found")
        
        workflow = Workflow(**workflow_doc)
        
        if workflow.trigger_type != TriggerType.WEBHOOK:
            raise Exception("Workflow is not webhook-triggered")
        
        if not workflow.n8n_workflow_id:
            raise Exception("Workflow not deployed to n8n")
        
        # n8n webhook URL format
        webhook_path = workflow.trigger_config.get("path", "webhook")
        return f"{self.webhook_url}/webhook/{webhook_path}"

n8n_service = N8NService()