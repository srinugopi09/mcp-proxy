# MCP Proxy Hub

A dynamic proxy hub for testing and integrating with remote Model Context Protocol (MCP) servers. The hub provides both REST API and native MCP protocol access to remote servers through isolated, session-based proxies.

## Features

- **Dynamic Proxy Mounting**: Connect to any remote MCP server without configuration
- **Session Management**: Isolated sessions with automatic TTL-based cleanup
- **Security**: Built-in SSRF protection and configurable security policies
- **Authentication**: Bearer token and custom header forwarding
- **Streaming Support**: Real-time tool execution with NDJSON streaming
- **Dual Protocol**: Both REST API and native MCP protocol access

## Quick Start

### Prerequisites

- Python 3.8+
- [UV](https://docs.astral.sh/uv/) package manager

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd mcp-proxy-hub

# Install dependencies
uv sync
```

### Running the Server

```bash
# Start the server
uv run mcp-hub

# Or with custom host/port
HOST=127.0.0.1 PORT=8080 uv run mcp-hub
```

The server will start on `http://0.0.0.0:8000` by default and provide:
- REST API at the root (`/`)
- Native MCP protocol at `/mcp/`
- Interactive API docs at `/docs`

## Basic Usage

### 1. Create a Server Connection

```bash
curl -X POST "http://localhost:8000/api/v1/server" \
  -H "Content-Type: application/json" \
  -d '{
    "remote_url": "https://example.com/mcp",
    "token": "your-bearer-token"
  }'
```

Response:
```json
{
  "session_id": "a1b2c3d4",
  "prefix": "a1b2c3d4",
  "remote_url": "https://example.com/mcp",
  "expires_at": "2024-01-01T12:30:00Z"
}
```

### 2. List Available Tools

```bash
curl "http://localhost:8000/api/v1/server/a1b2c3d4/tools"
```

### 3. Execute a Tool

```bash
curl -X POST "http://localhost:8000/api/v1/server/a1b2c3d4/tools/example-tool" \
  -H "Content-Type: application/json" \
  -d '{
    "arguments": {"param1": "value1"},
    "stream": false
  }'
```

### 4. Close Server Connection

```bash
curl -X DELETE "http://localhost:8000/api/v1/server/a1b2c3d4"
```

## Configuration

Configure the application using environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | `0.0.0.0` | Server host |
| `PORT` | `8000` | Server port |
| `MCP_HUB_SESSION_TTL` | `1800` | Session TTL in seconds |

### Example Configuration

Create a `.env` file:
```env
HOST=127.0.0.1
PORT=8080
MCP_HUB_SESSION_TTL=3600
```

## Development

### Setup Development Environment

```bash
# Install with development dependencies
uv sync --group dev

# Run tests
uv run pytest

# Format code
uv run black src tests

# Type checking
uv run mypy src
```

### Running with Auto-reload

```bash
uv run uvicorn mcp_proxy_hub.main:create_app --factory --reload
```

## API Documentation

Once the server is running, visit:
- **Interactive docs**: http://localhost:8000/docs
- **OpenAPI spec**: http://localhost:8000/openapi.json

## Security

The hub includes built-in security features:

- **SSRF Protection**: Blocks access to private networks and localhost
- **URL Validation**: Only allows HTTP/HTTPS schemes
- **Configurable Policies**: Customize allowed/denied hosts
- **No Credential Storage**: Tokens are forwarded, not stored

## Architecture

For detailed architecture information, see [docs/knowledge_base/architecture.md](docs/knowledge_base/architecture.md).

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Run code quality checks: `uv run black src tests && uv run pytest`
5. Submit a pull request

For detailed development guidelines, see [docs/knowledge_base/development.md](docs/knowledge_base/development.md).

## License

MIT License - see LICENSE file for details.