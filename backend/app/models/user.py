from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, EmailStr
from enum import Enum

class UserRole(str, Enum):
    ADMIN = "admin"
    MEMBER = "member"
    GUEST = "guest"

class SubscriptionPlan(str, Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"

class User(BaseModel):
    id: str = Field(default_factory=lambda: __import__('uuid').uuid4().hex)
    email: EmailStr
    hashed_password: str
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    is_active: bool = True
    is_verified: bool = False
    team_id: Optional[str] = None
    role: UserRole = UserRole.MEMBER
    settings: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: Optional[str]
    avatar_url: Optional[str]
    is_active: bool
    is_verified: bool
    team_id: Optional[str]
    role: UserRole
    settings: Dict[str, Any]
    created_at: datetime
    last_login: Optional[datetime]

class Team(BaseModel):
    id: str = Field(default_factory=lambda: __import__('uuid').uuid4().hex)
    name: str
    description: Optional[str] = None
    owner_id: str
    subscription_plan: SubscriptionPlan = SubscriptionPlan.FREE
    settings: Dict[str, Any] = Field(default_factory=dict)
    limits: Dict[str, int] = Field(default_factory=lambda: {
        "max_members": 5,
        "max_integrations": 3,
        "max_workflows": 10,
        "max_ai_requests_per_month": 1000
    })
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class TeamCreate(BaseModel):
    name: str
    description: Optional[str] = None

class TeamResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    owner_id: str
    subscription_plan: SubscriptionPlan
    settings: Dict[str, Any]
    limits: Dict[str, int]
    created_at: datetime