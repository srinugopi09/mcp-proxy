# MCP Registry - Modular Architecture

## Overview

The MCP Registry has been completely restructured into a modular, enterprise-ready architecture with clean separation of concerns, proper dependency injection, and comprehensive CLI tooling.

## Architecture Components

### 🏗️ Core Layer (`mcp_registry/core/`)
- **`config.py`**: Centralized configuration management with Pydantic settings
- **`database.py`**: Database initialization and session management
- **`exceptions.py`**: Custom exception classes

### 🗄️ Database Layer (`mcp_registry/db/`)
- **`models.py`**: SQLAlchemy ORM models with proper relationships
- **Base**: Declarative base for all models
- **Server**: Server registration model
- **Capability**: Server capability model

### 📊 Repository Layer (`mcp_registry/repositories/`)
- **`server.py`**: Server data access operations
- **`capability.py`**: Capability data access operations
- Repository pattern for clean data access abstraction

### 🔧 Service Layer (`mcp_registry/services/`)
- **`registry.py`**: Business logic for server management
- **`discovery.py`**: Business logic for capability discovery
- Clean separation of business logic from data access

### 🌐 API Layer (`mcp_registry/api/`)
- **`app.py`**: FastAPI application factory
- **`routes/`**: RESTful API endpoints
  - `health.py`: Health check endpoints
  - `servers.py`: Server management endpoints
  - `capabilities.py`: Capability discovery endpoints

### 🖥️ CLI Layer (`mcp_registry/cli/`)
- **`main.py`**: Main CLI application with Typer
- **`commands/`**: Command modules
  - `server.py`: Server management commands
  - `discovery.py`: Capability discovery commands
  - `database.py`: Database management commands
  - `config.py`: Configuration management commands

### 📋 Models Layer (`mcp_registry/models/`)
- **Pydantic models** for request/response validation
- **`server.py`**: Server-related models
- **`capability.py`**: Capability-related models

## Key Features

### ✨ Modern Technology Stack
- **SQLAlchemy 2.0** with async support
- **Alembic** for database migrations
- **FastAPI** with dependency injection
- **Typer** with Rich formatting for CLI
- **Pydantic** for data validation

### 🔧 CLI Interface
```bash
# Database management
mcp-registry db init          # Initialize database
mcp-registry db status        # Check database status
mcp-registry db migrate       # Run migrations

# Server management
mcp-registry server register  # Register new server
mcp-registry server list      # List servers
mcp-registry server show      # Show server details

# Discovery
mcp-registry discover scan    # Scan for capabilities
mcp-registry discover search  # Search capabilities

# Configuration
mcp-registry config show      # Show configuration
mcp-registry config create    # Create config file

# API Server
mcp-registry start            # Start API server
```

### 🌐 REST API
- **Health endpoints**: `/health/`, `/health/ready`
- **Server endpoints**: `/api/v1/servers/`
- **Capability endpoints**: `/api/v1/capabilities/`
- **OpenAPI documentation**: `/docs` (in debug mode)

### 🗄️ Database Features
- **Async SQLAlchemy** with proper session management
- **Migration support** with Alembic
- **Relationship mapping** between servers and capabilities
- **JSON metadata** storage for flexible data

### ⚙️ Configuration Management
- **Environment-based** configuration
- **Pydantic Settings** with validation
- **Development/Production** profiles
- **Security validation** for production settings

## Usage Examples

### Starting the API Server
```bash
# Development mode
mcp-registry start --debug --reload

# Production mode
mcp-registry start --host 0.0.0.0 --port 8000
```

### Managing Servers
```bash
# Register a server
mcp-registry server register \
  --name "My MCP Server" \
  --endpoint "http://localhost:3000" \
  --description "A sample MCP server"

# List all servers
mcp-registry server list

# Show server details
mcp-registry server show server-id-123
```

### Database Operations
```bash
# Initialize database
mcp-registry db init

# Check status
mcp-registry db status

# Create migration
mcp-registry db migrate --message "Add new fields" --auto

# Reset database (development only)
mcp-registry db reset --force
```

## Development Setup

### 1. Install Dependencies
```bash
pip install -e .
# or
pip install pydantic-settings sqlalchemy aiosqlite alembic "typer[all]" rich
```

### 2. Initialize Database
```bash
mcp-registry db init
```

### 3. Start Development Server
```bash
mcp-registry start --debug --reload
```

### 4. Access API Documentation
Visit: `http://localhost:8000/docs`

## Configuration

### Environment Variables
```bash
# Database
DATABASE_URL=sqlite+aiosqlite:///./mcp_registry.db

# API Server
HOST=0.0.0.0
PORT=8000
DEBUG=true
RELOAD=true

# CORS
CORS_ORIGINS=["http://localhost:3000", "http://localhost:8080"]

# Security (Production)
SECRET_KEY=your-secret-key-here
```

### Configuration File
```yaml
# config.yaml
database_url: "sqlite+aiosqlite:///./mcp_registry.db"
host: "0.0.0.0"
port: 8000
debug: true
cors_origins:
  - "http://localhost:3000"
  - "http://localhost:8080"
```

## Migration from Legacy Structure

The new modular architecture provides:

1. **Better Maintainability**: Clear separation of concerns
2. **Improved Testing**: Isolated components for unit testing
3. **Enhanced CLI**: Rich, user-friendly command interface
4. **Modern ORM**: SQLAlchemy 2.0 with async support
5. **API Documentation**: Auto-generated OpenAPI specs
6. **Configuration Management**: Centralized, validated settings
7. **Database Migrations**: Proper schema versioning

## API Server Preview

The API server is now running at: **https://8000--01990fa6-a82a-7bd0-aaf6-898f8742a749.us-east-1-01.gitpod.dev**

You can access:
- **API Documentation**: `/docs`
- **Health Check**: `/health/`
- **Server Management**: `/api/v1/servers/`
- **Capability Discovery**: `/api/v1/capabilities/`

## Next Steps

1. **Add Authentication**: Implement JWT or API key authentication
2. **Add Caching**: Redis caching for frequently accessed data
3. **Add Monitoring**: Prometheus metrics and health checks
4. **Add Testing**: Comprehensive test suite with pytest
5. **Add Docker**: Containerization for easy deployment