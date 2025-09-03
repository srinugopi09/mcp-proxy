# MCP Proxy Setup Guide

Complete setup instructions for the MCP Proxy Server with Registry using UV.

## Prerequisites

- Python ≥ 3.10
- Git

## Step 1: Install UV

UV is a fast Python package installer and resolver. Install it first:

### Linux/macOS
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Windows
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Alternative (using pip)
```bash
pip install uv
```

## Step 2: Clone the Repository

Clone the latest registry implementation:

```bash
git clone -b feature/registry-increment-1 https://github.com/srinugopi09/mcp-proxy.git
cd mcp-proxy
```

## Step 3: Setup Dependencies

UV will automatically create a virtual environment and install dependencies:

```bash
# Install all dependencies
uv sync

# Install with development dependencies (for testing/development)
uv sync --extra dev

# Install with test dependencies only
uv sync --extra test
```

## Step 4: Activate Environment

```bash
# Activate the virtual environment
source .venv/bin/activate

# On Windows
.venv\Scripts\activate
```

## Step 5: Verify Installation

Test that everything is working:

```bash
# Test the proxy server help
uv run python mcp_proxy_server.py --help

# Run the test suite
uv run python test_registry.py

# Test the installed script
uv run mcp-proxy --help
```

## Usage Examples

### Start Registry API
```bash
uv run python mcp_proxy_server.py --enable-registry --api-port 8080
```

### Register a Server (from another terminal)
```bash
curl -X POST http://localhost:8080/api/servers \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Server",
    "url": "http://localhost:8001/mcp",
    "description": "A test MCP server",
    "tags": ["test", "example"]
  }'
```

### Connect via Registry
```bash
# Get the server ID from the registration response, then:
uv run python mcp_proxy_server.py --server-id {server-id} --transport http --port 8002
```

### Direct URL Connection (still works)
```bash
uv run python mcp_proxy_server.py http://localhost:8001/mcp --transport http --port 8002
```

## Development Setup

For development work, install with dev dependencies:

```bash
# Install with development tools
uv sync --extra dev

# Run code formatting
uv run black .
uv run isort .

# Run type checking
uv run mypy .

# Run linting
uv run flake8 .
```

## API Documentation

When the registry is running, access interactive documentation:

- **Swagger UI**: http://localhost:8080/api/docs
- **ReDoc**: http://localhost:8080/api/redoc

## Troubleshooting

### UV Command Not Found
If `uv` command is not found after installation:
```bash
# Add UV to your PATH (Linux/macOS)
export PATH="$HOME/.cargo/bin:$PATH"

# Or restart your terminal
```

### Python Version Issues
Ensure you have Python 3.10 or higher:
```bash
python --version
# or
python3 --version
```

### Virtual Environment Issues
If you need to recreate the virtual environment:
```bash
# Remove existing environment
rm -rf .venv

# Recreate with UV
uv sync
```

### Import Errors
If you get import errors for registry modules:
```bash
# Make sure you're in the project directory
cd mcp-proxy

# Activate the virtual environment
source .venv/bin/activate

# Run with uv to ensure correct environment
uv run python mcp_proxy_server.py --help
```

## Alternative: Using pip

If you prefer pip over UV:

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e .

# Or install from requirements.txt
pip install -r requirements.txt

# Run the server
python mcp_proxy_server.py --help
```

## Next Steps

1. **Test the setup** by running the registry API
2. **Register your first server** using the API
3. **Connect via server ID** to test the proxy functionality
4. **Integrate with your portal** using the REST API

For complete API documentation, see [REGISTRY_API.md](REGISTRY_API.md).