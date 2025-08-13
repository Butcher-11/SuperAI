import os
from pathlib import Path
from typing import List, Optional
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables
ROOT_DIR = Path(__file__).parent.parent.parent
load_dotenv(ROOT_DIR / '.env')

class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Loki AI Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # Database
    MONGO_URL: str = os.getenv("MONGO_URL", "mongodb://localhost:27017")
    POSTGRES_URL: str = os.getenv("POSTGRES_URL", "postgresql://localhost/loki_db")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    DB_NAME: str = os.getenv("DB_NAME", "loki_platform")
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-super-secret-key")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
    
    # CORS
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "*")
    
    # AI APIs
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    ANTHROPIC_API_KEY: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
    EMERGENT_LLM_KEY: Optional[str] = os.getenv("EMERGENT_LLM_KEY")
    
    # n8n Configuration
    N8N_BASE_URL: str = os.getenv("N8N_BASE_URL", "http://localhost:5678")
    N8N_API_KEY: Optional[str] = os.getenv("N8N_API_KEY")
    N8N_WEBHOOK_URL: str = os.getenv("N8N_WEBHOOK_URL", "http://localhost:8001")
    
    # OAuth Configurations
    GOOGLE_CLIENT_ID: Optional[str] = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET: Optional[str] = os.getenv("GOOGLE_CLIENT_SECRET")
    SLACK_CLIENT_ID: Optional[str] = os.getenv("SLACK_CLIENT_ID")
    SLACK_CLIENT_SECRET: Optional[str] = os.getenv("SLACK_CLIENT_SECRET")
    GITHUB_CLIENT_ID: Optional[str] = os.getenv("GITHUB_CLIENT_ID")
    GITHUB_CLIENT_SECRET: Optional[str] = os.getenv("GITHUB_CLIENT_SECRET")
    NOTION_CLIENT_ID: Optional[str] = os.getenv("NOTION_CLIENT_ID")
    NOTION_CLIENT_SECRET: Optional[str] = os.getenv("NOTION_CLIENT_SECRET")
    FIGMA_CLIENT_ID: Optional[str] = os.getenv("FIGMA_CLIENT_ID")
    FIGMA_CLIENT_SECRET: Optional[str] = os.getenv("FIGMA_CLIENT_SECRET")
    JIRA_CLIENT_ID: Optional[str] = os.getenv("JIRA_CLIENT_ID")
    JIRA_CLIENT_SECRET: Optional[str] = os.getenv("JIRA_CLIENT_SECRET")
    
    # Background Jobs
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
    RATE_LIMIT_PER_HOUR: int = int(os.getenv("RATE_LIMIT_PER_HOUR", "1000"))
    
    # Monitoring
    SENTRY_DSN: Optional[str] = os.getenv("SENTRY_DSN")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    class Config:
        case_sensitive = True

settings = Settings()