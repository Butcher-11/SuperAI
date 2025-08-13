<file>
      <absolute_file_name>/app/backend/app/api/chat.py</absolute_file_name>
      <content">from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from datetime import datetime
import json

from app.models.chat import (
    Conversation, ConversationCreate, ConversationResponse,
    Message, MessageCreate, MessageResponse, ThinkingMode, ChatSession
)
from app.models.user import UserResponse
from app.services.ai_service import ai_service
from app.db.mongodb import get_database
from app.api.deps import get_current_active_user, rate_limit_check

router = APIRouter(prefix="/chat", tags=["chat"])

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.active_connections[user_id] = websocket
    
    def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
    
    async def send_message(self, user_id: str, message: dict):
        if user_id in self.active_connections:
            await self.active_connections[user_id].send_text(json.dumps(message))

manager = ConnectionManager()

@router.post("/conversations", response_model=ConversationResponse)
async def create_conversation(
    conversation_data: ConversationCreate,
    current_user: UserResponse = Depends(get_current_active_user)
):
    """Create new conversation"""
    db = get_database()
    
    conversation = Conversation(
        user_id=current_user.id,
        team_id=current_user.team_id or "",
        title=conversation_data.title,
        chat_type=conversation_data.chat_type,
        thinking_mode=conversation_data.thinking_mode,
        ai_model=conversation_data.ai_model
    )
    
    await db.conversations.insert_one(conversation.dict())
    
    return ConversationResponse(**conversation.dict())

@router.get("/conversations", response_model=List[ConversationResponse])
async def get_conversations(
    current_user: UserResponse = Depends(get_current_active_user)
):
    """Get user's conversations"""
    db = get_database()
    
    conversations = await db.conversations.find(
        {"user_id": current_user.id, "is_active": True}
    ).sort("last_activity", -1).limit(50).to_list(50)
    
    return [ConversationResponse(**conv) for conv in conversations]

@router.get("/conversations/{conversation_id}/messages", response_model=List[MessageResponse])
async def get_messages(
    conversation_id: str,
    current_user: UserResponse = Depends(get_current_active_user),
    limit: int = 50
):
    """Get conversation messages"""
    db = get_database()
    
    # Verify conversation belongs to user
    conversation = await db.conversations.find_one({
        "id": conversation_id,
        "user_id": current_user.id
    })
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    messages = await db.messages.find(
        {"conversation_id": conversation_id}
    ).sort("created_at", 1).limit(limit).to_list(limit)
    
    return [MessageResponse(**msg) for msg in messages]

@router.post("/conversations/{conversation_id}/messages", response_model=MessageResponse)
async def send_message(
    conversation_id: str,
    message_data: MessageCreate,
    current_user: UserResponse = Depends(get_current_active_user),
    _: None = Depends(rate_limit_check)
):
    """Send message to conversation"""
    db = get_database()
    
    # Verify conversation belongs to user
    conversation = await db.conversations.find_one({
        "id": conversation_id,
        "user_id": current_user.id
    })
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Process message with AI
    try:
        ai_response = await ai_service.process_message(
            user_id=current_user.id,
            conversation_id=conversation_id,
            message_content=message_data.content,
            thinking_mode=message_data.thinking_mode or ThinkingMode.MEDIUM
        )
        
        # Send real-time update via WebSocket
        await manager.send_message(current_user.id, {
            "type": "ai_response",
            "conversation_id": conversation_id,
            "message": ai_response
        })
        
        return MessageResponse(**ai_response)
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI processing failed: {str(e)}"
        )

@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user: UserResponse = Depends(get_current_active_user)
):
    """Delete conversation"""
    db = get_database()
    
    # Delete conversation and its messages
    await db.conversations.update_one(
        {"id": conversation_id, "user_id": current_user.id},
        {"$set": {"is_active": False}}
    )
    
    return {"message": "Conversation deleted"}

@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """WebSocket endpoint for real-time chat"""
    try:
        await manager.connect(websocket, user_id)
        
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # Handle different message types
            if message_data.get("type") == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
            elif message_data.get("type") == "typing":
                # Broadcast typing indicator to other participants
                pass
            
    except WebSocketDisconnect:
        manager.disconnect(user_id)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(user_id)</content>
    </file>