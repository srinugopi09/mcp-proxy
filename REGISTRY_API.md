# MCP Registry API Documentation

Complete API reference for the MCP Server Registry.

## Overview

The MCP Registry provides a REST API for managing and discovering MCP servers. It supports server registration, health monitoring, and capability discovery.

## Base URL

When running the registry API:
```
http://localhost:8080/api
```

## Authentication

Currently, the API does not require authentication. This may be added in future versions.

## API Endpoints

### Health Check

#### GET /api/health
Check if the registry service is running.

**Response:**
```json
{
  "status": "healthy",
  "service": "mcp-registry"
}
```

### Statistics

#### GET /api/stats
Get registry statistics and server counts.

**Response:**
```json
{
  "total_servers": 5,
  "status_breakdown": {
    "healthy": 3,
    "unhealthy": 1,
    "unknown": 1
  },
  "transport_breakdown": {
    "http": 3,
    "sse": 1,
    "auto": 1
  }
}
```

### Server Management

#### POST /api/servers
Register a new MCP server.

**Request Body:**
```json
{
  "name": "Weather Service",
  "url": "http://localhost:8001/mcp",
  "description": "Provides weather information and forecasts",
  "tags": ["weather", "external-api", "production"],
  "transport": "http",
  "metadata": {
    "version": "1.0.0",
    "maintainer": "weather-team@company.com",
    "documentation": "https://docs.weather-service.com"
  }
}
```

**Required Fields:**
- `name` (string): Human-readable server name
- `url` (string): Valid HTTP/HTTPS URL to the MCP server

**Optional Fields:**
- `description` (string): Server description
- `tags` (array): Categorization tags
- `transport` (string): Transport type (`http`, `sse`, `auto`)
- `metadata` (object): Additional metadata

**Response (201 Created):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Weather Service",
  "url": "http://localhost:8001/mcp",
  "description": "Provides weather information and forecasts",
  "tags": ["weather", "external-api", "production"],
  "transport": "http",
  "status": "unknown",
  "metadata": {
    "version": "1.0.0",
    "maintainer": "weather-team@company.com",
    "documentation": "https://docs.weather-service.com"
  },
  "created_at": "2025-01-01T12:00:00Z",
  "updated_at": "2025-01-01T12:00:00Z",
  "last_checked": null
}
```

**Error Responses:**
- `409 Conflict`: URL already registered
- `422 Unprocessable Entity`: Validation error

#### GET /api/servers
List registered MCP servers with optional filtering.

**Query Parameters:**
- `status` (string): Filter by server status (`healthy`, `unhealthy`, `unknown`)
- `tags` (string): Filter by tags (comma-separated)
- `limit` (integer): Maximum number of servers to return (1-1000)
- `offset` (integer): Number of servers to skip

**Examples:**
```bash
# Get all servers
GET /api/servers

# Get healthy servers only
GET /api/servers?status=healthy

# Get servers with specific tags
GET /api/servers?tags=weather,production

# Paginated results
GET /api/servers?limit=10&offset=20
```

**Response (200 OK):**
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Weather Service",
    "url": "http://localhost:8001/mcp",
    "description": "Provides weather information",
    "tags": ["weather", "external-api"],
    "transport": "http",
    "status": "healthy",
    "metadata": {},
    "created_at": "2025-01-01T12:00:00Z",
    "updated_at": "2025-01-01T12:00:00Z",
    "last_checked": "2025-01-01T12:30:00Z"
  }
]
```

#### GET /api/servers/{server_id}
Get details of a specific MCP server.

**Path Parameters:**
- `server_id` (string): Server ID

**Response (200 OK):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Weather Service",
  "url": "http://localhost:8001/mcp",
  "description": "Provides weather information",
  "tags": ["weather", "external-api"],
  "transport": "http",
  "status": "healthy",
  "metadata": {},
  "created_at": "2025-01-01T12:00:00Z",
  "updated_at": "2025-01-01T12:00:00Z",
  "last_checked": "2025-01-01T12:30:00Z"
}
```

**Error Responses:**
- `404 Not Found`: Server not found

#### PUT /api/servers/{server_id}
Update an existing MCP server registration.

**Path Parameters:**
- `server_id` (string): Server ID

**Request Body:**
```json
{
  "name": "Updated Weather Service",
  "description": "Updated description",
  "tags": ["weather", "updated"],
  "metadata": {
    "version": "1.1.0"
  }
}
```

**Note:** All fields are optional. Only provided fields will be updated.

**Response (200 OK):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Updated Weather Service",
  "url": "http://localhost:8001/mcp",
  "description": "Updated description",
  "tags": ["weather", "updated"],
  "transport": "http",
  "status": "healthy",
  "metadata": {
    "version": "1.1.0"
  },
  "created_at": "2025-01-01T12:00:00Z",
  "updated_at": "2025-01-01T12:15:00Z",
  "last_checked": "2025-01-01T12:30:00Z"
}
```

**Error Responses:**
- `404 Not Found`: Server not found
- `409 Conflict`: URL conflicts with another server
- `422 Unprocessable Entity`: Validation error

#### DELETE /api/servers/{server_id}
Delete an MCP server registration.

**Path Parameters:**
- `server_id` (string): Server ID

**Response (200 OK):**
```json
{
  "message": "Server 550e8400-e29b-41d4-a716-446655440000 deleted successfully"
}
```

**Error Responses:**
- `404 Not Found`: Server not found

#### PATCH /api/servers/{server_id}/status
Update server health status.

**Path Parameters:**
- `server_id` (string): Server ID

**Request Body:**
```json
{
  "status": "healthy"
}
```

**Valid Status Values:**
- `healthy`: Server is responding and functional
- `unhealthy`: Server is not responding or has errors
- `unknown`: Status has not been checked

**Response (200 OK):**
```json
{
  "message": "Server 550e8400-e29b-41d4-a716-446655440000 status updated to healthy"
}
```

**Error Responses:**
- `404 Not Found`: Server not found
- `422 Unprocessable Entity`: Invalid status value

## Data Models

### Server Registration Model
```json
{
  "name": "string (required, 1-255 chars)",
  "url": "string (required, valid HTTP/HTTPS URL)",
  "description": "string (optional, max 1000 chars)",
  "tags": ["string"] (optional, array of strings),
  "transport": "string (optional, 'http'|'sse'|'auto', default: 'auto')",
  "metadata": {} (optional, object with additional data)
}
```

### Server Response Model
```json
{
  "id": "string (UUID)",
  "name": "string",
  "url": "string",
  "description": "string|null",
  "tags": ["string"],
  "transport": "string",
  "status": "string ('healthy'|'unhealthy'|'unknown')",
  "metadata": {},
  "created_at": "string (ISO 8601 datetime)",
  "updated_at": "string (ISO 8601 datetime)",
  "last_checked": "string|null (ISO 8601 datetime)"
}
```

## Error Handling

All error responses follow this format:
```json
{
  "detail": "Error description"
}
```

### HTTP Status Codes
- `200 OK`: Request successful
- `201 Created`: Resource created successfully
- `400 Bad Request`: Invalid request format
- `404 Not Found`: Resource not found
- `409 Conflict`: Resource conflict (e.g., duplicate URL)
- `422 Unprocessable Entity`: Validation error
- `500 Internal Server Error`: Server error

## Usage Examples

### Python Client Example
```python
import requests

# Register a server
server_data = {
    "name": "My MCP Server",
    "url": "http://localhost:8001/mcp",
    "description": "My custom MCP server",
    "tags": ["custom", "test"]
}

response = requests.post("http://localhost:8080/api/servers", json=server_data)
server = response.json()
server_id = server["id"]

# List servers
response = requests.get("http://localhost:8080/api/servers")
servers = response.json()

# Update server status
requests.patch(
    f"http://localhost:8080/api/servers/{server_id}/status",
    json={"status": "healthy"}
)

# Delete server
requests.delete(f"http://localhost:8080/api/servers/{server_id}")
```

### JavaScript Client Example
```javascript
// Register a server
const serverData = {
  name: "My MCP Server",
  url: "http://localhost:8001/mcp",
  description: "My custom MCP server",
  tags: ["custom", "test"]
};

const response = await fetch("http://localhost:8080/api/servers", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(serverData)
});

const server = await response.json();
const serverId = server.id;

// List servers
const serversResponse = await fetch("http://localhost:8080/api/servers");
const servers = await serversResponse.json();

// Update server status
await fetch(`http://localhost:8080/api/servers/${serverId}/status`, {
  method: "PATCH",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ status: "healthy" })
});
```

## Interactive Documentation

When the registry API is running, you can access interactive documentation:

- **Swagger UI**: `http://localhost:8080/api/docs`
- **ReDoc**: `http://localhost:8080/api/redoc`

These interfaces allow you to test API endpoints directly from your browser.