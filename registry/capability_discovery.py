"""
MCP Capability Discovery Service

Connects to MCP servers and discovers their capabilities (tools, resources, prompts).
Handles connection management, error handling, and capability caching.
"""

import asyncio
import json
import time
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple

from fastmcp.client import Client
from fastmcp.client.transports import SSETransport, StreamableHttpTransport, infer_transport
from fastmcp.utilities.logging import get_logger

from .models import ServerCapability, CapabilityDiscoveryResponse
from .database import Database

logger = get_logger(__name__)


class CapabilityDiscoveryService:
    """Service for discovering MCP server capabilities."""
    
    def __init__(self, database: Database):
        self.database = database
        self.discovery_timeout = 30  # seconds
    
    def _create_client(self, server_url: str, transport_type: str = "auto") -> Client:
        """Create MCP client for the given server URL."""
        if transport_type == "sse":
            transport = SSETransport(server_url)
        elif transport_type == "http":
            transport = StreamableHttpTransport(server_url)
        else:
            # Auto-detect transport based on URL
            transport = infer_transport(server_url)
        
        return Client(transport)
    
    async def discover_server_capabilities(
        self, 
        server_id: str, 
        server_url: str, 
        transport_type: str = "auto",
        timeout_seconds: int = None,
        force_refresh: bool = False
    ) -> CapabilityDiscoveryResponse:
        """
        Discover capabilities for a specific MCP server.
        
        Args:
            server_id: Server ID in the registry
            server_url: MCP server URL
            transport_type: Transport type (auto, http, sse)
            timeout_seconds: Discovery timeout
            force_refresh: Force refresh even if recently discovered
            
        Returns:
            CapabilityDiscoveryResponse with discovery results
        """
        start_time = time.time()
        timeout = timeout_seconds or self.discovery_timeout
        
        logger.info(f"Starting capability discovery for server {server_id} at {server_url}")
        
        try:
            # Check if we should skip discovery (not forced and recently discovered)
            if not force_refresh:
                recent_discovery = self._get_recent_successful_discovery(server_id)
                if recent_discovery:
                    logger.info(f"Skipping discovery for {server_id} - recently discovered")
                    existing_capabilities = self.database.get_server_capabilities(server_id)
                    
                    # Get server information for cached response
                    server = self.database.get_server(server_id)
                    cached_response = CapabilityDiscoveryResponse(
                        server_id=server_id,
                        status="cached",
                        capabilities_found=len(existing_capabilities),
                        discovery_time_ms=0,
                        capabilities=[ServerCapability(**cap.to_dict()) for cap in existing_capabilities]
                    )
                    
                    # Add server information if available
                    if server:
                        if server.server_name:
                            cached_response.server_name = server.server_name
                        if server.server_version:
                            cached_response.server_version = server.server_version
                        if server.protocol_version:
                            cached_response.protocol_version = server.protocol_version
                        if server.server_capabilities and server.server_capabilities != "{}":
                            try:
                                cached_response.server_capabilities = json.loads(server.server_capabilities)
                            except (json.JSONDecodeError, TypeError):
                                pass
                        if server.avg_response_time_ms:
                            cached_response.response_time_ms = server.avg_response_time_ms
                    
                    return cached_response
            
            # Create client and discover capabilities
            client = self._create_client(server_url, transport_type)
            capabilities = []
            server_info = {}
            
            async with client:
                # Capture server initialization information
                try:
                    # Get server info from initialization result
                    if hasattr(client, 'initialize_result') and client.initialize_result:
                        init_result = client.initialize_result
                        
                        # Extract server information
                        if hasattr(init_result, 'serverInfo') and init_result.serverInfo:
                            server_info['server_name'] = getattr(init_result.serverInfo, 'name', None)
                            server_info['server_version'] = getattr(init_result.serverInfo, 'version', None)
                        
                        # Extract protocol version
                        if hasattr(init_result, 'protocolVersion'):
                            server_info['protocol_version'] = init_result.protocolVersion
                        
                        # Extract server capabilities
                        if hasattr(init_result, 'capabilities') and init_result.capabilities:
                            server_capabilities = {}
                            caps = init_result.capabilities
                            
                            # Check for various capability flags
                            if hasattr(caps, 'logging'):
                                server_capabilities['logging'] = True
                            if hasattr(caps, 'prompts'):
                                server_capabilities['prompts'] = True
                            if hasattr(caps, 'resources'):
                                server_capabilities['resources'] = True
                            if hasattr(caps, 'tools'):
                                server_capabilities['tools'] = True
                            if hasattr(caps, 'experimental'):
                                server_capabilities['experimental'] = getattr(caps, 'experimental', {})
                            
                            server_info['server_capabilities'] = server_capabilities
                        
                        logger.info(f"Captured server info for {server_id}: {server_info}")
                    
                    # Test server responsiveness with ping
                    ping_start = time.time()
                    try:
                        await client.ping()
                        ping_time_ms = int((time.time() - ping_start) * 1000)
                        server_info['response_time_ms'] = ping_time_ms
                        logger.info(f"Server {server_id} ping: {ping_time_ms}ms")
                    except Exception as e:
                        logger.warning(f"Ping failed for {server_id}: {e}")
                        
                except Exception as e:
                    logger.warning(f"Failed to capture server info for {server_id}: {e}")
                # Discover tools
                try:
                    tools = await client.list_tools()
                    for tool in tools:
                        capability = ServerCapability(
                            server_id=server_id,
                            type="tool",
                            name=tool.name,
                            description=tool.description,
                            input_schema=tool.inputSchema if hasattr(tool, 'inputSchema') else None,
                            output_schema=tool.outputSchema if hasattr(tool, 'outputSchema') else None,
                        )
                        capabilities.append(capability)
                    logger.info(f"Discovered {len(tools)} tools for server {server_id}")
                except Exception as e:
                    logger.warning(f"Failed to discover tools for {server_id}: {e}")
                
                # Discover resources
                try:
                    resources = await client.list_resources()
                    for resource in resources:
                        capability = ServerCapability(
                            server_id=server_id,
                            type="resource",
                            name=resource.name or str(resource.uri),
                            description=resource.description,
                            uri_template=str(resource.uri),
                        )
                        capabilities.append(capability)
                    logger.info(f"Discovered {len(resources)} resources for server {server_id}")
                except Exception as e:
                    logger.warning(f"Failed to discover resources for {server_id}: {e}")
                
                # Discover resource templates
                try:
                    templates = await client.list_resource_templates()
                    for template in templates:
                        capability = ServerCapability(
                            server_id=server_id,
                            type="resource_template",
                            name=template.name or template.uriTemplate,
                            description=template.description,
                            uri_template=template.uriTemplate,
                        )
                        capabilities.append(capability)
                    logger.info(f"Discovered {len(templates)} resource templates for server {server_id}")
                except Exception as e:
                    logger.warning(f"Failed to discover resource templates for {server_id}: {e}")
                
                # Discover prompts
                try:
                    prompts = await client.list_prompts()
                    for prompt in prompts:
                        # Convert prompt arguments to input schema
                        input_schema = {}
                        if hasattr(prompt, 'arguments') and prompt.arguments:
                            properties = {}
                            required = []
                            for arg in prompt.arguments:
                                properties[arg.name] = {
                                    "type": "string",  # Default type
                                    "description": arg.description or ""
                                }
                                if getattr(arg, 'required', False):
                                    required.append(arg.name)
                            
                            input_schema = {
                                "type": "object",
                                "properties": properties,
                                "required": required
                            }
                        
                        capability = ServerCapability(
                            server_id=server_id,
                            type="prompt",
                            name=prompt.name,
                            description=prompt.description,
                            input_schema=input_schema if input_schema else None,
                        )
                        capabilities.append(capability)
                    logger.info(f"Discovered {len(prompts)} prompts for server {server_id}")
                except Exception as e:
                    logger.warning(f"Failed to discover prompts for {server_id}: {e}")
            
            # Store capabilities in database
            stored_count = self.database.store_capabilities(server_id, capabilities)
            discovery_time_ms = int((time.time() - start_time) * 1000)
            
            # Update server information if captured
            if server_info:
                try:
                    self.database.update_server_info(
                        server_id=server_id,
                        server_name=server_info.get('server_name'),
                        server_version=server_info.get('server_version'),
                        protocol_version=server_info.get('protocol_version'),
                        server_capabilities=server_info.get('server_capabilities'),
                        response_time_ms=server_info.get('response_time_ms')
                    )
                    logger.info(f"Updated server info for {server_id}")
                except Exception as e:
                    logger.warning(f"Failed to update server info for {server_id}: {e}")
            
            # Update discovery statistics
            try:
                # Increment discovery counters
                with self.database._get_cursor() as cursor:
                    cursor.execute("""
                        UPDATE servers 
                        SET total_discoveries = COALESCE(total_discoveries, 0) + 1,
                            successful_discoveries = COALESCE(successful_discoveries, 0) + 1,
                            updated_at = ?
                        WHERE id = ?
                    """, (datetime.utcnow(), server_id))
            except Exception as e:
                logger.warning(f"Failed to update discovery statistics for {server_id}: {e}")
            
            # Record successful discovery
            self.database.record_discovery_attempt(
                server_id=server_id,
                status="success",
                capabilities_found=stored_count,
                discovery_time_ms=discovery_time_ms
            )
            
            logger.info(f"Successfully discovered {stored_count} capabilities for server {server_id} in {discovery_time_ms}ms")
            
            # Create enhanced response with server information
            response = CapabilityDiscoveryResponse(
                server_id=server_id,
                status="success",
                capabilities_found=stored_count,
                discovery_time_ms=discovery_time_ms,
                capabilities=capabilities
            )
            
            # Add server information if captured
            if server_info:
                response.server_info = server_info
                response.server_name = server_info.get('server_name')
                response.server_version = server_info.get('server_version')
                response.protocol_version = server_info.get('protocol_version')
                response.server_capabilities = server_info.get('server_capabilities')
                response.response_time_ms = server_info.get('response_time_ms')
            
            return response
            
        except asyncio.TimeoutError:
            discovery_time_ms = int((time.time() - start_time) * 1000)
            error_msg = f"Discovery timeout after {timeout} seconds"
            
            # Update discovery statistics (failed attempt)
            try:
                with self.database._get_cursor() as cursor:
                    cursor.execute("""
                        UPDATE servers 
                        SET total_discoveries = COALESCE(total_discoveries, 0) + 1,
                            updated_at = ?
                        WHERE id = ?
                    """, (datetime.utcnow(), server_id))
            except Exception as e:
                logger.warning(f"Failed to update discovery statistics for {server_id}: {e}")
            
            self.database.record_discovery_attempt(
                server_id=server_id,
                status="failed",
                error_message=error_msg,
                discovery_time_ms=discovery_time_ms
            )
            
            logger.error(f"Discovery timeout for server {server_id}: {error_msg}")
            
            return CapabilityDiscoveryResponse(
                server_id=server_id,
                status="failed",
                capabilities_found=0,
                discovery_time_ms=discovery_time_ms,
                error_message=error_msg
            )
            
        except Exception as e:
            discovery_time_ms = int((time.time() - start_time) * 1000)
            error_msg = f"Discovery failed: {str(e)}"
            
            # Update discovery statistics (failed attempt)
            try:
                with self.database._get_cursor() as cursor:
                    cursor.execute("""
                        UPDATE servers 
                        SET total_discoveries = COALESCE(total_discoveries, 0) + 1,
                            updated_at = ?
                        WHERE id = ?
                    """, (datetime.utcnow(), server_id))
            except Exception as e:
                logger.warning(f"Failed to update discovery statistics for {server_id}: {e}")
            
            self.database.record_discovery_attempt(
                server_id=server_id,
                status="failed",
                error_message=error_msg,
                discovery_time_ms=discovery_time_ms
            )
            
            logger.error(f"Discovery failed for server {server_id}: {error_msg}")
            
            return CapabilityDiscoveryResponse(
                server_id=server_id,
                status="failed",
                capabilities_found=0,
                discovery_time_ms=discovery_time_ms,
                error_message=error_msg
            )
    
    def _get_recent_successful_discovery(self, server_id: str, max_age_minutes: int = 60) -> bool:
        """Check if server has been successfully discovered recently."""
        try:
            history = self.database.get_discovery_history(server_id, limit=1)
            if not history:
                return False
            
            latest = history[0]
            if latest.status != "success":
                return False
            
            # Check if discovery is recent enough
            age_minutes = (datetime.utcnow() - latest.discovered_at).total_seconds() / 60
            return age_minutes < max_age_minutes
            
        except Exception as e:
            logger.warning(f"Failed to check recent discovery for {server_id}: {e}")
            return False
    
    async def discover_multiple_servers(
        self, 
        server_configs: List[Tuple[str, str, str]], 
        max_concurrent: int = 5
    ) -> List[CapabilityDiscoveryResponse]:
        """
        Discover capabilities for multiple servers concurrently.
        
        Args:
            server_configs: List of (server_id, server_url, transport_type) tuples
            max_concurrent: Maximum concurrent discoveries
            
        Returns:
            List of CapabilityDiscoveryResponse objects
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def discover_with_semaphore(server_id: str, server_url: str, transport_type: str):
            async with semaphore:
                return await self.discover_server_capabilities(server_id, server_url, transport_type)
        
        tasks = [
            discover_with_semaphore(server_id, server_url, transport_type)
            for server_id, server_url, transport_type in server_configs
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to failed responses
        responses = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                server_id, server_url, transport_type = server_configs[i]
                responses.append(CapabilityDiscoveryResponse(
                    server_id=server_id,
                    status="failed",
                    capabilities_found=0,
                    discovery_time_ms=0,
                    error_message=str(result)
                ))
            else:
                responses.append(result)
        
        return responses
    
    def get_server_capabilities_summary(self, server_id: str) -> Dict[str, Any]:
        """Get a summary of server capabilities by type."""
        capabilities = self.database.get_server_capabilities(server_id)
        
        summary = {
            "total": len(capabilities),
            "by_type": {},
            "last_discovery": None
        }
        
        # Count by type
        for cap in capabilities:
            cap_type = cap.type
            if cap_type not in summary["by_type"]:
                summary["by_type"][cap_type] = 0
            summary["by_type"][cap_type] += 1
        
        # Get last discovery time
        history = self.database.get_discovery_history(server_id, limit=1)
        if history:
            summary["last_discovery"] = history[0].discovered_at
        
        return summary