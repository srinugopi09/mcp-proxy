# MCP Proxy Hub Architecture

## Overview

The MCP Proxy Hub is designed with a modular architecture that separates concerns and provides a clean, maintainable codebase. The application acts as a dynamic proxy hub for Model Context Protocol (MCP) servers.

## Architecture Patterns

### Hub-and-Spoke Model
- **Central Hub**: Single FastMCP hub that manages all proxy connections
- **Dynamic Proxies**: Each remote MCP server connection is proxied through an isolated session
- **Session Isolation**: Each connection is encapsulated with unique prefixes to prevent interference

### Modular Design
The codebase is organized into focused modules:

```
src/mcp_proxy_hub/
├── __init__.py          # Package initialization and exports
├── app.py              # FastAPI application factory
├── config.py           # Configuration management
├── main.py             # CLI entry point
├── models.py           # Pydantic data models
├── routes.py           # API route handlers
├── security.py         # Security validation utilities
└── session.py          # Session management logic
```

## Core Components

### Configuration (`config.py`)
- **Environment-based**: Uses Pydantic BaseSettings for environment variable support
- **Type Safety**: All configuration options are typed and validated
- **Defaults**: Sensible defaults for all settings
- **Security**: Built-in security configurations (denied hosts, allowed schemes)

### Security (`security.py`)
- **URL Validation**: Prevents SSRF attacks by validating remote URLs
- **Private Network Blocking**: Blocks access to local/private networks by default
- **Scheme Validation**: Only allows HTTP/HTTPS schemes
- **Configurable Policies**: Security policies can be customized via configuration

### Session Management (`session.py`)
- **Session Lifecycle**: Manages creation, expiry, and cleanup of proxy sessions
- **TTL-based Expiry**: Sessions automatically expire after configurable time
- **Background Cleanup**: Periodic cleanup task removes expired sessions
- **Resource Management**: Proper cleanup of proxy clients and connections

### API Routes (`routes.py`)
- **RESTful Design**: Clean REST API for session and tool management
- **Streaming Support**: NDJSON streaming for real-time tool execution
- **Error Handling**: Proper HTTP error responses with meaningful messages
- **Type Safety**: Full Pydantic model validation for requests/responses

### Models (`models.py`)
- **Request/Response Models**: Pydantic models for all API interactions
- **Type Safety**: Full type annotations and validation
- **Documentation**: Built-in API documentation via Pydantic field descriptions
- **Serialization**: Automatic JSON serialization/deserialization

## Key Features

### Dynamic Proxy Mounting
- Remote MCP servers are dynamically mounted under unique prefixes
- Each session gets its own isolated namespace
- Tools and resources are automatically namespaced
- No configuration required for new remote servers

### Header Injection
- Support for arbitrary HTTP headers on remote requests
- Bearer token authentication support
- Authorization header override capability
- Flexible authentication mechanisms

### Session Management
- Unique session IDs using cryptographically secure tokens
- Configurable TTL with automatic cleanup
- Session refresh capability to extend lifetime
- Graceful session termination

### Streaming Support
- Real-time tool execution with NDJSON streaming
- Non-blocking async generators
- Compatible with EventSource and custom streaming clients
- Fallback to synchronous responses

## Security Architecture

### SSRF Prevention
- URL scheme validation (HTTP/HTTPS only)
- Hostname/IP validation against deny lists
- Private network access blocking
- Configurable security policies

### Authentication
- Bearer token forwarding to remote servers
- Custom header injection support
- No credential storage (pass-through only)
- Flexible authentication mechanisms

### Resource Management
- Session-based resource isolation
- Automatic cleanup of expired sessions
- Connection pooling and management
- Memory leak prevention

## Integration Points

### FastAPI Integration
- Native FastAPI application with full OpenAPI support
- Automatic API documentation generation
- Type-safe request/response handling
- Middleware support for cross-cutting concerns

### FastMCP Integration
- Native MCP protocol support at `/mcp/` endpoint
- WSGI middleware integration
- Proxy mounting with advanced MCP features
- Stateful and stateless proxy support

### External Integrations
- Designed for Angular UI integration
- RESTful API for any HTTP client
- NDJSON streaming for real-time applications
- Native MCP protocol for MCP clients

## Deployment Considerations

### Environment Configuration
- All settings configurable via environment variables
- `.env` file support for development
- Production-ready defaults
- Docker-friendly configuration

### Scalability
- Async/await throughout for high concurrency
- Session-based architecture allows horizontal scaling
- Stateless design (sessions stored in memory)
- Background task management

### Monitoring
- Structured logging support
- Health check endpoints
- Session metrics available
- Error tracking and reporting

## Extension Points

### Custom Transports
- Pluggable transport layer
- Support for different MCP transport types
- Custom authentication mechanisms
- Protocol adapters

### Security Policies
- Configurable allow/deny lists
- Custom validation functions
- Pluggable security modules
- Audit logging support

### Session Storage
- Currently in-memory storage
- Extensible to Redis, database, etc.
- Session persistence options
- Distributed session management