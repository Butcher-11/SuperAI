from celery import current_app as celery_app
from typing import Dict, Any
import asyncio

from app.services.ai_service import ai_service
from app.db.mongodb import get_database

@celery_app.task(bind=True)
def process_ai_message_task(self, user_id: str, conversation_id: str, message_content: str, thinking_mode: str = "medium"):
    """Background task for AI message processing"""
    try:
        # Run async function in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        result = loop.run_until_complete(
            ai_service.process_message(user_id, conversation_id, message_content, thinking_mode)
        )
        
        loop.close()
        return result
    
    except Exception as e:
        # Retry up to 3 times with exponential backoff
        if self.request.retries < 3:
            raise self.retry(countdown=60 * (2 ** self.request.retries), max_retries=3)
        raise e

@celery_app.task
def batch_ai_processing_task(requests: list):
    """Process multiple AI requests in batch"""
    results = []
    
    for request in requests:
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            result = loop.run_until_complete(
                ai_service.process_message(
                    request["user_id"],
                    request["conversation_id"],
                    request["message_content"],
                    request.get("thinking_mode", "medium")
                )
            )
            
            results.append({"success": True, "result": result})
            loop.close()
            
        except Exception as e:
            results.append({"success": False, "error": str(e)})
    
    return results