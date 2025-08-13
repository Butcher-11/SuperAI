from celery import current_app as celery_app
import asyncio
from typing import Dict, Any

from app.services.workflow_service import workflow_service
from app.services.n8n_service import n8n_service
from app.db.mongodb import get_database

@celery_app.task(bind=True)
def execute_workflow_task(self, workflow_id: str, user_id: str, trigger_data: Dict[str, Any] = None):
    """Background task for workflow execution"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        execution_id = loop.run_until_complete(
            workflow_service.execute_workflow(workflow_id, user_id, trigger_data)
        )
        
        loop.close()
        return {"execution_id": execution_id, "status": "started"}
    
    except Exception as e:
        # Retry up to 2 times
        if self.request.retries < 2:
            raise self.retry(countdown=120, max_retries=2)  # 2 minutes
        raise e

@celery_app.task
def monitor_workflow_executions_task():
    """Monitor and update workflow execution statuses"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        db = get_database()
        
        # Find running executions
        running_executions = loop.run_until_complete(
            db.workflow_executions.find({"status": "running"}).to_list(100)
        )
        
        updated_count = 0
        for execution in running_executions:
            try:
                # Get status from n8n
                status_result = loop.run_until_complete(
                    n8n_service.get_execution_status(execution["id"])
                )
                
                if status_result["status"] != "running":
                    updated_count += 1
                
            except Exception as e:
                print(f"Error checking execution {execution['id']}: {e}")
        
        loop.close()
        return {"updated_executions": updated_count}
    
    except Exception as e:
        raise e

@celery_app.task
def cleanup_old_executions_task():
    """Clean up old workflow executions"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        db = get_database()
        
        # Delete executions older than 30 days
        cutoff_date = __import__('datetime').datetime.utcnow() - __import__('datetime').timedelta(days=30)
        
        result = loop.run_until_complete(
            db.workflow_executions.delete_many({"started_at": {"$lt": cutoff_date}})
        )
        
        loop.close()
        return {"deleted_executions": result.deleted_count}
    
    except Exception as e:
        raise e

@celery_app.task
def deploy_workflow_task(workflow_id: str, user_id: str):
    """Deploy workflow to n8n in background"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        result = loop.run_until_complete(
            workflow_service.deploy_workflow(workflow_id, user_id)
        )
        
        loop.close()
        return result
    
    except Exception as e:
        raise e