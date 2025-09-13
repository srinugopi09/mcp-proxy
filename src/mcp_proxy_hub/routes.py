"""API routes for MCP Proxy Hub."""

import json
from datetime import datetime
from typing import Union

from fastapi import APIRouter, HTTPException, Path, Query
from fastapi.responses import JSONResponse, StreamingResponse

from .models import (
    CreateSessionRequest,
    CreateSessionResponse,
    ErrorResponse,
    PingResponse,
    SessionCloseResponse,
    SessionRefreshResponse,
    ToolCallRequest,
    ToolCallResponse,
    ToolInfo,
    ToolsListResponse,
)
from .session import hub_state

# Create router for session management
router = APIRouter()


@router.post("/server", response_model=CreateSessionResponse)
async def create_server_connection(req: CreateSessionRequest) -> CreateSessionResponse:
    """Create a new proxy session to a remote MCP server.

    This endpoint validates the URL, constructs a `StreamableHttpTransport`
    with any provided headers or bearer token, creates a `ProxyClient`,
    and mounts it onto the hub under a unique prefix. The session will
    expire after `SESSION_TTL_SECONDS` if not refreshed.
    """
    return await hub_state.create_session(req)


@router.delete("/server/{server_id}", response_model=SessionCloseResponse, responses={404: {"model": ErrorResponse}})
async def close_server_connection(
    server_id: str = Path(..., min_length=1, max_length=255, description="Server connection identifier")
) -> SessionCloseResponse:
    """Terminate a server connection and remove it from the hub."""
    session = hub_state.remove_session(server_id)
    if session is None:
        raise HTTPException(
            status_code=404, 
            detail={
                "error": "SERVER_NOT_FOUND",
                "message": f"Server connection with ID '{server_id}' not found",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    await session.close()
    return SessionCloseResponse(
        detail=f"Server connection {server_id} closed", 
        session_id=server_id
    )


@router.post("/server/{server_id}/refresh", response_model=SessionRefreshResponse)
async def refresh_server_connection(
    server_id: str = Path(..., min_length=1, max_length=255, description="Server connection identifier")
) -> SessionRefreshResponse:
    """Refresh (extend) the expiry time for an active server connection."""
    new_expires_at = await hub_state.refresh_session(server_id)
    return SessionRefreshResponse(
        detail=f"Server connection {server_id} refreshed",
        session_id=server_id,
        new_expires_at=new_expires_at,
    )


@router.get("/server/{server_id}/discover", response_model=ToolsListResponse)
async def discover_server_capabilities(
    server_id: str = Path(..., min_length=1, max_length=255, description="Server connection identifier")
) -> ToolsListResponse:
    """Discover capabilities (tools) for a specific server connection."""
    return await list_tools(server_id)


@router.get("/server/{server_id}/tools", response_model=ToolsListResponse)
async def list_tools(
    server_id: str = Path(..., min_length=1, max_length=255, description="Server connection identifier")
) -> ToolsListResponse:
    """List tools available on the remote server for this connection."""
    session = hub_state.get_session(server_id)
    client = session.proxy_client
    # Create a fresh client instance to avoid interfering with active contexts
    fresh_client = client.new()
    tools_data = []
    async with fresh_client:
        tools = await fresh_client.list_tools()
        for tool in tools:
            # Convert tool metadata into JSON serializable form
            tools_data.append(
                ToolInfo(
                    name=tool.name,
                    description=tool.description,
                    arguments=tool.arguments,
                    returns=tool.returns,
                    structured=bool(tool.structured),
                )
            )
    return ToolsListResponse(tools=tools_data, session_id=server_id)


@router.post("/server/{server_id}/tools/{tool_name}", response_model=None)
async def call_tool(
    req: ToolCallRequest,
    server_id: str = Path(..., min_length=1, max_length=255, description="Server connection identifier"),
    tool_name: str = Path(..., min_length=1, max_length=255, description="Tool name"),
) -> Union[StreamingResponse, ToolCallResponse]:
    """Execute a tool on the remote server. Supports streaming responses.

    Args:
        server_id: The ID of the server connection
        tool_name: The unprefixed name of the tool on the remote server
        req: Request body containing arguments and stream flag

    Returns:
        Either a streaming response (NDJSON lines) or a JSON body with the
        complete result once finished.
    """
    session = hub_state.get_session(server_id)
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
        # Stream the response as an NDJSON stream. Each line is a JSON object
        # containing either `content`/`structured_content` or `data`. The
        # Angular UI can consume this via EventSource or custom streaming.
        return StreamingResponse(
            _stream_generator(),
            media_type="application/x-ndjson",
        )
    else:
        return await _call_tool_once()


@router.get("/server/{server_id}/resources/{resource_uri:path}")
async def get_resource(
    server_id: str = Path(..., min_length=1, max_length=255, description="Server connection identifier"),
    resource_uri: str = Path(..., min_length=1, description="Resource URI")
) -> dict:
    """Get a resource from the remote MCP server."""
    session = hub_state.get_session(server_id)
    client = session.proxy_client.new()
    async with client:
        # Try to get resource if the client supports it
        try:
            resources = await client.list_resources()
            # Find the matching resource
            for resource in resources:
                if resource.uri == resource_uri:
                    result = await client.read_resource(resource_uri)
                    return {"resource_uri": resource_uri, "content": result}
            raise HTTPException(status_code=404, detail="Resource not found")
        except AttributeError:
            # Client doesn't support resources
            raise HTTPException(status_code=501, detail="Resources not supported by this server")


@router.get("/server/{server_id}/prompts/{prompt_name}")
async def get_prompt(
    server_id: str = Path(..., min_length=1, max_length=255, description="Server connection identifier"),
    prompt_name: str = Path(..., min_length=1, max_length=255, description="Prompt name"),
    arguments: str = Query(None, description="JSON string of arguments")
) -> dict:
    """Get a prompt from the remote MCP server."""
    session = hub_state.get_session(server_id)
    client = session.proxy_client.new()
    
    # Parse arguments if provided
    parsed_args = None
    if arguments:
        import json
        try:
            parsed_args = json.loads(arguments)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON in arguments")
    
    async with client:
        try:
            prompts = await client.list_prompts()
            # Find the matching prompt
            for prompt in prompts:
                if prompt.name == prompt_name:
                    result = await client.get_prompt(prompt_name, parsed_args or {})
                    return {"prompt_name": prompt_name, "content": result}
            raise HTTPException(status_code=404, detail="Prompt not found")
        except AttributeError:
            # Client doesn't support prompts
            raise HTTPException(status_code=501, detail="Prompts not supported by this server")


@router.post("/server/{server_id}/rpc")
async def proxy_rpc_request(
    request: dict,
    server_id: str = Path(..., min_length=1, max_length=255, description="Server connection identifier")
) -> dict:
    """Proxy a generic JSON-RPC request to the remote MCP server."""
    session = hub_state.get_session(server_id)
    client = session.proxy_client.new()
    
    method = request.get("method")
    params = request.get("params", {})
    
    if not method:
        raise HTTPException(status_code=400, detail="Method is required")
    
    async with client:
        try:
            # Use the generic call method if available
            if hasattr(client, 'call'):
                result = await client.call(method, params)
                return {"result": result}
            else:
                raise HTTPException(status_code=501, detail="Generic RPC not supported")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


@router.get("/server/{server_id}/ping", response_model=PingResponse)
async def ping(
    server_id: str = Path(..., min_length=1, max_length=255, description="Server connection identifier")
) -> PingResponse:
    """Ping the remote server to verify connectivity."""
    session = hub_state.get_session(server_id)
    client = session.proxy_client.new()
    async with client:
        await client.ping()
    return PingResponse(session_id=server_id)