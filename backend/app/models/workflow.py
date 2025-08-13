from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from enum import Enum

class WorkflowStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"

class TriggerType(str, Enum):
    MANUAL = "manual"
    WEBHOOK = "webhook"
    SCHEDULE = "schedule"
    EVENT = "event"  # Integration event

class ActionType(str, Enum):
    API_CALL = "api_call"
    AI_PROCESS = "ai_process"
    DATA_TRANSFORM = "data_transform"
    NOTIFICATION = "notification"
    INTEGRATION_ACTION = "integration_action"

class ExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"

class WorkflowStep(BaseModel):
    id: str = Field(default_factory=lambda: __import__('uuid').uuid4().hex)
    name: str
    action_type: ActionType
    integration_id: Optional[str] = None  # Required for integration actions
    
    # Step configuration
    config: Dict[str, Any] = Field(default_factory=dict)
    input_mapping: Dict[str, str] = Field(default_factory=dict)
    output_mapping: Dict[str, str] = Field(default_factory=dict)
    
    # Execution settings
    timeout_seconds: int = 300
    retry_count: int = 0
    on_error: str = "stop"  # stop, continue, retry
    
    # Position in workflow
    order: int = 0
    depends_on: List[str] = Field(default_factory=list)  # Step IDs this depends on

class Workflow(BaseModel):
    id: str = Field(default_factory=lambda: __import__('uuid').uuid4().hex)
    user_id: str
    team_id: str
    name: str
    description: Optional[str] = None
    
    # Workflow configuration
    trigger_type: TriggerType
    trigger_config: Dict[str, Any] = Field(default_factory=dict)
    
    # Steps
    steps: List[WorkflowStep] = Field(default_factory=list)
    
    # n8n integration
    n8n_workflow_id: Optional[str] = None
    n8n_webhook_id: Optional[str] = None
    
    # Status and metadata
    status: WorkflowStatus = WorkflowStatus.DRAFT
    is_template: bool = False
    tags: List[str] = Field(default_factory=list)
    
    # Execution settings
    max_concurrent_executions: int = 1
    execution_timeout_minutes: int = 30
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class WorkflowExecution(BaseModel):
    id: str = Field(default_factory=lambda: __import__('uuid').uuid4().hex)
    workflow_id: str
    user_id: str
    
    # Execution details
    status: ExecutionStatus = ExecutionStatus.PENDING
    trigger_data: Dict[str, Any] = Field(default_factory=dict)
    
    # Results
    step_results: Dict[str, Any] = Field(default_factory=dict)  # step_id -> result
    output_data: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None
    
    # Timing
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    
    # n8n execution reference
    n8n_execution_id: Optional[str] = None

class WorkflowCreate(BaseModel):
    name: str
    description: Optional[str] = None
    trigger_type: TriggerType
    trigger_config: Dict[str, Any] = Field(default_factory=dict)

class WorkflowUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    trigger_config: Optional[Dict[str, Any]] = None
    status: Optional[WorkflowStatus] = None

class WorkflowResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    trigger_type: TriggerType
    trigger_config: Dict[str, Any]
    status: WorkflowStatus
    steps_count: int
    tags: List[str]
    created_at: datetime
    updated_at: datetime

class WorkflowExecutionResponse(BaseModel):
    id: str
    workflow_id: str
    status: ExecutionStatus
    started_at: datetime
    completed_at: Optional[datetime]
    duration_seconds: Optional[float]
    error_message: Optional[str]