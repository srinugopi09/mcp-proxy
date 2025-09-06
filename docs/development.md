# Development Guide

## Prerequisites

- Python 3.10+
- UV (recommended package manager)
- Git

## Setup

### 1. Clone the Repository
```bash
git clone <repository-url>
cd mcp-registry
```

### 2. Install Dependencies
```bash
# Install with UV (recommended)
uv sync

# Install development dependencies
uv sync --dev
```

### 3. Initialize Database
```bash
# Using UV script
uv run init-db

# Or module mode
uv run python -m mcp_registry.cli.main db init
```

### 4. Run Tests
```bash
uv run pytest
```

### 5. Start Development Server
```bash
# Using UV script (recommended for development)
uv run dev-server

# Or module mode
uv run python -m mcp_registry.cli.main start --debug --reload

# Or install package first, then use command
uv pip install -e .
mcp-registry start --debug --reload
```

## Project Structure

```
mcp-registry/
├── docs/                    # Documentation
├── examples/               # Usage examples
├── mcp_registry/          # Main package
│   ├── api/               # FastAPI routes and app
│   ├── cli/               # Typer CLI commands
│   ├── core/              # Core functionality (config, database)
│   ├── db/                # Database models
│   ├── models/            # Pydantic models
│   ├── repositories/      # Data access layer
│   └── services/          # Business logic layer
├── tests/                 # Test suite
├── pyproject.toml         # Project configuration
└── README.md              # Project overview
```

## Development Workflow

### 1. Create Feature Branch
```bash
git checkout -b feature/your-feature-name
```

### 2. Make Changes
Follow the existing code patterns and architecture.

### 3. Run Tests
```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_api/test_servers.py

# Run with coverage
uv run pytest --cov=mcp_registry
```

### 4. Format Code
```bash
# Format with black
uv run black mcp_registry/ tests/

# Sort imports with isort
uv run isort mcp_registry/ tests/

# Lint with flake8
uv run flake8 mcp_registry/ tests/
```

### 5. Type Check
```bash
uv run mypy mcp_registry/
```

### 6. Commit Changes
```bash
git add .
git commit -m "feat: add new feature"
```

## Architecture Guidelines

### Layered Architecture
The project follows a clean layered architecture:

1. **API Layer** (`api/`): FastAPI routes and HTTP handling
2. **Service Layer** (`services/`): Business logic and orchestration
3. **Repository Layer** (`repositories/`): Data access abstraction
4. **Database Layer** (`db/`): SQLAlchemy models and database operations
5. **Core Layer** (`core/`): Configuration, exceptions, utilities

### Dependency Flow
```
API → Services → Repositories → Database
```

### Key Principles
- **Separation of Concerns**: Each layer has a specific responsibility
- **Dependency Injection**: Use FastAPI's dependency system
- **Type Safety**: Use Pydantic models and type hints throughout
- **Async/Await**: Use async patterns for I/O operations
- **Error Handling**: Proper exception handling at each layer

## Code Style

### Python Style
- Follow PEP 8
- Use Black for formatting (line length: 88)
- Use isort for import sorting
- Use type hints throughout

### Naming Conventions
- Classes: `PascalCase`
- Functions/Variables: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Private members: `_leading_underscore`

### Documentation
- Use docstrings for all public functions and classes
- Follow Google docstring format
- Include type information in docstrings
- Document complex business logic

## Database Development

### Migrations
```bash
# Create new migration
uv run alembic revision --autogenerate -m "Add new table"

# Run migrations
uv run alembic upgrade head

# Downgrade migration
uv run alembic downgrade -1
```

### Model Changes
1. Update SQLAlchemy models in `db/models.py`
2. Update Pydantic models in `models/`
3. Create migration with Alembic
4. Update repositories if needed
5. Update tests

## Testing

### Test Structure
```
tests/
├── conftest.py              # Pytest fixtures
├── test_api/               # API endpoint tests
├── test_cli/               # CLI command tests
├── test_services/          # Service layer tests
├── test_repositories/      # Repository tests
└── test_models/            # Model validation tests
```

### Writing Tests
```python
import pytest
from fastapi.testclient import TestClient

def test_create_server(test_client: TestClient):
    response = test_client.post("/servers/", json={
        "name": "Test Server",
        "url": "http://test.com/mcp"
    })
    assert response.status_code == 201
    assert response.json()["name"] == "Test Server"
```

### Test Database
Tests use an in-memory SQLite database that's created and destroyed for each test session.

## CLI Development

### Adding New Commands
1. Create command file in `cli/commands/`
2. Define Typer app and commands
3. Add rich formatting for output
4. Include in main CLI app
5. Add tests

### CLI Best Practices
- Use Rich for beautiful output
- Provide helpful error messages
- Include progress indicators for long operations
- Support both interactive and scripting use cases

## API Development

### Adding New Endpoints
1. Create route file in `api/routes/`
2. Define FastAPI router and endpoints
3. Use dependency injection for database sessions
4. Add proper request/response models
5. Include error handling
6. Add tests

### API Best Practices
- Use proper HTTP status codes
- Include comprehensive error responses
- Add request validation with Pydantic
- Use dependency injection
- Document with OpenAPI

## Contributing

### Pull Request Process
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Update documentation
7. Submit pull request

### Code Review Checklist
- [ ] Code follows style guidelines
- [ ] Tests are included and passing
- [ ] Documentation is updated
- [ ] No breaking changes (or properly documented)
- [ ] Performance impact considered
- [ ] Security implications reviewed

## Debugging

### Common Issues
1. **Import Errors**: Check PYTHONPATH and package structure
2. **Database Errors**: Ensure database is initialized
3. **CLI Not Working**: Check if package is installed in development mode
4. **API Errors**: Check FastAPI logs and database connection

### Debug Tools
```bash
# Enable SQL logging
export DEBUG=true

# Verbose CLI output
mcp-registry --verbose command

# Python debugger
import pdb; pdb.set_trace()
```

## Performance

### Database Optimization
- Use async SQLAlchemy for I/O operations
- Implement proper indexing
- Use connection pooling
- Consider query optimization

### API Optimization
- Use async endpoints
- Implement caching where appropriate
- Use pagination for large datasets
- Monitor response times

## Security

### Development Security
- Never commit secrets or API keys
- Use environment variables for configuration
- Validate all input data
- Implement proper error handling

### Production Considerations
- Use HTTPS in production
- Implement authentication/authorization
- Add rate limiting
- Monitor for security vulnerabilities