"""Session management for MCP Proxy Hub."""

import asyncio
import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from fastapi import HTTPException
from fastmcp import FastMCP
from fastmcp.client.auth import BearerAuth
from fastmcp.client.transports import StreamableHttpTransport
from fastmcp.server.proxy import ProxyClient

from .config import settings
from .models import CreateSessionRequest, CreateSessionResponse
from .security import validate_remote_url


class SessionData:
    """Internal record of an active server connection."""

    def __init__(
        self,
        prefix: str,
        remote_url: str,
        proxy_client: ProxyClient,
        proxy_server: FastMCP,
        expires_at: datetime,
    ) -> None:
        self.prefix = prefix
        self.remote_url = remote_url
        self.proxy_client = proxy_client
        self.proxy_server = proxy_server
        self.expires_at = expires_at

    async def close(self) -> None:
        """Disconnect the proxy client and clear stateful caches."""
        try:
            # For stateful servers you might need to call clear() instead
            await self.proxy_client._disconnect(force=True)
        except Exception:
            pass


class HubState:
    """Singleton holding active server connections and cleanup logic."""

    def __init__(self) -> None:
        self.hub = FastMCP("MCP Hub")
        self.sessions: Dict[str, SessionData] = {}
        self._cleanup_task: Optional[asyncio.Task] = None

    def register_session(self, session: SessionData) -> None:
        """Register a new server connection."""
        self.sessions[session.prefix] = session

    def get_session(self, server_id: str) -> SessionData:
        """Get a server connection by ID, raising HTTPException if not found."""
        session = self.sessions.get(server_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Server connection not found")
        return session

    def remove_session(self, server_id: str) -> Optional[SessionData]:
        """Remove and return a server connection by ID."""
        return self.sessions.pop(server_id, None)

    async def cleanup_expired_sessions(self) -> None:
        """Remove all server connections whose expiry time has passed."""
        now = datetime.utcnow()
        expired = [
            sid for sid, data in self.sessions.items() 
            if data.expires_at <= now
        ]
        for sid in expired:
            data = self.sessions.pop(sid)
            # Unmounting is implicit—once the session is removed it no longer responds
            await data.close()

    async def refresh_session(self, server_id: str) -> datetime:
        """Extend the expiry for a server connection without recreating the proxy."""
        session = self.get_session(server_id)
        new_expires_at = datetime.utcnow() + timedelta(seconds=settings.session_ttl_seconds)
        session.expires_at = new_expires_at
        return new_expires_at

    async def get_session_capabilities(self, server_id: str) -> Dict[str, Any]:
        """Get capabilities for a specific server connection."""
        session = self.get_session(server_id)
        client = session.proxy_client.new()
        
        capabilities = {
            "tools": [],
            "resources": [],
            "prompts": [],
            "server_info": {
                "server_id": server_id,
                "remote_url": session.remote_url,
                "expires_at": session.expires_at.isoformat()
            }
        }
        
        async with client:
            # Try to get tools
            try:
                tools = await client.list_tools()
                capabilities["tools"] = [
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "arguments": tool.arguments,
                        "returns": tool.returns,
                        "structured": bool(tool.structured)
                    }
                    for tool in tools
                ]
            except (AttributeError, Exception):
                pass
            
            # Try to get resources
            try:
                resources = await client.list_resources()
                capabilities["resources"] = [
                    {
                        "uri": resource.uri,
                        "name": resource.name,
                        "description": resource.description,
                        "mimeType": resource.mimeType
                    }
                    for resource in resources
                ]
            except (AttributeError, Exception):
                pass
            
            # Try to get prompts
            try:
                prompts = await client.list_prompts()
                capabilities["prompts"] = [
                    {
                        "name": prompt.name,
                        "description": prompt.description,
                        "arguments": prompt.arguments
                    }
                    for prompt in prompts
                ]
            except (AttributeError, Exception):
                pass
        
        return capabilities

    async def start_cleanup_task(self) -> None:
        """Start the background cleanup task."""
        if self._cleanup_task is not None:
            return
            
        async def cleanup_loop() -> None:
            while True:
                await self.cleanup_expired_sessions()
                await asyncio.sleep(settings.cleanup_interval_seconds)

        self._cleanup_task = asyncio.create_task(cleanup_loop())

    async def stop_cleanup_task(self) -> None:
        """Stop the background cleanup task."""
        if self._cleanup_task is not None:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None

    async def create_session(self, req: CreateSessionRequest) -> CreateSessionResponse:
        """Create a new proxy connection to a remote MCP server."""
        # Validate remote URL
        validate_remote_url(str(req.remote_url))

        # Build headers dictionary from token/headers
        headers: Dict[str, str] = {}
        if req.headers:
            # Use provided headers first
            headers.update(req.headers)
        if req.token and "Authorization" not in headers:
            headers["Authorization"] = f"Bearer {req.token}"

        # Construct transport with optional headers
        transport_kwargs: Dict[str, Any] = {"url": str(req.remote_url)}
        if headers:
            transport_kwargs["headers"] = headers

        transport = StreamableHttpTransport(**transport_kwargs)

        # If only a bearer token is provided we can also use BearerAuth for
        # convenience. BearerAuth will format the Authorization header correctly
        # and handle token refresh if you implement a custom auth provider.
        # Note: BearerAuth is optional; headers take precedence if provided.
        auth = None
        if req.token and not req.headers:
            auth = BearerAuth(req.token)

        # Create ProxyClient over the transport (passing auth if present)
        proxy_client = ProxyClient(transport, auth=auth) if auth else ProxyClient(transport)

        # Build proxy server using FastMCP.as_proxy(). The name helps with
        # identification in debugging but is not used by the API.
        proxy_server = await FastMCP.as_proxy(proxy_client, name="proxy-server")

        # Create unique session/prefix
        session_id = secrets.token_hex(4)
        prefix = session_id

        # Mount the proxy server under the prefix. Using as_proxy=True ensures
        # advanced MCP features are forwarded correctly.
        self.hub.mount(prefix, proxy_server, as_proxy=True)

        # Determine expiry time
        expires_at = datetime.utcnow() + timedelta(seconds=settings.session_ttl_seconds)

        # Save session data
        session_data = SessionData(
            prefix, str(req.remote_url), proxy_client, proxy_server, expires_at
        )
        self.register_session(session_data)

        return CreateSessionResponse(
            session_id=session_id,
            prefix=prefix,
            remote_url=req.remote_url,
            expires_at=expires_at,
        )


# Global hub state instance
hub_state = HubState()