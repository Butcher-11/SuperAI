from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from pydantic import BaseModel

from app.models.user import UserCreate, UserResponse
from app.services.auth_service import auth_service
from app.api.deps import get_current_active_user

router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer()

class LoginRequest(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    user: UserResponse

class RefreshTokenRequest(BaseModel):
    refresh_token: str

@router.post("/register", response_model=TokenResponse)
async def register(user_data: UserCreate):
    """Register new user"""
    user, tokens = await auth_service.register_user(user_data)
    
    return TokenResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_type=tokens["token_type"],
        expires_in=tokens["expires_in"],
        user=user
    )

@router.post("/login", response_model=TokenResponse)
async def login(login_data: LoginRequest):
    """Login user"""
    user, tokens = await auth_service.authenticate_user(login_data.email, login_data.password)
    
    return TokenResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_type=tokens["token_type"],
        expires_in=tokens["expires_in"],
        user=user
    )

@router.post("/refresh", response_model=dict)
async def refresh_token(refresh_data: RefreshTokenRequest):
    """Refresh access token"""
    tokens = await auth_service.refresh_token(refresh_data.refresh_token)
    return tokens

@router.post("/logout")
async def logout(current_user: UserResponse = Depends(get_current_active_user)):
    """Logout user"""
    await auth_service.logout_user(current_user.id)
    return {"message": "Successfully logged out"}

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: UserResponse = Depends(get_current_active_user)):
    """Get current user information"""
    return current_user