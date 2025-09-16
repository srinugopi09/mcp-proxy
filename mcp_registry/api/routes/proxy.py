"""
MCP Proxy endpoints for proxying requests to registered servers.
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from ...core.database import get_session
from ...services.proxy import ProxyService

router = APIRouter()

# Define reusable path parameters
ServerIdPath = Path(..., min_length=1, max_length=255, description="Server ID")
PromptNamePath = Path(..., min_length=1, max_length=255, description="Prompt name")
ResourceUriPath = Path(..., min_length=1, description="Resource URI")


class ProxyRequest(BaseModel):
    """Generic proxy request model."""
    method: str
    params: Optional[Dict[str, Any]] = None


class ToolCallRequest(BaseModel):
    """Tool call request model."""
    tool_name: str
    arguments: Dict[str, Any]


@router.post("/{server_id}/rpc")
async def proxy_rpc_request(
    request: ProxyRequest,
    server_id: str = ServerIdPath,
    session: AsyncSession = Depends(get_session)
) -> Dict[str, Any]:
    """Proxy a generic JSON-RPC request to a registered MCP server."""
    service = ProxyService(session)
    result = await service.proxy_request(server_id, request.method, request.params)
    return result


@router.post("/{server_id}/tools/call")
async def call_tool(
    request: ToolCallRequest,
    server_id: str = ServerIdPath,
    session: AsyncSession = Depends(get_session)
) -> Dict[str, Any]:
    """Call a tool on a registered MCP server."""
    service = ProxyService(session)
    result = await service.call_tool(server_id, request.tool_name, request.arguments)
    return result


@router.get("/{server_id}/resources/{resource_uri:path}")
async def get_resource(
    server_id: str = ServerIdPath,
    resource_uri: str = ResourceUriPath,
    session: AsyncSession = Depends(get_session)
) -> Dict[str, Any]:
    """Get a resource from a registered MCP server."""
    service = ProxyService(session)
    result = await service.get_resource(server_id, resource_uri)
    return result


@router.get("/{server_id}/prompts/{prompt_name}")
async def get_prompt(
    server_id: str = ServerIdPath,
    prompt_name: str = PromptNamePath,
    arguments: Optional[str] = Query(None, description="JSON string of arguments"),
    session: AsyncSession = Depends(get_session)
) -> Dict[str, Any]:
    """Get a prompt from a registered MCP server."""
    service = ProxyService(session)
    
    # Parse arguments if provided
    parsed_args = None
    if arguments:
        import json
        try:
            parsed_args = json.loads(arguments)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in arguments parameter: {e}")
    
    result = await service.get_prompt(server_id, prompt_name, parsed_args)
    return result


@router.post("/{server_id}/initialize")
async def initialize_server(
    server_id: str = ServerIdPath,
    session: AsyncSession = Depends(get_session)
) -> Dict[str, Any]:
    """Initialize connection with a registered MCP server."""
    service = ProxyService(session)
    result = await service.initialize_server(server_id)
    return result