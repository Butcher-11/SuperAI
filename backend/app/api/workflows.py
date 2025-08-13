from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status

from app.models.workflow import (
    WorkflowCreate, WorkflowUpdate, WorkflowResponse,
    WorkflowStep, WorkflowExecutionResponse
)
from app.models.user import UserResponse
from app.services.workflow_service import workflow_service
from app.api.deps import get_current_active_user, rate_limit_check

router = APIRouter(prefix="/workflows", tags=["workflows"])

@router.post("/", response_model=WorkflowResponse)
async def create_workflow(
    workflow_data: WorkflowCreate,
    current_user: UserResponse = Depends(get_current_active_user)
):
    """Create new workflow"""
    return await workflow_service.create_workflow(
        user_id=current_user.id,
        team_id=current_user.team_id or "",
        workflow_data=workflow_data
    )

@router.get("/", response_model=List[WorkflowResponse])
async def get_workflows(
    current_user: UserResponse = Depends(get_current_active_user)
):
    """Get user's workflows"""
    return await workflow_service.get_user_workflows(current_user.id)

@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(
    workflow_id: str,
    current_user: UserResponse = Depends(get_current_active_user)
):
    """Get workflow by ID"""
    workflow = await workflow_service.get_workflow(workflow_id, current_user.id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    return WorkflowResponse(
        id=workflow.id,
        name=workflow.name,
        description=workflow.description,
        trigger_type=workflow.trigger_type,
        trigger_config=workflow.trigger_config,
        status=workflow.status,
        steps_count=len(workflow.steps),
        tags=workflow.tags,
        created_at=workflow.created_at,
        updated_at=workflow.updated_at
    )

@router.put("/{workflow_id}", response_model=WorkflowResponse)
async def update_workflow(
    workflow_id: str,
    update_data: WorkflowUpdate,
    current_user: UserResponse = Depends(get_current_active_user)
):
    """Update workflow"""
    return await workflow_service.update_workflow(workflow_id, current_user.id, update_data)

@router.post("/{workflow_id}/steps")
async def add_workflow_step(
    workflow_id: str,
    step: WorkflowStep,
    current_user: UserResponse = Depends(get_current_active_user)
):
    """Add step to workflow"""
    new_step = await workflow_service.add_workflow_step(workflow_id, current_user.id, step)
    return {"message": "Step added successfully", "step": new_step.dict()}

@router.put("/{workflow_id}/steps/{step_id}")
async def update_workflow_step(
    workflow_id: str,
    step_id: str,
    step_update: Dict[str, Any],
    current_user: UserResponse = Depends(get_current_active_user)
):
    """Update workflow step"""
    success = await workflow_service.update_workflow_step(workflow_id, current_user.id, step_id, step_update)
    if not success:
        raise HTTPException(status_code=404, detail="Step not found")
    
    return {"message": "Step updated successfully"}

@router.delete("/{workflow_id}/steps/{step_id}")
async def remove_workflow_step(
    workflow_id: str,
    step_id: str,
    current_user: UserResponse = Depends(get_current_active_user)
):
    """Remove step from workflow"""
    success = await workflow_service.remove_workflow_step(workflow_id, current_user.id, step_id)
    if not success:
        raise HTTPException(status_code=404, detail="Step not found")
    
    return {"message": "Step removed successfully"}

@router.post("/{workflow_id}/deploy")
async def deploy_workflow(
    workflow_id: str,
    current_user: UserResponse = Depends(get_current_active_user)
):
    """Deploy workflow to n8n"""
    try:
        result = await workflow_service.deploy_workflow(workflow_id, current_user.id)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Deployment failed: {str(e)}"
        )

@router.post("/{workflow_id}/execute")
async def execute_workflow(
    workflow_id: str,
    trigger_data: Dict[str, Any] = None,
    current_user: UserResponse = Depends(get_current_active_user),
    _: None = Depends(rate_limit_check)
):
    """Execute workflow"""
    try:
        execution_id = await workflow_service.execute_workflow(
            workflow_id, current_user.id, trigger_data
        )
        return {"execution_id": execution_id, "status": "started"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Execution failed: {str(e)}"
        )

@router.get("/{workflow_id}/executions", response_model=List[WorkflowExecutionResponse])
async def get_workflow_executions(
    workflow_id: str,
    current_user: UserResponse = Depends(get_current_active_user),
    limit: int = 50
):
    """Get workflow execution history"""
    return await workflow_service.get_workflow_executions(workflow_id, current_user.id, limit)

@router.get("/executions/{execution_id}/status")
async def get_execution_status(
    execution_id: str,
    current_user: UserResponse = Depends(get_current_active_user)
):
    """Get execution status"""
    try:
        return await workflow_service.get_execution_status(execution_id, current_user.id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

@router.post("/{workflow_id}/pause")
async def pause_workflow(
    workflow_id: str,
    current_user: UserResponse = Depends(get_current_active_user)
):
    """Pause workflow"""
    success = await workflow_service.pause_workflow(workflow_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    return {"message": "Workflow paused"}

@router.post("/{workflow_id}/resume")
async def resume_workflow(
    workflow_id: str,
    current_user: UserResponse = Depends(get_current_active_user)
):
    """Resume workflow"""
    success = await workflow_service.resume_workflow(workflow_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    return {"message": "Workflow resumed"}

@router.delete("/{workflow_id}")
async def delete_workflow(
    workflow_id: str,
    current_user: UserResponse = Depends(get_current_active_user)
):
    """Delete workflow"""
    success = await workflow_service.delete_workflow(workflow_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    return {"message": "Workflow deleted successfully"}