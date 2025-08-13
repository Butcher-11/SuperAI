from typing import Dict, Any
from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
import json

from app.db.mongodb import get_database
from app.services.workflow_service import workflow_service

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

@router.post("/n8n/{workflow_id}")
async def n8n_webhook(
    workflow_id: str,
    request: Request,
    background_tasks: BackgroundTasks
):
    """Handle n8n webhook triggers"""
    try:
        # Get request body
        body = await request.body()
        trigger_data = json.loads(body) if body else {}
        
        # Add to background tasks to avoid blocking
        background_tasks.add_task(
            workflow_service.execute_workflow,
            workflow_id,
            "system",  # system user for webhook triggers
            trigger_data
        )
        
        return {"status": "webhook_received", "workflow_id": workflow_id}
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/integration/{integration_type}")
async def integration_webhook(
    integration_type: str,
    request: Request,
    background_tasks: BackgroundTasks
):
    """Handle webhooks from integrations (Slack, GitHub, etc.)"""
    try:
        # Get request body and headers
        body = await request.body()
        headers = dict(request.headers)
        
        webhook_data = {
            "integration_type": integration_type,
            "headers": headers,
            "body": json.loads(body) if body else {},
            "timestamp": __import__('datetime').datetime.utcnow().isoformat()
        }
        
        # Store webhook event for processing
        db = get_database()
        await db.webhook_events.insert_one(webhook_data)
        
        # Process webhook in background
        background_tasks.add_task(
            process_integration_webhook,
            integration_type,
            webhook_data
        )
        
        return {"status": "webhook_processed"}
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

async def process_integration_webhook(integration_type: str, webhook_data: Dict[str, Any]):
    """Process integration webhook events"""
    db = get_database()
    
    try:
        # Find workflows that should be triggered by this event
        workflows = await db.workflows.find({
            "trigger_type": "webhook",
            "trigger_config.integration_type": integration_type,
            "status": "active"
        }).to_list(100)
        
        for workflow in workflows:
            # Check if webhook matches trigger conditions
            trigger_config = workflow.get("trigger_config", {})
            
            # Simple event matching (can be extended)
            if matches_trigger_conditions(webhook_data, trigger_config):
                # Execute workflow
                await workflow_service.execute_workflow(
                    workflow["id"],
                    workflow["user_id"],
                    webhook_data["body"]
                )
    
    except Exception as e:
        # Log error (in production, use proper logging)
        print(f"Webhook processing error: {e}")

def matches_trigger_conditions(webhook_data: Dict[str, Any], trigger_config: Dict[str, Any]) -> bool:
    """Check if webhook data matches trigger conditions"""
    # Basic event type matching
    expected_event = trigger_config.get("event_type")
    if expected_event:
        body = webhook_data.get("body", {})
        actual_event = body.get("type") or body.get("action") or body.get("event_type")
        if actual_event != expected_event:
            return False
    
    # Add more sophisticated matching logic here
    return True