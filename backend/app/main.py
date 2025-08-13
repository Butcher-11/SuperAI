import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from app.core.config import settings
from app.db.mongodb import connect_to_mongo, close_mongo_connection, create_indexes
from app.db.redis import connect_to_redis, close_redis_connection

# Import routers
from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.integrations import router as integrations_router
from app.api.workflows import router as workflows_router
from app.api.webhooks import router as webhooks_router

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting up Loki AI Platform Backend...")
    
    # Connect to databases
    await connect_to_mongo()
    await connect_to_redis()
    
    # Create database indexes
    await create_indexes()
    
    logger.info("✅ Backend startup complete!")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Loki AI Platform Backend...")
    await close_mongo_connection()
    await close_redis_connection()
    logger.info("✅ Backend shutdown complete!")

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-Powered Productivity Platform Backend - Connect tools, automate workflows, chat with AI",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(",") if settings.CORS_ORIGINS != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Global exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
            "error": str(exc) if settings.DEBUG else "Something went wrong"
        }
    )

# Health check endpoints
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Loki AI Platform Backend",
        "version": settings.APP_VERSION,
        "status": "healthy"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Basic health checks could be added here
        # (database connectivity, external services, etc.)
        return {
            "status": "healthy",
            "timestamp": __import__('datetime').datetime.utcnow().isoformat(),
            "version": settings.APP_VERSION
        }
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": __import__('datetime').datetime.utcnow().isoformat()
            }
        )

# Include API routers with /api prefix
app.include_router(auth_router, prefix="/api")
app.include_router(chat_router, prefix="/api")
app.include_router(integrations_router, prefix="/api")
app.include_router(workflows_router, prefix="/api")
app.include_router(webhooks_router, prefix="/api")

# Development server
if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8001,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )