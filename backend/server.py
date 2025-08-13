from fastapi import FastAPI, APIRouter
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Dict, Any
import uuid
from datetime import datetime

# Load environment variables
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME', 'test_database')]

# Create the main app
app = FastAPI(
    title="Loki AI Platform Backend",
    version="1.0.0",
    description="AI-Powered Productivity Platform Backend"
)

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Basic health check endpoints
@app.get("/")
async def root():
    return {
        "message": "Loki AI Platform Backend",
        "version": "1.0.0",
        "status": "healthy"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }

# Define Models (keeping the original status check for compatibility)
class StatusCheck(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class StatusCheckCreate(BaseModel):
    client_name: str

# Basic API endpoints for compatibility
@api_router.get("/")
async def api_root():
    return {"message": "Loki AI Platform API", "version": "1.0.0"}

@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = input.dict()
    status_obj = StatusCheck(**status_dict)
    await db.status_checks.insert_one(status_obj.dict())
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    status_checks = await db.status_checks.find().to_list(1000)
    return [StatusCheck(**status_check) for status_check in status_checks]

# Placeholder API endpoints for the full platform
@api_router.get("/integrations")
async def get_integrations():
    """Get available integrations"""
    return {
        "integrations": [
            {"name": "Slack", "type": "slack", "status": "available"},
            {"name": "Google Workspace", "type": "google", "status": "available"},
            {"name": "GitHub", "type": "github", "status": "available"},
            {"name": "Notion", "type": "notion", "status": "available"},
            {"name": "Figma", "type": "figma", "status": "available"},
            {"name": "Jira", "type": "jira", "status": "available"}
        ]
    }

@api_router.get("/workflows")
async def get_workflows():
    """Get workflows"""
    return {"workflows": [], "message": "Workflow system ready"}

@api_router.post("/chat")
async def chat_endpoint(message: Dict[str, Any]):
    """Chat endpoint placeholder"""
    return {
        "response": "AI chat system is being prepared. This is a placeholder response.",
        "message": message.get("content", ""),
        "status": "placeholder"
    }

# Include the router in the main app
app.include_router(api_router)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()

# For backwards compatibility
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)