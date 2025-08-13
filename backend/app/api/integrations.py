from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import RedirectResponse

from app.models.integration import (
    Integration, IntegrationCreate, IntegrationResponse, 
    IntegrationType, IntegrationStatus
)
from app.models.user import UserResponse
from app.services.integration_service import integration_service
from app.api.deps import get_current_active_user, rate_limit_check

router = APIRouter(prefix="/integrations", tags=["integrations"])

@router.get("/", response_model=List[IntegrationResponse])
async def get_integrations(
    current_user: UserResponse = Depends(get_current_active_user)
):
    """Get user's integrations"""
    integrations = await integration_service.get_user_integrations(current_user.id)
    
    return [
        IntegrationResponse(
            id=integration["id"],
            integration_type=integration["integration_type"],
            name=integration["name"],
            status=integration["status"],
            settings=integration.get("settings", {}),
            scopes=integration.get("scopes", []),
            external_user_id=integration.get("external_user_id"),
            last_sync=integration.get("last_sync"),
            sync_enabled=integration.get("sync_enabled", True),
            created_at=integration["created_at"]
        )
        for integration in integrations
    ]

@router.get("/available")
async def get_available_integrations():
    """Get list of available integrations"""
    from app.models.integration import INTEGRATION_CONFIGS
    
    return [
        {
            "type": integration_type.value,
            "name": config["name"],
            "capabilities": config["capabilities"],
            "webhook_events": config["webhook_events"]
        }
        for integration_type, config in INTEGRATION_CONFIGS.items()
    ]

@router.post("/connect/{integration_type}")
async def connect_integration(
    integration_type: IntegrationType,
    redirect_uri: str = Query(..., description="OAuth redirect URI"),
    current_user: UserResponse = Depends(get_current_active_user)
):
    """Initiate OAuth connection for integration"""
    try:
        oauth_url = await integration_service.initiate_oauth(
            user_id=current_user.id,
            integration_type=integration_type,
            redirect_uri=redirect_uri
        )
        
        return {"oauth_url": oauth_url}
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/oauth/callback")
async def oauth_callback(
    code: str = Query(..., description="OAuth authorization code"),
    state: str = Query(..., description="OAuth state parameter")
):
    """Handle OAuth callback"""
    try:
        result = await integration_service.complete_oauth(code, state)
        return result
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth callback failed: {str(e)}"
        )

@router.post("/execute")
async def execute_integration_action(
    integration_type: IntegrationType,
    action: str,
    parameters: Dict[str, Any],
    current_user: UserResponse = Depends(get_current_active_user),
    _: None = Depends(rate_limit_check)
):
    """Execute action on integration"""
    try:
        result = await integration_service.execute_action(
            user_id=current_user.id,
            integration_type=integration_type,
            action=action,
            parameters=parameters
        )
        
        return {"result": result}
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Action execution failed: {str(e)}"
        )

@router.delete("/{integration_id}")
async def delete_integration(
    integration_id: str,
    current_user: UserResponse = Depends(get_current_active_user)
):
    """Delete integration"""
    success = await integration_service.delete_integration(current_user.id, integration_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    return {"message": "Integration deleted successfully"}