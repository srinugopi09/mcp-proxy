# API Documentation

## Overview

The MCP Registry provides a RESTful API built with FastAPI for managing MCP servers and capabilities.

## Base URL

```
http://localhost:8000
```

## Authentication

Currently, the API does not require authentication. This will be added in future versions.

## Endpoints

### Health Checks

#### GET /health/
Returns the health status of the API.

**Response:**
```json
{
  "status": "healthy",
  "version": "2.0.0"
}
```

#### GET /health/ready
Returns the readiness status of the API.

**Response:**
```json
{
  "status": "ready",
  "version": "2.0.0"
}
```

### Server Management

#### GET /servers/
List all registered servers.

**Query Parameters:**
- `skip` (int): Number of records to skip (default: 0)
- `limit` (int): Maximum number of records to return (default: 100)

**Response:**
```json
[
  {
    "id": "uuid",
    "name": "Server Name",
    "url": "http://example.com/mcp",
    "description": "Server description",
    "tags": ["tag1", "tag2"],
    "transport": "http",
    "status": "unknown",
    "metadata": {},
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  }
]
```

#### POST /servers/
Register a new server.

**Request Body:**
```json
{
  "name": "Server Name",
  "url": "http://example.com/mcp",
  "description": "Server description",
  "tags": ["tag1", "tag2"],
  "transport": "http",
  "metadata": {}
}
```

**Response:**
```json
{
  "id": "uuid",
  "name": "Server Name",
  "url": "http://example.com/mcp",
  "description": "Server description",
  "tags": ["tag1", "tag2"],
  "transport": "http",
  "status": "unknown",
  "metadata": {},
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

#### GET /servers/{server_id}
Get a specific server by ID.

**Response:**
```json
{
  "id": "uuid",
  "name": "Server Name",
  "url": "http://example.com/mcp",
  "description": "Server description",
  "tags": ["tag1", "tag2"],
  "transport": "http",
  "status": "unknown",
  "metadata": {},
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

#### PUT /servers/{server_id}
Update a server.

**Request Body:**
```json
{
  "name": "Updated Server Name",
  "description": "Updated description"
}
```

#### DELETE /servers/{server_id}
Delete a server.

**Response:**
```json
{
  "message": "Server deleted successfully"
}
```

### Capability Discovery

#### GET /capabilities/
List all available capabilities.

**Query Parameters:**
- `skip` (int): Number of records to skip (default: 0)
- `limit` (int): Maximum number of records to return (default: 100)

#### POST /capabilities/search
Search capabilities by criteria.

**Request Body:**
```json
{
  "capability_type": "tool",
  "name": "search_term"
}
```

#### GET /capabilities/discover/{server_id}
Discover capabilities for a specific server.

**Response:**
```json
{
  "server_id": "uuid",
  "capabilities": [...]
}
```

## Error Responses

All endpoints return standard HTTP status codes and error responses:

```json
{
  "detail": "Error message"
}
```

## OpenAPI Documentation

Interactive API documentation is available at:
- Swagger UI: `/docs`
- ReDoc: `/redoc`

These are only available in debug mode.