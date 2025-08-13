from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from enum import Enum

class ChatType(str, Enum):
    DIRECT = "direct"  # Direct user-AI chat
    TEAM = "team"      # Team chat with AI
    WORKFLOW = "workflow"  # Workflow-triggered conversation

class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant" 
    SYSTEM = "system"
    TOOL = "tool"

class ThinkingMode(str, Enum):
    QUICK = "quick"
    MEDIUM = "medium"
    DEEP = "deep"

class Conversation(BaseModel):
    id: str = Field(default_factory=lambda: __import__('uuid').uuid4().hex)
    user_id: str
    team_id: str
    chat_type: ChatType = ChatType.DIRECT
    title: str
    
    # AI Configuration
    thinking_mode: ThinkingMode = ThinkingMode.MEDIUM
    ai_model: str = "gpt-4"  # Default AI model
    
    # Context and memory
    context: Dict[str, Any] = Field(default_factory=dict)
    active_integrations: List[str] = Field(default_factory=list)  # Integration IDs
    
    # Metadata
    is_active: bool = True
    last_activity: datetime = Field(default_factory=datetime.utcnow)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class Message(BaseModel):
    id: str = Field(default_factory=lambda: __import__('uuid').uuid4().hex)
    conversation_id: str
    role: MessageRole
    content: str
    
    # Tool interactions
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)
    tool_results: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ConversationCreate(BaseModel):
    title: str
    chat_type: ChatType = ChatType.DIRECT
    thinking_mode: ThinkingMode = ThinkingMode.MEDIUM
    ai_model: str = "gpt-4"

class MessageCreate(BaseModel):
    content: str
    thinking_mode: Optional[ThinkingMode] = None

class ConversationResponse(BaseModel):
    id: str
    title: str
    chat_type: ChatType
    thinking_mode: ThinkingMode
    ai_model: str
    active_integrations: List[str]
    is_active: bool
    last_activity: datetime
    created_at: datetime

class MessageResponse(BaseModel):
    id: str
    role: MessageRole
    content: str
    tool_calls: List[Dict[str, Any]]
    tool_results: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    created_at: datetime

class ChatSession(BaseModel):
    """Real-time chat session data"""
    id: str = Field(default_factory=lambda: __import__('uuid').uuid4().hex)
    conversation_id: str
    user_id: str
    connection_id: str  # WebSocket connection ID
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)