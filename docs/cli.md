# CLI Usage Guide

## Overview

The MCP Registry provides a comprehensive command-line interface built with Typer and Rich for beautiful, user-friendly interactions.

## Installation

```bash
# Install with UV (recommended)
uv sync

# Install in development mode
uv pip install -e .
```

## Basic Usage

```bash
mcp-registry --help
```

## Commands

### Database Management

#### Initialize Database
```bash
mcp-registry db init
```
Creates the database and all required tables.

#### Check Database Status
```bash
mcp-registry db status
```
Shows database connection status, version, and table information.

#### Database Migrations
```bash
# Create a new migration
mcp-registry db migrate --message "Add new field" --auto

# Run migrations
mcp-registry db migrate
```

#### Reset Database (Development Only)
```bash
mcp-registry db reset --force
```
⚠️ **Warning:** This will delete all data!

### Server Management

#### Register a Server
```bash
mcp-registry server register \
  --name "My MCP Server" \
  --url "http://localhost:3000/mcp" \
  --description "A sample MCP server" \
  --tags "development,testing"
```

#### List Servers
```bash
# List all servers
mcp-registry server list

# List with pagination
mcp-registry server list --skip 10 --limit 5
```

#### Show Server Details
```bash
mcp-registry server show <server-id>
```

#### Update Server
```bash
mcp-registry server update <server-id> \
  --name "Updated Name" \
  --description "Updated description"
```

#### Delete Server
```bash
mcp-registry server delete <server-id>
```

### Capability Discovery

#### Scan for Capabilities
```bash
# Scan all servers
mcp-registry discover scan

# Scan specific server
mcp-registry discover scan --server-id <server-id>
```

#### Search Capabilities
```bash
# Search by name
mcp-registry discover search --name "weather"

# Search by type
mcp-registry discover search --type "tool"

# Combined search
mcp-registry discover search --name "weather" --type "tool"
```

#### List Capabilities
```bash
mcp-registry discover list
```

### Configuration Management

#### Show Configuration
```bash
# Show as table
mcp-registry config show

# Show as environment variables
mcp-registry config show --format env
```

#### Create Configuration File
```bash
# Create YAML config
mcp-registry config create --format yaml

# Create TOML config
mcp-registry config create --format toml
```

#### Validate Configuration
```bash
mcp-registry config validate
```

### API Server

#### Start the API Server
```bash
# Development mode (with auto-reload)
mcp-registry start --debug --reload

# Production mode
mcp-registry start --host 0.0.0.0 --port 8000 --workers 4

# Custom configuration
mcp-registry start \
  --host 127.0.0.1 \
  --port 8080 \
  --log-level info

# Quick debug start
mcp-registry start --debug  # Uses settings defaults with debug mode
```

**Server Options:**
- `--host`: Host to bind to (default: from settings or 127.0.0.1)
- `--port`: Port to bind to (default: from settings or 8000)  
- `--workers`: Number of worker processes (production only)
- `--reload`: Enable auto-reload (development only)
- `--debug`: Enable debug mode (shows docs, verbose logging)
- `--log-level`: Set logging level (debug, info, warning, error)

**Note:** The server uses Uvicorn as the ASGI server. Workers and reload are mutually exclusive - reload automatically disables multiple workers.

### System Information

#### Show Version
```bash
mcp-registry version
```

#### Show System Status
```bash
mcp-registry status
```

#### Initialize Everything
```bash
mcp-registry init
```
Initializes database, creates default configuration, and sets up the system.

## Configuration

### Environment Variables

```bash
# Database
export DATABASE_URL="sqlite+aiosqlite:///./mcp_registry.db"

# API Server
export HOST="0.0.0.0"
export PORT="8000"
export DEBUG="true"
export RELOAD="true"

# CORS
export CORS_ORIGINS='["http://localhost:3000"]'

# Security (Production)
export SECRET_KEY="your-secret-key-here"
```

### Configuration File

Create a `config.yaml` file:

```yaml
database_url: "sqlite+aiosqlite:///./mcp_registry.db"
host: "0.0.0.0"
port: 8000
debug: true
cors_origins:
  - "http://localhost:3000"
  - "http://localhost:8080"
```

## Examples

### Quick Start
```bash
# Initialize the system
mcp-registry init

# Register a server
mcp-registry server register \
  --name "Weather API" \
  --url "http://weather.example.com/mcp" \
  --description "Weather forecasting service"

# Start the API server
mcp-registry start --debug

# In another terminal, scan for capabilities
mcp-registry discover scan
```

### Batch Operations
```bash
# Register multiple servers from a script
for server in server1 server2 server3; do
  mcp-registry server register \
    --name "$server" \
    --url "http://$server.example.com/mcp"
done

# List all and export to JSON
mcp-registry server list --format json > servers.json
```

## Tips and Tricks

### Rich Output
The CLI uses Rich for beautiful output with colors, tables, and progress bars. All commands support:
- Colored output
- Progress indicators
- Formatted tables
- Error highlighting

### Debugging
```bash
# Enable verbose output
mcp-registry --verbose server list

# Show SQL queries
export DEBUG=true
mcp-registry db status
```

### Scripting
All commands return appropriate exit codes for scripting:
- `0`: Success
- `1`: General error
- `2`: Invalid usage

```bash
#!/bin/bash
if mcp-registry db status; then
  echo "Database is healthy"
else
  echo "Database needs attention"
  exit 1
fi
```