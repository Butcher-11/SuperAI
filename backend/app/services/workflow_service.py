from typing import Dict, List, Any, Optional
from datetime import datetime

from app.models.workflow import (
    Workflow, WorkflowCreate, WorkflowUpdate, WorkflowResponse,
    WorkflowExecution, WorkflowExecutionResponse, WorkflowStep,
    WorkflowStatus, ExecutionStatus, TriggerType
)
from app.db.mongodb import get_database
from app.services.n8n_service import n8n_service

class WorkflowService:
    def __init__(self):
        self.db = get_database()
    
    async def create_workflow(self, user_id: str, team_id: str, workflow_data: WorkflowCreate) -> WorkflowResponse:
        """Create a new workflow"""
        workflow = Workflow(
            user_id=user_id,
            team_id=team_id,
            name=workflow_data.name,
            description=workflow_data.description,
            trigger_type=workflow_data.trigger_type,
            trigger_config=workflow_data.trigger_config
        )
        
        await self.db.workflows.insert_one(workflow.dict())
        
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
    
    async def get_user_workflows(self, user_id: str) -> List[WorkflowResponse]:
        """Get all workflows for a user"""
        workflows = await self.db.workflows.find({"user_id": user_id}).to_list(100)
        
        return [
            WorkflowResponse(
                id=w["id"],
                name=w["name"],
                description=w.get("description"),
                trigger_type=w["trigger_type"],
                trigger_config=w["trigger_config"],
                status=w["status"],
                steps_count=len(w.get("steps", [])),
                tags=w.get("tags", []),
                created_at=w["created_at"],
                updated_at=w["updated_at"]
            )
            for w in workflows
        ]
    
    async def get_workflow(self, workflow_id: str, user_id: str) -> Optional[Workflow]:
        """Get workflow by ID"""
        workflow_doc = await self.db.workflows.find_one({"id": workflow_id, "user_id": user_id})
        return Workflow(**workflow_doc) if workflow_doc else None
    
    async def update_workflow(self, workflow_id: str, user_id: str, update_data: WorkflowUpdate) -> WorkflowResponse:
        """Update workflow"""
        update_dict = {k: v for k, v in update_data.dict().items() if v is not None}
        update_dict["updated_at"] = datetime.utcnow()
        
        result = await self.db.workflows.update_one(
            {"id": workflow_id, "user_id": user_id},
            {"$set": update_dict}
        )
        
        if result.matched_count == 0:
            raise Exception("Workflow not found")
        
        # Get updated workflow
        updated_workflow = await self.get_workflow(workflow_id, user_id)
        
        return WorkflowResponse(
            id=updated_workflow.id,
            name=updated_workflow.name,
            description=updated_workflow.description,
            trigger_type=updated_workflow.trigger_type,
            trigger_config=updated_workflow.trigger_config,
            status=updated_workflow.status,
            steps_count=len(updated_workflow.steps),
            tags=updated_workflow.tags,
            created_at=updated_workflow.created_at,
            updated_at=updated_workflow.updated_at
        )
    
    async def add_workflow_step(self, workflow_id: str, user_id: str, step: WorkflowStep) -> WorkflowStep:
        """Add step to workflow"""
        # Set step order
        workflow_doc = await self.db.workflows.find_one({"id": workflow_id, "user_id": user_id})
        if not workflow_doc:
            raise Exception("Workflow not found")
        
        workflow = Workflow(**workflow_doc)
        step.order = len(workflow.steps)
        
        # Add step to workflow
        await self.db.workflows.update_one(
            {"id": workflow_id, "user_id": user_id},
            {
                "$push": {"steps": step.dict()},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        
        return step
    
    async def update_workflow_step(self, workflow_id: str, user_id: str, step_id: str, step_update: Dict[str, Any]) -> bool:
        """Update specific workflow step"""
        result = await self.db.workflows.update_one(
            {
                "id": workflow_id,
                "user_id": user_id,
                "steps.id": step_id
            },
            {
                "$set": {
                    f"steps.$.{k}": v for k, v in step_update.items()
                }
            }
        )
        
        return result.modified_count > 0
    
    async def remove_workflow_step(self, workflow_id: str, user_id: str, step_id: str) -> bool:
        """Remove step from workflow"""
        result = await self.db.workflows.update_one(
            {"id": workflow_id, "user_id": user_id},
            {
                "$pull": {"steps": {"id": step_id}},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        
        return result.modified_count > 0
    
    async def deploy_workflow(self, workflow_id: str, user_id: str) -> Dict[str, Any]:
        """Deploy workflow to n8n"""
        workflow = await self.get_workflow(workflow_id, user_id)
        if not workflow:
            raise Exception("Workflow not found")
        
        if workflow.status == WorkflowStatus.ACTIVE:
            raise Exception("Workflow is already active")
        
        # Deploy to n8n
        try:
            n8n_workflow_id = await n8n_service.create_n8n_workflow(workflow)
            
            # Update workflow with n8n ID and activate
            await self.db.workflows.update_one(
                {"id": workflow_id},
                {
                    "$set": {
                        "n8n_workflow_id": n8n_workflow_id,
                        "status": WorkflowStatus.ACTIVE,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            # Get webhook URL if webhook trigger
            webhook_url = None
            if workflow.trigger_type == TriggerType.WEBHOOK:
                webhook_url = await n8n_service.get_workflow_webhook_url(workflow_id)
            
            return {
                "status": "deployed",
                "n8n_workflow_id": n8n_workflow_id,
                "webhook_url": webhook_url
            }
        except Exception as e:
            # Mark as error
            await self.db.workflows.update_one(
                {"id": workflow_id},
                {
                    "$set": {
                        "status": WorkflowStatus.ERROR,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            raise e
    
    async def execute_workflow(self, workflow_id: str, user_id: str, trigger_data: Dict[str, Any] = None) -> str:
        """Execute workflow"""
        workflow = await self.get_workflow(workflow_id, user_id)
        if not workflow:
            raise Exception("Workflow not found")
        
        if workflow.status != WorkflowStatus.ACTIVE:
            raise Exception("Workflow is not active")
        
        # Execute via n8n
        execution_id = await n8n_service.execute_workflow(workflow_id, trigger_data)
        
        return execution_id
    
    async def get_workflow_executions(self, workflow_id: str, user_id: str, limit: int = 50) -> List[WorkflowExecutionResponse]:
        """Get workflow execution history"""
        executions = await self.db.workflow_executions.find(
            {"workflow_id": workflow_id, "user_id": user_id}
        ).sort("started_at", -1).limit(limit).to_list(limit)
        
        return [
            WorkflowExecutionResponse(
                id=e["id"],
                workflow_id=e["workflow_id"],
                status=e["status"],
                started_at=e["started_at"],
                completed_at=e.get("completed_at"),
                duration_seconds=e.get("duration_seconds"),
                error_message=e.get("error_message")
            )
            for e in executions
        ]
    
    async def get_execution_status(self, execution_id: str, user_id: str) -> Dict[str, Any]:
        """Get execution status"""
        execution_doc = await self.db.workflow_executions.find_one({"id": execution_id, "user_id": user_id})
        if not execution_doc:
            raise Exception("Execution not found")
        
        # Get latest status from n8n
        return await n8n_service.get_execution_status(execution_id)
    
    async def pause_workflow(self, workflow_id: str, user_id: str) -> bool:
        """Pause workflow"""
        result = await self.db.workflows.update_one(
            {"id": workflow_id, "user_id": user_id},
            {
                "$set": {
                    "status": WorkflowStatus.PAUSED,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        return result.modified_count > 0
    
    async def resume_workflow(self, workflow_id: str, user_id: str) -> bool:
        """Resume workflow"""
        result = await self.db.workflows.update_one(
            {"id": workflow_id, "user_id": user_id},
            {
                "$set": {
                    "status": WorkflowStatus.ACTIVE,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        return result.modified_count > 0
    
    async def delete_workflow(self, workflow_id: str, user_id: str) -> bool:
        """Delete workflow"""
        workflow = await self.get_workflow(workflow_id, user_id)
        if not workflow:
            return False
        
        # Delete from n8n if deployed
        if workflow.n8n_workflow_id:
            try:
                await n8n_service.delete_n8n_workflow(workflow.n8n_workflow_id)
            except Exception:
                pass  # Continue even if n8n deletion fails
        
        # Delete executions
        await self.db.workflow_executions.delete_many({"workflow_id": workflow_id})
        
        # Delete workflow
        result = await self.db.workflows.delete_one({"id": workflow_id, "user_id": user_id})
        
        return result.deleted_count > 0

workflow_service = WorkflowService()