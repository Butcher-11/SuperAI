import json
import secrets
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import httpx
from urllib.parse import urlencode

from app.core.config import settings
from app.models.integration import Integration, IntegrationType, IntegrationStatus, OAuthState, INTEGRATION_CONFIGS
from app.db.mongodb import get_database
from app.core.security import encrypt_oauth_token, decrypt_oauth_token

class IntegrationService:
    def __init__(self):
        self.db = get_database()
        self.http_client = httpx.AsyncClient()
    
    async def get_user_integrations(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all integrations for a user"""
        integrations = await self.db.integrations.find({"user_id": user_id}).to_list(100)
        
        # Remove sensitive data
        for integration in integrations:
            integration.pop("access_token", None)
            integration.pop("refresh_token", None)
        
        return integrations
    
    async def initiate_oauth(self, user_id: str, integration_type: IntegrationType, redirect_uri: str) -> str:
        """Initiate OAuth flow for integration"""
        config = INTEGRATION_CONFIGS.get(integration_type)
        if not config:
            raise Exception(f"Integration type {integration_type} not supported")
        
        # Generate state parameter
        state = secrets.token_urlsafe(32)
        
        # Store OAuth state
        oauth_state = OAuthState(
            user_id=user_id,
            integration_type=integration_type,
            state=state,
            redirect_uri=redirect_uri,
            expires_at=datetime.utcnow() + timedelta(minutes=10)
        )
        await self.db.oauth_states.insert_one(oauth_state.dict())
        
        # Build OAuth URL based on integration type
        oauth_url = self._build_oauth_url(integration_type, state, redirect_uri)
        
        return oauth_url
    
    def _build_oauth_url(self, integration_type: IntegrationType, state: str, redirect_uri: str) -> str:
        """Build OAuth URL for specific integration"""
        oauth_configs = {
            IntegrationType.SLACK: {
                "base_url": "https://slack.com/oauth/v2/authorize",
                "client_id": settings.SLACK_CLIENT_ID,
                "scopes": "channels:read,chat:write,users:read,im:read,im:write"
            },
            IntegrationType.GOOGLE: {
                "base_url": "https://accounts.google.com/o/oauth2/v2/auth",
                "client_id": settings.GOOGLE_CLIENT_ID,
                "scopes": "https://www.googleapis.com/auth/gmail.modify https://www.googleapis.com/auth/calendar https://www.googleapis.com/auth/drive"
            },
            IntegrationType.GITHUB: {
                "base_url": "https://github.com/login/oauth/authorize",
                "client_id": settings.GITHUB_CLIENT_ID,
                "scopes": "repo,user,write:discussion"
            },
            IntegrationType.NOTION: {
                "base_url": "https://api.notion.com/v1/oauth/authorize",
                "client_id": settings.NOTION_CLIENT_ID,
                "scopes": "read_content,update_content,insert_content"
            }
        }
        
        config = oauth_configs.get(integration_type)
        if not config:
            raise Exception(f"OAuth not configured for {integration_type}")
        
        params = {
            "client_id": config["client_id"],
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": config["scopes"],
            "state": state
        }
        
        return f"{config['base_url']}?{urlencode(params)}"
    
    async def complete_oauth(self, code: str, state: str) -> Dict[str, Any]:
        """Complete OAuth flow and create integration"""
        # Verify state
        oauth_state_doc = await self.db.oauth_states.find_one({"state": state})
        if not oauth_state_doc:
            raise Exception("Invalid OAuth state")
        
        oauth_state = OAuthState(**oauth_state_doc)
        
        if oauth_state.expires_at < datetime.utcnow():
            raise Exception("OAuth state expired")
        
        # Exchange code for tokens
        tokens = await self._exchange_code_for_tokens(oauth_state.integration_type, code, oauth_state.redirect_uri)
        
        # Get user info from the integration
        user_info = await self._get_integration_user_info(oauth_state.integration_type, tokens["access_token"])
        
        # Create or update integration
        integration = Integration(
            user_id=oauth_state.user_id,
            team_id="",  # Will be filled from user's team
            integration_type=oauth_state.integration_type,
            name=f"{oauth_state.integration_type.value.title()} - {user_info.get('name', 'Default')}",
            status=IntegrationStatus.ACTIVE,
            access_token=encrypt_oauth_token(tokens["access_token"]),
            refresh_token=encrypt_oauth_token(tokens.get("refresh_token", "")),
            expires_at=datetime.utcnow() + timedelta(seconds=tokens.get("expires_in", 3600)),
            external_user_id=user_info.get("id"),
            external_workspace_id=user_info.get("workspace_id"),
            scopes=tokens.get("scope", "").split(",") if tokens.get("scope") else [],
            last_sync=datetime.utcnow()
        )
        
        # Get user's team_id
        user = await self.db.users.find_one({"id": oauth_state.user_id})
        if user:
            integration.team_id = user.get("team_id", "")
        
        # Save integration
        await self.db.integrations.insert_one(integration.dict())
        
        # Clean up OAuth state
        await self.db.oauth_states.delete_one({"state": state})
        
        return {
            "integration_id": integration.id,
            "integration_type": integration.integration_type,
            "status": "connected"
        }
    
    async def _exchange_code_for_tokens(self, integration_type: IntegrationType, code: str, redirect_uri: str) -> Dict[str, Any]:
        """Exchange authorization code for access tokens"""
        token_endpoints = {
            IntegrationType.SLACK: {
                "url": "https://slack.com/api/oauth.v2.access",
                "client_id": settings.SLACK_CLIENT_ID,
                "client_secret": settings.SLACK_CLIENT_SECRET
            },
            IntegrationType.GOOGLE: {
                "url": "https://oauth2.googleapis.com/token",
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET
            },
            IntegrationType.GITHUB: {
                "url": "https://github.com/login/oauth/access_token",
                "client_id": settings.GITHUB_CLIENT_ID,
                "client_secret": settings.GITHUB_CLIENT_SECRET
            }
        }
        
        config = token_endpoints.get(integration_type)
        if not config:
            raise Exception(f"Token exchange not configured for {integration_type}")
        
        data = {
            "client_id": config["client_id"],
            "client_secret": config["client_secret"],
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri
        }
        
        headers = {"Accept": "application/json"}
        
        response = await self.http_client.post(config["url"], data=data, headers=headers)
        response.raise_for_status()
        
        return response.json()
    
    async def _get_integration_user_info(self, integration_type: IntegrationType, access_token: str) -> Dict[str, Any]:
        """Get user info from integration API"""
        user_info_endpoints = {
            IntegrationType.SLACK: {
                "url": "https://slack.com/api/auth.test",
                "headers": {"Authorization": f"Bearer {access_token}"}
            },
            IntegrationType.GOOGLE: {
                "url": "https://www.googleapis.com/oauth2/v2/userinfo",
                "headers": {"Authorization": f"Bearer {access_token}"}
            },
            IntegrationType.GITHUB: {
                "url": "https://api.github.com/user",
                "headers": {"Authorization": f"Bearer {access_token}"}
            }
        }
        
        config = user_info_endpoints.get(integration_type)
        if not config:
            return {}
        
        response = await self.http_client.get(config["url"], headers=config["headers"])
        response.raise_for_status()
        
        return response.json()
    
    async def execute_action(self, user_id: str, integration_type: IntegrationType, action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an action on an integration"""
        # Get user's integration
        integration_doc = await self.db.integrations.find_one({
            "user_id": user_id,
            "integration_type": integration_type,
            "status": IntegrationStatus.ACTIVE
        })
        
        if not integration_doc:
            raise Exception(f"No active {integration_type} integration found")
        
        integration = Integration(**integration_doc)
        access_token = decrypt_oauth_token(integration.access_token)
        
        # Route to appropriate action handler
        if integration_type == IntegrationType.SLACK:
            return await self._execute_slack_action(access_token, action, parameters)
        elif integration_type == IntegrationType.GOOGLE:
            return await self._execute_google_action(access_token, action, parameters)
        elif integration_type == IntegrationType.GITHUB:
            return await self._execute_github_action(access_token, action, parameters)
        else:
            raise Exception(f"Action execution not implemented for {integration_type}")
    
    async def _execute_slack_action(self, access_token: str, action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute Slack actions"""
        headers = {"Authorization": f"Bearer {access_token}"}
        
        if action == "send_message":
            response = await self.http_client.post(
                "https://slack.com/api/chat.postMessage",
                headers=headers,
                json={
                    "channel": parameters["channel"],
                    "text": parameters["text"]
                }
            )
        elif action == "list_channels":
            response = await self.http_client.get(
                "https://slack.com/api/conversations.list",
                headers=headers
            )
        else:
            raise Exception(f"Unknown Slack action: {action}")
        
        response.raise_for_status()
        return response.json()
    
    async def _execute_google_action(self, access_token: str, action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute Google Workspace actions"""
        headers = {"Authorization": f"Bearer {access_token}"}
        
        if action == "send_email":
            # Gmail API implementation
            pass
        elif action == "list_emails":
            response = await self.http_client.get(
                "https://gmail.googleapis.com/gmail/v1/users/me/messages",
                headers=headers,
                params={"q": parameters.get("query", "")}
            )
            response.raise_for_status()
            return response.json()
        else:
            raise Exception(f"Unknown Google action: {action}")
    
    async def _execute_github_action(self, access_token: str, action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute GitHub actions"""
        headers = {"Authorization": f"Bearer {access_token}"}
        
        if action == "list_repos":
            response = await self.http_client.get(
                "https://api.github.com/user/repos",
                headers=headers
            )
        elif action == "create_issue":
            response = await self.http_client.post(
                f"https://api.github.com/repos/{parameters['owner']}/{parameters['repo']}/issues",
                headers=headers,
                json={
                    "title": parameters["title"],
                    "body": parameters["body"]
                }
            )
        else:
            raise Exception(f"Unknown GitHub action: {action}")
        
        response.raise_for_status()
        return response.json()
    
    async def delete_integration(self, user_id: str, integration_id: str) -> bool:
        """Delete user integration"""
        result = await self.db.integrations.delete_one({
            "id": integration_id,
            "user_id": user_id
        })
        return result.deleted_count > 0

integration_service = IntegrationService()