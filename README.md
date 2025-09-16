# MCP Registry API

Enterprise Model Context Protocol Server Registry with clean API-first architecture.

## Overview

A streamlined platform for managing, discovering, and monitoring MCP servers through a modern REST API. Features automatic capability discovery, performance monitoring, and comprehensive server management.

## Features

- **🏗️ Clean Architecture**: API-first design with separation of concerns
- **🗄️ Modern Database**: SQLAlchemy 2.0 with async support and JSON types
- **🌐 REST API**: FastAPI with automatic OpenAPI documentation and exception handling
- **🔍 MCP Discovery**: Automatic capability discovery from MCP servers
- **🔄 FastMCP Proxy**: Built-in FastMCP proxy server for registered MCP servers
- **🛠️ Full MCP Support**: Tools, resources, prompts, and resource templates
- **📡 Multiple Transports**: stdio, HTTP, and SSE transport support
- **⚙️ Configuration**: Environment-based configuration with Pydantic settings
- **🔧 Developer Friendly**: UV scripts for streamlined development workflow

## Quick Start

### Using UV (Recommended)

```bash
# Clone repository
git clone <repository-url>
cd mcp-registry

# Install dependencies
uv sync

# Initialize database
uv run init-db

# Start development server with auto-reload
uvicorn mcp_registry.api.app:app --host 0.0.0.0 --port 8000 --reload

# API will be available at http://localhost:8000
# Documentation at http://localhost:8000/docs
```

### Using Python directly

```bash
# Install dependencies
pip install -e .

# Initialize database
python -m mcp_registry.scripts.init_db

# Start server
uvicorn mcp_registry.api.app:app --host 0.0.0.0 --port 8000 --reload
```

## Development Commands

```bash
# Development Server
uvicorn mcp_registry.api.app:app --host 0.0.0.0 --port 8000 --reload

# Production Server
uvicorn mcp_registry.api.app:app --host 0.0.0.0 --port 8000

# Database Management  
python -m mcp_registry.scripts.init_db    # Initialize database
alembic upgrade head                       # Run pending migrations
alembic revision --autogenerate           # Generate new migration

# Testing
pytest                                     # Run tests
pytest --cov=mcp_registry --cov-report=html  # Run tests with coverage

# Code Quality
flake8 mcp_registry                       # Run linting
black mcp_registry                        # Format code
mypy mcp_registry                         # Type checking
```

## API Usage Examples

### Register a Server
```bash
curl -X POST "http://localhost:8000/api/v1/servers" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Weather API",
    "url": "https://weather.example.com/mcp",
    "description": "Weather forecasting service",
    "tags": ["weather", "forecast"],
    "metadata": {"version": "1.0.0", "region": "us-east-1"}
  }'
```

### List Servers
```bash
curl "http://localhost:8000/api/v1/servers"
```

### Discover Server Capabilities
```bash
curl -X POST "http://localhost:8000/api/v1/servers/{server_id}/discover"
```

### Proxy MCP Requests
```bash
# Call a tool through the proxy
curl -X POST "http://localhost:8000/api/v1/proxy/{server_id}/tools/call" \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "get_weather",
    "arguments": {"location": "San Francisco"}
  }'
```

## API Documentation

Once the server is running, visit:
- **Interactive API Docs**: http://localhost:8000/docs
- **ReDoc Documentation**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/openapi.json

## API Endpoints

### Server Management
- `GET /api/v1/servers/` - List all registered servers
- `POST /api/v1/servers/` - Register a new server
- `GET /api/v1/servers/{server_id}` - Get server details
- `PUT /api/v1/servers/{server_id}` - Update server information
- `DELETE /api/v1/servers/{server_id}` - Delete a server

### Capability Discovery
- `GET /api/v1/capabilities/` - List all discovered capabilities
- `POST /api/v1/servers/{server_id}/discover` - Discover server capabilities
- `GET /api/v1/servers/{server_id}/capabilities` - Get server capabilities

### MCP Proxy
- `POST /api/v1/proxy/{server_id}/rpc` - Proxy JSON-RPC requests
- `POST /api/v1/proxy/{server_id}/tools/call` - Call MCP server tools
- `GET /api/v1/proxy/{server_id}/resources/{resource_uri}` - Get resources
- `GET /api/v1/proxy/{server_id}/prompts/{prompt_name}` - Get prompts
- `POST /api/v1/proxy/{server_id}/initialize` - Initialize server connection

### Health & Monitoring
- `GET /api/v1/health/` - Health check endpoint

## Configuration

The application uses environment variables for configuration:

```bash
# Database
export DATABASE_URL="sqlite+aiosqlite:///./mcp_registry.db"

# Server
export HOST="0.0.0.0"
export PORT="8000"
export DEBUG="true"

# CORS (comma-separated)
export CORS_ORIGINS="http://localhost:3000,http://localhost:8080"

# Logging
export LOG_LEVEL="INFO"
```

You can also create a `.env` file in the project root:

```env
DATABASE_URL=sqlite+aiosqlite:///./mcp_registry.db
HOST=0.0.0.0
PORT=8000
DEBUG=true
CORS_ORIGINS=http://localhost:3000,http://localhost:8080
LOG_LEVEL=INFO
```

## Development

```bash
# Install development dependencies
uv sync --dev

# Development workflow
uvicorn mcp_registry.api.app:app --reload  # Start dev server
pytest                                      # Run tests
pytest --cov=mcp_registry                  # Run tests with coverage
black mcp_registry                          # Format code
flake8 mcp_registry                         # Run linting
mypy mcp_registry                           # Type checking
```

## Project Structure

```
mcp_registry/
├── api/                    # FastAPI application
│   ├── routes/            # API route handlers
│   ├── exception_handlers.py  # Centralized exception handling
│   └── app.py             # FastAPI app factory
├── core/                  # Core functionality
│   ├── config.py          # Configuration management
│   ├── database.py        # Database setup
│   └── exceptions.py      # Custom exceptions
├── models/                # Pydantic models
├── repositories/          # Data access layer
├── services/              # Business logic
├── db/                    # SQLAlchemy models
└── scripts/               # Utility scripts
```

## Examples

See the `examples/` directory for usage examples:

- `modular_api_example.py` - Demonstrates the modular API usage

## Requirements

- Python 3.11+
- UV package manager (recommended)
- FastMCP 2.0+ for MCP protocol support
- SQLite (default) or PostgreSQL (production)

## License

MIT License - see LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

For detailed development setup and guidelines, see the project structure above and use the provided UV scripts for development workflow.