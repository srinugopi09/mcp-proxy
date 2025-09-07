# MCP Registry

Enterprise Model Context Protocol Server Registry with modular architecture.

## Overview

A comprehensive platform for managing, discovering, and monitoring MCP servers with advanced features like capability discovery, performance monitoring, and a rich CLI interface.

## Features

- **🏗️ Modular Architecture**: Clean layered design with separation of concerns
- **🗄️ Modern Database**: SQLAlchemy 2.0 with async support and migrations
- **🖥️ Rich CLI**: Beautiful Typer-based CLI with Rich formatting
- **🌐 REST API**: FastAPI with automatic OpenAPI documentation
- **🔍 MCP Discovery**: Automatic capability discovery from MCP servers
- **🔄 MCP Proxy**: Proxy requests to registered MCP servers
- **🛠️ Full MCP Support**: Tools, resources, prompts, and resource templates
- **⚙️ Configuration**: Centralized settings with environment support

## Quick Start

### Installation

```bash
# Clone repository
git clone <repository-url>
cd mcp-registry

# Install with UV (recommended)
uv sync

# Initialize database
uv run init-db
# OR: uv run python -m mcp_registry.cli.main db init

# Start API server (uses Uvicorn)
uv run dev-server
# OR: uv run python -m mcp_registry.cli.main start --debug
```

### After Installation (Package Mode)

```bash
# Install the package to make mcp-registry command available
uv pip install -e .

# Now you can use the command directly
mcp-registry db init
mcp-registry start --debug
```

### Basic Usage

**Development Mode (UV scripts):**
```bash
# Register a server
uv run registry server register \
  --name "Weather API" \
  --url "http://weather.example.com/mcp" \
  --description "Weather forecasting service"

# List servers  
uv run registry server list

# Discover capabilities from all servers
uv run registry discover scan --all

# Check database status
uv run db-status
```

**Package Mode (after installation):**
```bash
# Register a server
mcp-registry server register \
  --name "Weather API" \
  --url "http://weather.example.com/mcp"

# List servers
mcp-registry server list

# Discover capabilities from all servers
mcp-registry discover scan --all

# List discovered capabilities
mcp-registry discover list
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `mcp-registry db init` | Initialize database |
| `mcp-registry db status` | Check database status |
| `mcp-registry server register` | Register new server |
| `mcp-registry server list` | List all servers |
| `mcp-registry discover scan` | Discover capabilities |
| `mcp-registry start` | Start API server |
| `mcp-registry config show` | Show configuration |

## API Endpoints

- **Health**: `GET /health/` - Health check
- **Servers**: `GET /servers/` - List servers
- **Servers**: `POST /servers/` - Register server
- **Capabilities**: `GET /capabilities/` - List capabilities
- **Discovery**: `GET /capabilities/discover/{server_id}` - Discover server capabilities
- **Proxy**: `POST /proxy/{server_id}/tools/call` - Call MCP server tools
- **Proxy**: `POST /proxy/{server_id}/resources/read` - Get MCP server resources
- **Proxy**: `POST /proxy/{server_id}/prompts/get` - Get MCP server prompts

## Configuration

### Environment Variables

```bash
export DATABASE_URL="sqlite+aiosqlite:///./mcp_registry.db"
export HOST="127.0.0.1"
export PORT="8000"
export DEBUG="true"
```

### Configuration File

Create `config.yaml`:

```yaml
database_url: "sqlite+aiosqlite:///./mcp_registry.db"
host: "127.0.0.1"
port: 8000
debug: true
cors_origins:
  - "http://localhost:3000"
```

## Development

```bash
# Install development dependencies
uv sync --dev

# Run tests
uv run pytest

# Format code
uv run black mcp_registry/
uv run isort mcp_registry/

# Type checking
uv run mypy mcp_registry/
```

## Documentation

- **[Architecture](docs/architecture.md)** - Detailed architecture overview
- **[API Documentation](docs/api.md)** - REST API reference
- **[CLI Guide](docs/cli.md)** - Command-line interface usage
- **[Development](docs/development.md)** - Development setup and guidelines
- **[Deployment](docs/deployment.md)** - Production deployment guide

## Examples

See the `examples/` directory for usage examples:

- `modular_api_example.py` - Demonstrates the modular API usage

## Requirements

- Python 3.10+
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

See [Development Guide](docs/development.md) for detailed contribution guidelines.