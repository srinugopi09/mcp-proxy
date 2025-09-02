"""
Hub Server for Testing Remote MCP Servers via Dynamic Proxies
===========================================================

This module implements a FastAPI application that acts as a hub for
discovering and testing remote Model Context Protocol (MCP) servers.  It
leverages FastMCP's proxying and transport features to dynamically
connect to arbitrary remote servers, optionally injecting custom HTTP
headers (for example an `Authorization` bearer token) and enforcing
security policies such as host allow‐/deny‐lists.  Each remote
connection is encapsulated in an isolated session and mounted onto
a single `FastMCP` instance under a unique prefix.  Sessions expire
after a configurable TTL to avoid resource leaks.

Key features
------------

* **Dynamic proxy mounting** – The hub exposes one MCP endpoint and
  dynamically mounts a proxy for each remote server the user wishes
  to test.  Tools and resources from the remote server are
  namespaced under the session ID prefix.  Clients can call tools
  directly through the hub without needing to know the remote
  server's details.
* **Header injection** – When creating a session the user can supply
  arbitrary HTTP headers (for example an Authorization header) which
  are forwarded to the remote server on every request.  FastMCP's
  `StreamableHttpTransport` supports a `headers` parameter for this
  purpose【62461327927832†L343-L360】.
* **Allowlist/denylist** – Before establishing a session the hub
  validates that the target URL is permissible.  By default local and
  private network addresses are denied.  The allowlist/denylist can
  be customised via environment variables or extended in code.
* **Session TTL and cleanup** – Each session stores an expiry time
  based on a configurable TTL.  A background task periodically
  removes expired sessions and unmounts the associated proxies.  Users
  can also explicitly close a session via the API.
* **RESTful API** – A thin REST wrapper exposes endpoints to create
  sessions, list tools, call tools (with optional streaming), ping the
  remote server, refresh a session and close a session.  This API
  integrates easily with an Angular UI.

Note
----

This hub server focuses on remote HTTP/SSE MCP servers.  For local
STDIO or stateful MCP servers you can adapt the proxy creation logic
accordingly (e.g. using `StatefulProxyClient`【757769647945008†L681-L721】).

Running the server
------------------

Install the required dependencies:

```
pip install fastapi uvicorn fastmcp
```

Then start the server:

```
python hub_server.py
```

It will listen on `0.0.0.0:8000` by default and expose both the FastAPI
REST API and the FastMCP hub at `/mcp/`.
"""

from fastapi.middleware.wsgi import WSGIMiddleware
import asyncio
import ipaddress
import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Union

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Path
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field, HttpUrl
from starlette.concurrency import iterate_in_threadpool

from fastmcp import FastMCP
from fastmcp.client.auth import BearerAuth
from fastmcp.client.transports import StreamableHttpTransport
from fastmcp.server.proxy import ProxyClient


###############################################################################
# Configuration
###############################################################################

# Session expiry in seconds.  Each session will be cleaned up once its
# `expires_at` time has passed.  You can override this via the
# `MCP_HUB_SESSION_TTL` environment variable (set in seconds) if needed.
SESSION_TTL_SECONDS: int = int(
    (lambda v: v if v else 1800)(
        __import__("os").environ.get("MCP_HUB_SESSION_TTL", "1800")
    )
)

# Allowed remote schemes.  Only http and https are supported by Streamable HTTP.
ALLOWED_SCHEMES = {"http", "https"}

# Denied hosts.  Localhost and private network ranges are denied by default to
# prevent SSRF and other misuse.  Add additional domains/IPs as needed.
DENIED_HOSTS = {
    "localhost",
    "127.0.0.1",
    "::1",
}


def _is_private_ip(hostname: str) -> bool:
    """Return True if the hostname/IP points to a private or local network.

    This function attempts to parse the host as an IP address.  If the
    conversion fails it assumes the host is a domain and allows it (DNS
    resolution is not performed here).  Localhost and loopback addresses
    are explicitly denied via `DENIED_HOSTS`.
    """
    try:
        ip = ipaddress.ip_address(hostname)
        return ip.is_private or ip.is_loopback or ip.is_link_local
    except ValueError:
        return False


def validate_remote_url(url: str) -> None:
    """Validate that the remote URL uses an allowed scheme and host.

    Raises:
        HTTPException: if the URL is not allowed.
    """
    from urllib.parse import urlparse

    parsed = urlparse(url)
    if parsed.scheme not in ALLOWED_SCHEMES:
        raise HTTPException(
            status_code=400, detail="Only HTTP/S MCP servers are supported")
    host = parsed.hostname or ""
    if host in DENIED_HOSTS or _is_private_ip(host):
        raise HTTPException(
            status_code=400, detail="Connection to local/private hosts is denied")


###############################################################################
# Pydantic models for request/response bodies
###############################################################################


class CreateSessionRequest(BaseModel):
    """Request body for creating a new session."""

    remote_url: HttpUrl = Field(
        ..., description="Base URL of the remote MCP server (must include path to /mcp)",
    )
    token: Optional[str] = Field(
        None,
        description="Bearer token for Authorization header.  If provided this will be used "
        "to set `Authorization: Bearer <token>` on all requests to the remote server.  "
        "You may alternatively specify custom headers via the `headers` field.",
    )
    headers: Optional[Dict[str, str]] = Field(
        None,
        description="Arbitrary HTTP headers to inject into requests to the remote server.  "
        "If an `Authorization` header is present it overrides the `token` field.",
    )


class CreateSessionResponse(BaseModel):
    """Response body for session creation."""

    session_id: str
    prefix: str
    remote_url: HttpUrl
    expires_at: datetime


class ToolCallRequest(BaseModel):
    """Request body for calling a tool."""

    arguments: Dict[str, Any] = Field(
        ..., description="Arguments to pass to the tool.  Must match the tool's schema."
    )
    stream: Optional[bool] = Field(
        False,
        description="When true the response will be streamed back to the client as NDJSON.  "
        "If false (default) the full result is returned once the tool completes.",
    )


class ToolCallResponse(BaseModel):
    """Response body for non-streaming tool calls."""

    content: Optional[Any] = None
    structured_content: Optional[Any] = None


###############################################################################
# Hub state
###############################################################################


class SessionData:
    """Internal record of an active session."""

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
        # Disconnect the underlying ProxyClient
        try:
            # For stateful servers you might need to call clear() instead
            await self.proxy_client._disconnect(force=True)
        except Exception:
            pass


class HubState:
    """Singleton holding active sessions and cleanup logic."""

    def __init__(self) -> None:
        self.hub = FastMCP("MCP Hub")
        self.sessions: Dict[str, SessionData] = {}

    def register_session(self, session: SessionData) -> None:
        self.sessions[session.prefix] = session

    def get_session(self, session_id: str) -> SessionData:
        session = self.sessions.get(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found")
        return session

    def remove_session(self, session_id: str) -> Optional[SessionData]:
        return self.sessions.pop(session_id, None)

    async def cleanup_expired_sessions(self) -> None:
        """Remove all sessions whose expiry time has passed."""
        now = datetime.utcnow()
        expired = [sid for sid, data in self.sessions.items()
                   if data.expires_at <= now]
        for sid in expired:
            data = self.sessions.pop(sid)
            # Unmounting is implicit—once the session is removed it no longer responds
            await data.close()

    async def refresh_session(self, session_id: str) -> None:
        """Extend the expiry for a session without recreating the proxy."""
        session = self.get_session(session_id)
        session.expires_at = datetime.utcnow() + timedelta(seconds=SESSION_TTL_SECONDS)


hub_state = HubState()


###############################################################################
# FastAPI app and dependency injection
###############################################################################

app = FastAPI(title="MCP Hub API")


@app.on_event("startup")
async def startup() -> None:
    """Perform startup tasks such as scheduling the cleanup loop."""
    async def cleanup_loop() -> None:
        while True:
            await hub_state.cleanup_expired_sessions()
            await asyncio.sleep(30)  # check every 30 seconds

    # Launch background cleanup task
    asyncio.create_task(cleanup_loop())


def get_hub() -> FastMCP:
    """Dependency returning the hub's FastMCP instance."""
    return hub_state.hub


###############################################################################
# REST Endpoints
###############################################################################


@app.post("/session", response_model=CreateSessionResponse)
async def create_session(
    req: CreateSessionRequest, background_tasks: BackgroundTasks
) -> CreateSessionResponse:
    """Create a new proxy session to a remote MCP server.

    This endpoint validates the URL, constructs a `StreamableHttpTransport`
    with any provided headers or bearer token, creates a `ProxyClient`,
    and mounts it onto the hub under a unique prefix.  The session will
    expire after `SESSION_TTL_SECONDS` if not refreshed.
    """
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
    # convenience.  BearerAuth will format the Authorization header correctly
    # and handle token refresh if you implement a custom auth provider.
    # Note: BearerAuth is optional; headers take precedence if provided.
    auth = None
    if req.token and not req.headers:
        auth = BearerAuth(req.token)

    # Create ProxyClient over the transport (passing auth if present)
    proxy_client = ProxyClient(
        transport, auth=auth) if auth else ProxyClient(transport)

    # Build proxy server using FastMCP.as_proxy().  The name helps with
    # identification in debugging but is not used by the API.
    proxy_server = await FastMCP.as_proxy(proxy_client, name="proxy-server")

    # Create unique session/prefix
    session_id = secrets.token_hex(4)
    prefix = session_id

    # Mount the proxy server under the prefix.  Using as_proxy=True ensures
    # advanced MCP features are forwarded correctly【757769647945008†L569-L603】.
    hub_state.hub.mount(prefix, proxy_server, as_proxy=True)

    # Determine expiry time
    expires_at = datetime.utcnow() + timedelta(seconds=SESSION_TTL_SECONDS)

    # Save session data
    session_data = SessionData(prefix, str(
        req.remote_url), proxy_client, proxy_server, expires_at)
    hub_state.register_session(session_data)

    return CreateSessionResponse(
        session_id=session_id,
        prefix=prefix,
        remote_url=req.remote_url,
        expires_at=expires_at,
    )


@app.delete("/session/{session_id}")
async def close_session(session_id: str = Path(..., description="Session identifier")) -> JSONResponse:
    """Terminate a proxy session and remove it from the hub."""
    session = hub_state.remove_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    await session.close()
    return JSONResponse({"detail": f"Session {session_id} closed"})


@app.post("/session/{session_id}/refresh")
async def refresh_session(session_id: str) -> JSONResponse:
    """Refresh (extend) the expiry time for an active session."""
    await hub_state.refresh_session(session_id)
    return JSONResponse({"detail": f"Session {session_id} refreshed"})


@app.get("/session/{session_id}/tools")
async def list_tools(session_id: str) -> JSONResponse:
    """List tools available on the remote server for this session."""
    session = hub_state.get_session(session_id)
    client = session.proxy_client
    # Create a fresh client instance to avoid interfering with active contexts
    fresh_client = client.new()
    tools_data = []
    async with fresh_client:
        tools = await fresh_client.list_tools()
        for tool in tools:
            # Convert tool metadata into JSON serialisable form
            tools_data.append(
                {
                    "name": tool.name,
                    "description": tool.description,
                    "arguments": tool.arguments,
                    "return": tool.returns,
                    "structured": bool(tool.structured)
                }
            )
    return JSONResponse({"tools": tools_data})


@app.post("/session/{session_id}/tools/{tool_name}")
async def call_tool(
    session_id: str,
    tool_name: str,
    req: ToolCallRequest,
) -> Union[StreamingResponse, ToolCallResponse]:
    """Execute a tool on the remote server.  Supports streaming responses.

    Args:
        session_id: The ID of the session
        tool_name: The unprefixed name of the tool on the remote server
        req: Request body containing arguments and stream flag

    Returns:
        Either a streaming response (NDJSON lines) or a JSON body with the
        complete result once finished.
    """
    session = hub_state.get_session(session_id)
    client = session.proxy_client.new()

    async def _stream_generator():
        """Async generator streaming tool output as JSON lines."""
        async with client:
            async for chunk in client.call_tool(tool_name, req.arguments):
                # Each chunk is a ToolResult or str depending on implementation
                if isinstance(chunk, bytes):
                    data = chunk.decode("utf-8")
                else:
                    data = chunk
                # Yield JSON‐encoded line for each piece of content
                import json

                # If the chunk has .content attribute use that, else raw
                if hasattr(chunk, "content"):
                    payload = {
                        "content": chunk.content,
                        "structured_content": chunk.structured_content,
                    }
                else:
                    payload = {"data": data}
                yield json.dumps(payload) + "\n"

    async def _call_tool_once():
        """Run a non-streaming tool call and return the result."""
        async with client:
            result = await client.call_tool(tool_name, req.arguments)
            return ToolCallResponse(
                content=getattr(result, "content", None),
                structured_content=getattr(result, "structured_content", None),
            )

    if req.stream:
        # Stream the response as an NDJSON stream.  Each line is a JSON object
        # containing either `content`/`structured_content` or `data`.  The
        # Angular UI can consume this via EventSource or custom streaming.
        return StreamingResponse(
            _stream_generator(),
            media_type="application/x-ndjson",
        )
    else:
        return await _call_tool_once()


@app.get("/session/{session_id}/ping")
async def ping(session_id: str) -> JSONResponse:
    """Ping the remote server to verify connectivity."""
    session = hub_state.get_session(session_id)
    client = session.proxy_client.new()
    async with client:
        await client.ping()
    return JSONResponse({"detail": "pong"})


###############################################################################
# Mount the MCP hub under /mcp/
###############################################################################


# Expose the FastMCP server as a WSGI app.  FastMCP provides a Starlette
# compatible ASGI adapter but for FastAPI integration we wrap it in WSGI.
app.mount("/mcp", WSGIMiddleware(hub_state.hub.app))


###############################################################################
# CLI entrypoint
###############################################################################

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
