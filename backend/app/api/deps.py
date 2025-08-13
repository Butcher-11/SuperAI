from typing import Generator, Optional
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.models.user import UserResponse
from app.services.auth_service import auth_service
from app.db.redis import check_rate_limit
from app.core.config import settings

# Security scheme
security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> UserResponse:
    """Get current authenticated user"""
    return await auth_service.get_current_user(credentials.credentials)

async def get_current_active_user(
    current_user: UserResponse = Depends(get_current_user)
) -> UserResponse:
    """Get current active user"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user"
        )
    return current_user

async def rate_limit_check(
    x_forwarded_for: Optional[str] = Header(None),
    current_user: UserResponse = Depends(get_current_active_user)
):
    """Rate limiting middleware"""
    # Use user ID as rate limit key
    rate_limit_key = f"rate_limit:user:{current_user.id}"
    
    # Check per-minute rate limit
    minute_check = await check_rate_limit(
        f"{rate_limit_key}:minute",
        settings.RATE_LIMIT_PER_MINUTE,
        60
    )
    
    if not minute_check["allowed"]:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded - too many requests per minute"
        )
    
    # Check per-hour rate limit
    hour_check = await check_rate_limit(
        f"{rate_limit_key}:hour",
        settings.RATE_LIMIT_PER_HOUR,
        3600
    )
    
    if not hour_check["allowed"]:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded - too many requests per hour"
        )

def get_team_member(
    current_user: UserResponse = Depends(get_current_active_user)
) -> UserResponse:
    """Ensure user is part of a team"""
    if not current_user.team_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User must be part of a team"
        )
    return current_user

def get_team_admin(
    current_user: UserResponse = Depends(get_team_member)
) -> UserResponse:
    """Ensure user is team admin"""
    if current_user.role not in ["admin", "owner"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user