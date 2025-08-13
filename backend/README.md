# Loki AI Platform Backend

A comprehensive FastAPI-based backend for building AI-powered productivity platforms like itsloki.com.

## 🏗️ Architecture Overview

This backend provides a complete foundation for building a Loki-like AI productivity platform with:

- **FastAPI** for high-performance API development
- **MongoDB** with Motor for async database operations  
- **Redis** for caching and session management
- **n8n** integration for workflow automation
- **Multiple AI providers** (OpenAI, Anthropic, Emergent)
- **OAuth integrations** for popular tools (Slack, Google, GitHub, etc.)
- **Celery** for background task processing
- **WebSockets** for real-time communication

## 🔧 Current Implementation Status

### ✅ Completed Features

#### Core Infrastructure
- FastAPI application with proper CORS handling
- MongoDB connection with Motor async driver
- Redis integration for caching and sessions
- Environment-based configuration system
- Proper error handling and logging

#### API Structure
- Modular API router system with `/api` prefix
- Health check endpoints (`/` and `/health`)
- RESTful API design patterns
- Comprehensive data models with Pydantic

#### Database Models
- **Users & Teams**: User management with team-based organization
- **Integrations**: OAuth integration management for external services
- **Chat & Conversations**: AI chat system with context management
- **Workflows**: n8n-based workflow automation system
- **Background Tasks**: Celery task definitions

#### Service Layer
- **AuthService**: User authentication and team management
- **AIService**: Multi-provider AI integration (OpenAI, Anthropic, Emergent)
- **IntegrationService**: OAuth and external service management
- **WorkflowService**: Workflow creation and execution
- **N8NService**: n8n workflow automation integration

### 📊 API Endpoints

#### Core Endpoints
```
GET  /                          # Health check
GET  /health                    # Detailed health status
GET  /api/                      # API root
```

#### Authentication (Prepared)
```
POST /api/auth/register         # User registration
POST /api/auth/login            # User login
POST /api/auth/refresh          # Token refresh
POST /api/auth/logout           # User logout
GET  /api/auth/me              # Current user info
```

#### Integrations (Prepared)
```
GET  /api/integrations          # List user integrations
GET  /api/integrations/available # Available integration types
POST /api/integrations/connect/{type} # Initiate OAuth
POST /api/integrations/oauth/callback # OAuth callback
POST /api/integrations/execute  # Execute integration action
DEL  /api/integrations/{id}     # Remove integration
```

#### AI Chat (Prepared)
```
POST /api/chat/conversations    # Create conversation
GET  /api/chat/conversations    # List conversations
GET  /api/chat/conversations/{id}/messages # Get messages
POST /api/chat/conversations/{id}/messages # Send message
WS   /api/chat/ws/{user_id}     # WebSocket connection
```

#### Workflows (Prepared)
```
POST /api/workflows             # Create workflow
GET  /api/workflows             # List workflows
GET  /api/workflows/{id}        # Get workflow
PUT  /api/workflows/{id}        # Update workflow
POST /api/workflows/{id}/deploy # Deploy to n8n
POST /api/workflows/{id}/execute # Execute workflow
GET  /api/workflows/{id}/executions # Execution history
```

#### Webhooks (Prepared)
```
POST /api/webhooks/n8n/{workflow_id} # n8n webhook
POST /api/webhooks/integration/{type} # Integration webhook
```

### 🔌 Supported Integrations

The backend is designed to support these integrations:

#### Active Support Prepared
- **Slack**: Messaging, channels, users
- **Google Workspace**: Gmail, Calendar, Drive
- **GitHub**: Repositories, issues, pull requests
- **Notion**: Pages, databases, blocks
- **Figma**: Files, comments, components
- **Jira**: Issues, projects, workflows
- **Confluence**: Pages, spaces, content

#### Coming Soon (Framework Ready)
- HubSpot, Salesforce, Greenhouse
- Workday, AWS, Amazon Marketplace

## 🔄 n8n Workflow Integration

The backend includes comprehensive n8n integration:

### Features
- **Workflow Creation**: Convert Loki workflows to n8n format
- **Execution Management**: Track workflow executions
- **Webhook Support**: Handle n8n webhook triggers
- **Status Monitoring**: Real-time execution status updates

### n8n Node Types Supported
- HTTP Request nodes for API calls
- Integration-specific nodes (Slack, GitHub, etc.)
- AI processing nodes (OpenAI)
- Custom function nodes
- Trigger nodes (webhook, schedule, manual)

## 🤖 AI Integration

### Multiple Provider Support
- **OpenAI**: GPT-4, GPT-3.5-turbo
- **Anthropic**: Claude models
- **Emergent**: Unified LLM access

### Features
- **Thinking Modes**: Quick, Medium, Deep processing
- **Tool Calling**: Integration action execution
- **Context Management**: Conversation history and context
- **Streaming Responses**: Real-time AI responses

## 🔐 Security & Authentication

### JWT-Based Authentication
- Access tokens (30 min expiry)
- Refresh tokens (7 day expiry)
- Secure password hashing with bcrypt

### OAuth Integration
- OAuth 2.0 flows for external services
- Encrypted token storage
- Automatic token refresh

### Rate Limiting
- Per-user rate limiting
- Redis-based sliding window
- Configurable limits per endpoint

## ⚙️ Configuration

### Environment Variables
```bash
# Database
MONGO_URL="mongodb://localhost:27017"
REDIS_URL="redis://localhost:6379"
DB_NAME="loki_platform"

# Security
SECRET_KEY="your-super-secret-key"
ACCESS_TOKEN_EXPIRE_MINUTES=30

# AI APIs
OPENAI_API_KEY=""
ANTHROPIC_API_KEY=""
EMERGENT_LLM_KEY=""

# n8n Integration
N8N_BASE_URL="http://localhost:5678"
N8N_API_KEY=""

# OAuth Credentials (for each integration)
GOOGLE_CLIENT_ID=""
GOOGLE_CLIENT_SECRET=""
SLACK_CLIENT_ID=""
SLACK_CLIENT_SECRET=""
# ... (more OAuth configs)
```

## 🚀 Deployment

### Development
```bash
cd /app/backend
pip install -r requirements.txt
python server.py
```

### Production
- Supervisord configuration included
- Health checks at `/health`
- Graceful shutdown handling
- Comprehensive logging

### Required Services
- MongoDB (document storage)
- Redis (caching, sessions)
- n8n (workflow automation)
- Celery + Redis (background jobs)

## 📦 Dependencies

### Core
- FastAPI 0.110.1 (API framework)
- Motor 3.3.1 (async MongoDB driver)
- Redis 5.0+ (caching and sessions)
- Pydantic 2.6+ (data validation)

### AI & ML
- OpenAI 1.12+ (GPT integration)
- Anthropic 0.21+ (Claude integration)
- LangChain 0.1+ (AI framework)

### Background Processing
- Celery 5.3+ (task queue)
- Flower 2.0+ (task monitoring)

### External Integrations
- httpx 0.27+ (HTTP client)
- requests-oauthlib 2.0+ (OAuth)

## 🔍 Monitoring & Observability

### Logging
- Structured logging with timestamps
- Configurable log levels
- Error tracking and debugging

### Health Checks
- Database connectivity
- Redis connectivity  
- External service status
- Memory and performance metrics

## 🧪 Testing

### Test Infrastructure
- pytest for unit testing
- pytest-asyncio for async tests
- Test database isolation
- Mock external service calls

## 📚 Usage Examples

### Creating a User
```python
# POST /api/auth/register
{
    "email": "user@example.com",
    "password": "securepassword",
    "full_name": "John Doe"
}
```

### Connecting Slack Integration
```python
# POST /api/integrations/connect/slack
{
    "redirect_uri": "http://localhost:3000/callback"
}
# Returns OAuth URL for user to authorize
```

### Creating a Workflow
```python
# POST /api/workflows
{
    "name": "Daily Standup Reminder",
    "trigger_type": "schedule",
    "trigger_config": {"cron": "0 9 * * 1-5"}
}
```

### Sending AI Chat Message
```python
# POST /api/chat/conversations/{id}/messages
{
    "content": "Analyze my GitHub issues and create a summary",
    "thinking_mode": "deep"
}
```

## 🗂️ File Structure

```
/app/backend/
├── app/
│   ├── api/                    # API endpoints
│   │   ├── auth.py            # Authentication routes
│   │   ├── chat.py            # Chat and AI routes
│   │   ├── integrations.py    # Integration management
│   │   ├── workflows.py       # Workflow management
│   │   └── webhooks.py        # Webhook handlers
│   ├── core/                  # Core utilities
│   │   ├── config.py          # Configuration management
│   │   └── security.py        # Security utilities
│   ├── db/                    # Database layers
│   │   ├── mongodb.py         # MongoDB connection
│   │   └── redis.py           # Redis connection
│   ├── models/                # Data models
│   │   ├── user.py            # User and team models
│   │   ├── integration.py     # Integration models
│   │   ├── chat.py            # Chat and conversation models
│   │   └── workflow.py        # Workflow models
│   ├── services/              # Business logic
│   │   ├── auth_service.py    # Authentication service
│   │   ├── ai_service.py      # AI integration service
│   │   ├── integration_service.py # External integrations
│   │   ├── workflow_service.py # Workflow management
│   │   └── n8n_service.py     # n8n integration
│   ├── tasks/                 # Background tasks
│   │   ├── ai_tasks.py        # AI processing tasks
│   │   ├── integration_tasks.py # Integration sync tasks
│   │   └── workflow_tasks.py  # Workflow execution tasks
│   └── main.py               # Main application (advanced)
├── server.py                 # Simple server (current)
├── celery_app.py            # Celery configuration
├── requirements.txt         # Python dependencies
└── .env                     # Environment variables
```

## 🎯 Next Steps

To activate the full platform features:

1. **Set up external services** (MongoDB, Redis, n8n)
2. **Configure OAuth applications** for integrations
3. **Add AI API keys** (OpenAI, Anthropic, or Emergent)
4. **Switch to advanced server** (`app/main.py`)
5. **Start Celery workers** for background processing

This backend provides a solid foundation for building a production-ready AI productivity platform similar to itsloki.com with enterprise-grade features and scalability.