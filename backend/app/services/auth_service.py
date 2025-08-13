from typing import Optional, Tuple
from datetime import datetime, timedelta
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.security import create_password_hash, verify_password, create_access_token, create_refresh_token, verify_token, generate_uuid
from app.models.user import User, UserCreate, UserResponse, Team, TeamCreate, UserRole
from app.db.mongodb import get_database
from app.db.redis import store_session, get_session, delete_session

class AuthService:
    def __init__(self):
        self.db = None
    
    def _get_db(self):
        if not self.db:
            self.db = get_database()
        return self.db
    
    async def register_user(self, user_data: UserCreate) -> Tuple[UserResponse, dict]:
        """Register new user and create default team"""
        db = self._get_db()
        # Check if user already exists
        existing_user = await db.users.find_one({"email": user_data.email})
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists"
            )
        
        # Create team first
        team = Team(
            name=f"{user_data.full_name or 'Personal'} Team",
            owner_id=generate_uuid()  # Temporary, will update after user creation
        )
        
        # Create user
        user = User(
            email=user_data.email,
            hashed_password=create_password_hash(user_data.password),
            full_name=user_data.full_name,
            team_id=team.id,
            role=UserRole.ADMIN
        )
        
        # Update team owner_id
        team.owner_id = user.id
        
        # Insert both documents
        await self.db.teams.insert_one(team.dict())
        await self.db.users.insert_one(user.dict())
        
        # Generate tokens
        tokens = await self._generate_user_tokens(user)
        
        return UserResponse(**user.dict()), tokens
    
    async def authenticate_user(self, email: str, password: str) -> Tuple[UserResponse, dict]:
        """Authenticate user and return tokens"""
        user_doc = await self.db.users.find_one({"email": email})
        if not user_doc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        user = User(**user_doc)
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is deactivated"
            )
        
        if not verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        # Update last login
        await self.db.users.update_one(
            {"id": user.id},
            {"$set": {"last_login": datetime.utcnow()}}
        )
        user.last_login = datetime.utcnow()
        
        # Generate tokens
        tokens = await self._generate_user_tokens(user)
        
        return UserResponse(**user.dict()), tokens
    
    async def refresh_token(self, refresh_token: str) -> dict:
        """Refresh access token"""
        payload = verify_token(refresh_token, "refresh")
        user_id = payload.get("sub")
        
        user_doc = await self.db.users.find_one({"id": user_id})
        if not user_doc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        user = User(**user_doc)
        return await self._generate_user_tokens(user)
    
    async def get_current_user(self, access_token: str) -> UserResponse:
        """Get current user from access token"""
        payload = verify_token(access_token, "access")
        user_id = payload.get("sub")
        
        user_doc = await self.db.users.find_one({"id": user_id})
        if not user_doc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        user = User(**user_doc)
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is deactivated"
            )
        
        return UserResponse(**user.dict())
    
    async def _generate_user_tokens(self, user: User) -> dict:
        """Generate access and refresh tokens"""
        access_token = create_access_token({"sub": user.id, "email": user.email})
        refresh_token = create_refresh_token({"sub": user.id})
        
        # Store session
        session_data = {
            "user_id": user.id,
            "team_id": user.team_id,
            "role": user.role,
            "created_at": datetime.utcnow().isoformat()
        }
        await store_session(user.id, session_data)
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": 1800  # 30 minutes
        }
    
    async def logout_user(self, user_id: str):
        """Logout user by clearing session"""
        await delete_session(user_id)
    
    async def get_user_team(self, user_id: str) -> Optional[dict]:
        """Get user's team information"""
        user_doc = await self.db.users.find_one({"id": user_id})
        if not user_doc or not user_doc.get("team_id"):
            return None
        
        team_doc = await self.db.teams.find_one({"id": user_doc["team_id"]})
        return team_doc

auth_service = AuthService()