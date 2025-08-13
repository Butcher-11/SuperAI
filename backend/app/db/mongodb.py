import asyncio
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import IndexModel, ASCENDING, DESCENDING
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

class MongoDB:
    client: Optional[AsyncIOMotorClient] = None
    database: Optional[AsyncIOMotorDatabase] = None

mongodb = MongoDB()

async def connect_to_mongo():
    """Create database connection"""
    logger.info("Connecting to MongoDB...")
    mongodb.client = AsyncIOMotorClient(settings.MONGO_URL)
    mongodb.database = mongodb.client[settings.DB_NAME]
    
    # Test connection
    try:
        await mongodb.client.admin.command('ping')
        logger.info("Successfully connected to MongoDB")
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise

async def close_mongo_connection():
    """Close database connection"""
    logger.info("Closing connection to MongoDB...")
    if mongodb.client:
        mongodb.client.close()

async def create_indexes():
    """Create database indexes for optimal performance"""
    if not mongodb.database:
        return
    
    # Users collection indexes
    await mongodb.database.users.create_indexes([
        IndexModel([("email", ASCENDING)], unique=True),
        IndexModel([("team_id", ASCENDING)]),
        IndexModel([("created_at", DESCENDING)])
    ])
    
    # Teams collection indexes  
    await mongodb.database.teams.create_indexes([
        IndexModel([("owner_id", ASCENDING)]),
        IndexModel([("created_at", DESCENDING)])
    ])
    
    # Integrations collection indexes
    await mongodb.database.integrations.create_indexes([
        IndexModel([("user_id", ASCENDING)]),
        IndexModel([("team_id", ASCENDING)]),
        IndexModel([("integration_type", ASCENDING)]),
        IndexModel([("user_id", ASCENDING), ("integration_type", ASCENDING)]),
        IndexModel([("created_at", DESCENDING)])
    ])
    
    # Conversations collection indexes
    await mongodb.database.conversations.create_indexes([
        IndexModel([("user_id", ASCENDING)]),
        IndexModel([("team_id", ASCENDING)]),
        IndexModel([("last_activity", DESCENDING)]),
        IndexModel([("created_at", DESCENDING)])
    ])
    
    # Messages collection indexes
    await mongodb.database.messages.create_indexes([
        IndexModel([("conversation_id", ASCENDING)]),
        IndexModel([("conversation_id", ASCENDING), ("created_at", ASCENDING)]),
        IndexModel([("created_at", DESCENDING)])
    ])
    
    # Workflows collection indexes
    await mongodb.database.workflows.create_indexes([
        IndexModel([("user_id", ASCENDING)]),
        IndexModel([("team_id", ASCENDING)]),
        IndexModel([("status", ASCENDING)]),
        IndexModel([("trigger_type", ASCENDING)]),
        IndexModel([("created_at", DESCENDING)])
    ])
    
    # Workflow executions collection indexes
    await mongodb.database.workflow_executions.create_indexes([
        IndexModel([("workflow_id", ASCENDING)]),
        IndexModel([("user_id", ASCENDING)]),
        IndexModel([("status", ASCENDING)]),
        IndexModel([("started_at", DESCENDING)])
    ])
    
    # OAuth states collection indexes (with TTL)
    await mongodb.database.oauth_states.create_indexes([
        IndexModel([("user_id", ASCENDING)]),
        IndexModel([("state", ASCENDING)], unique=True),
        IndexModel([("expires_at", ASCENDING)], expireAfterSeconds=3600)  # TTL index
    ])
    
    logger.info("Database indexes created successfully")

def get_database() -> AsyncIOMotorDatabase:
    """Get database instance"""
    if not mongodb.database:
        raise Exception("Database not connected")
    return mongodb.database