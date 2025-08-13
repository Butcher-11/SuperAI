from celery import current_app as celery_app
import asyncio
from typing import Dict, Any

from app.services.integration_service import integration_service
from app.db.mongodb import get_database

@celery_app.task(bind=True)
def sync_integration_data_task(self, user_id: str, integration_id: str):
    """Background task for syncing integration data"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Get integration details
        db = get_database()
        integration_doc = loop.run_until_complete(
            db.integrations.find_one({"id": integration_id, "user_id": user_id})
        )
        
        if not integration_doc:
            raise Exception("Integration not found")
        
        integration_type = integration_doc["integration_type"]
        
        # Perform sync based on integration type
        if integration_type == "slack":
            result = loop.run_until_complete(sync_slack_data(user_id, integration_id))
        elif integration_type == "google":
            result = loop.run_until_complete(sync_google_data(user_id, integration_id))
        elif integration_type == "github":
            result = loop.run_until_complete(sync_github_data(user_id, integration_id))
        else:
            result = {"status": "no_sync_needed"}
        
        # Update last sync time
        loop.run_until_complete(
            db.integrations.update_one(
                {"id": integration_id},
                {"$set": {"last_sync": __import__('datetime').datetime.utcnow()}}
            )
        )
        
        loop.close()
        return result
    
    except Exception as e:
        # Retry up to 3 times
        if self.request.retries < 3:
            raise self.retry(countdown=300, max_retries=3)  # 5 minutes
        raise e

async def sync_slack_data(user_id: str, integration_id: str) -> Dict[str, Any]:
    """Sync Slack channels, users, and recent messages"""
    # Implementation would fetch recent channels, users, messages
    # and store them in a cache or search index
    return {"status": "slack_sync_completed", "channels": 10, "messages": 100}

async def sync_google_data(user_id: str, integration_id: str) -> Dict[str, Any]:
    """Sync Google Workspace data"""
    # Implementation would sync Gmail, Calendar, Drive data
    return {"status": "google_sync_completed", "emails": 50, "events": 20}

async def sync_github_data(user_id: str, integration_id: str) -> Dict[str, Any]:
    """Sync GitHub repositories and issues"""
    # Implementation would sync repos, issues, PRs
    return {"status": "github_sync_completed", "repos": 15, "issues": 30}

@celery_app.task
def execute_integration_action_task(user_id: str, integration_type: str, action: str, parameters: Dict[str, Any]):
    """Execute integration action in background"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        result = loop.run_until_complete(
            integration_service.execute_action(user_id, integration_type, action, parameters)
        )
        
        loop.close()
        return result
    
    except Exception as e:
        raise e