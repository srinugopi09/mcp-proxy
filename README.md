# MCP Registry

Enterprise Model Context Protocol Server Registry with modular architecture.

## Overview

A comprehensive platform for managing, discovering, and monitoring MCP servers with advanced features like capability discovery, performance monitoring, and a rich CLI interface.

## Features

- **🏗️ Modular Architecture**: Clean layered design with separation of concerns
- **🗄️ Modern Database**: SQLAlchemy 2.0 with async support and migrations
- **🖥️ Rich CLI**: Beautiful Typer-based CLI with Rich formatting
- **🌐 REST API**: FastAPI with automatic OpenAPI documentation
- **🔍 Discovery**: Automatic capability discovery and introspection
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

# Discover capabilities
mcp-registry discover scan
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