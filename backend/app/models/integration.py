from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from enum import Enum

class IntegrationType(str, Enum):
    SLACK = "slack"
    GOOGLE = "google"
    GITHUB = "github"
    FIGMA = "figma"
    JIRA = "jira"
    NOTION = "notion"
    CONFLUENCE = "confluence"
    HUBSPOT = "hubspot"
    SALESFORCE = "salesforce"
    AWS = "aws"
    GREENHOUSE = "greenhouse"
    WORKDAY = "workday"
    AMAZON = "amazon"

class IntegrationStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    PENDING = "pending"

class Integration(BaseModel):
    id: str = Field(default_factory=lambda: __import__('uuid').uuid4().hex)
    user_id: str
    team_id: str
    integration_type: IntegrationType
    name: str  # User-defined name for this integration
    status: IntegrationStatus = IntegrationStatus.PENDING
    
    # OAuth tokens (encrypted)
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    expires_at: Optional[datetime] = None
    
    # Integration-specific settings
    settings: Dict[str, Any] = Field(default_factory=dict)
    scopes: List[str] = Field(default_factory=list)
    
    # Metadata
    external_user_id: Optional[str] = None
    external_workspace_id: Optional[str] = None
    
    # Sync status
    last_sync: Optional[datetime] = None
    sync_enabled: bool = True
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class IntegrationCreate(BaseModel):
    integration_type: IntegrationType
    name: str
    settings: Optional[Dict[str, Any]] = None

class IntegrationUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[IntegrationStatus] = None
    settings: Optional[Dict[str, Any]] = None
    sync_enabled: Optional[bool] = None

class IntegrationResponse(BaseModel):
    id: str
    integration_type: IntegrationType
    name: str
    status: IntegrationStatus
    settings: Dict[str, Any]
    scopes: List[str]
    external_user_id: Optional[str]
    last_sync: Optional[datetime]
    sync_enabled: bool
    created_at: datetime

class OAuthState(BaseModel):
    id: str = Field(default_factory=lambda: __import__('uuid').uuid4().hex)
    user_id: str
    integration_type: IntegrationType
    state: str
    redirect_uri: Optional[str] = None
    expires_at: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)

# Integration capabilities and permissions
INTEGRATION_CONFIGS = {
    IntegrationType.SLACK: {
        "name": "Slack",
        "oauth_scopes": ["channels:read", "chat:write", "users:read", "im:read", "im:write"],
        "capabilities": ["send_messages", "read_channels", "search_history"],
        "webhook_events": ["message", "channel_created", "member_joined"]
    },
    IntegrationType.GOOGLE: {
        "name": "Google Workspace",
        "oauth_scopes": ["https://www.googleapis.com/auth/gmail.modify", 
                        "https://www.googleapis.com/auth/calendar",
                        "https://www.googleapis.com/auth/drive"],
        "capabilities": ["gmail_access", "calendar_access", "drive_access"],
        "webhook_events": []
    },
    IntegrationType.GITHUB: {
        "name": "GitHub",
        "oauth_scopes": ["repo", "user", "write:discussion"],
        "capabilities": ["repo_access", "issue_management", "pr_management"],
        "webhook_events": ["push", "pull_request", "issues"]
    },
    IntegrationType.NOTION: {
        "name": "Notion",
        "oauth_scopes": ["read_content", "update_content", "insert_content"],
        "capabilities": ["page_access", "database_access", "block_operations"],
        "webhook_events": []
    }
}