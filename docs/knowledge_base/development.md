# Development Guide

## Development Setup

### Prerequisites
- Python 3.8+
- UV package manager
- Git

### Initial Setup
```bash
# Clone the repository
git clone <repository-url>
cd mcp-proxy-hub

# Install dependencies with UV
uv sync

# Install development dependencies
uv sync --group dev
```

### Running the Application
```bash
# Using UV
uv run mcp-hub

# Or directly with Python
uv run python -m mcp_proxy_hub.main

# Development mode with auto-reload
uv run uvicorn mcp_proxy_hub.main:create_app --factory --reload
```

## Code Organization

### Module Structure
```
src/mcp_proxy_hub/
├── __init__.py          # Package exports
├── app.py              # FastAPI app factory
├── config.py           # Settings and configuration
├── main.py             # CLI entry point
├── models.py           # Pydantic models
├── routes.py           # API endpoints
├── security.py         # Security utilities
└── session.py          # Session management
```

### Testing Structure
```
tests/
├── __init__.py
├── conftest.py         # Pytest fixtures
├── unit/               # Unit tests
│   ├── test_config.py
│   ├── test_models.py
│   ├── test_security.py
│   └── test_session.py
├── integration/        # Integration tests
│   ├── test_api.py
│   └── test_mcp.py
└── fixtures/           # Test data and fixtures
```

## Development Workflow

### Code Quality
```bash
# Format code
uv run black src tests

# Sort imports
uv run isort src tests

# Lint code
uv run flake8 src tests

# Type checking
uv run mypy src
```

### Testing
```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov

# Run specific test types
uv run pytest -m unit
uv run pytest -m integration
uv run pytest -m "not slow"
```

### Pre-commit Hooks
```bash
# Install pre-commit hooks
uv run pre-commit install

# Run hooks manually
uv run pre-commit run --all-files
```

## Configuration Management

### Environment Variables
- `MCP_HUB_SESSION_TTL`: Session TTL in seconds (default: 1800)
- `HOST`: Server host (default: 0.0.0.0)
- `PORT`: Server port (default: 8000)

### Development Configuration
Create a `.env` file in the project root:
```env
MCP_HUB_SESSION_TTL=3600
HOST=127.0.0.1
PORT=8000
```

## API Development

### Adding New Endpoints
1. Define Pydantic models in `models.py`
2. Add route handler in `routes.py`
3. Update `__init__.py` exports if needed
4. Add tests in `tests/integration/test_api.py`

### Example New Endpoint
```python
# In models.py
class NewFeatureRequest(BaseModel):
    name: str
    description: Optional[str] = None

class NewFeatureResponse(BaseModel):
    id: str
    name: str
    created_at: datetime

# In routes.py
@router.post("/feature", response_model=NewFeatureResponse)
async def create_feature(req: NewFeatureRequest) -> NewFeatureResponse:
    # Implementation here
    pass
```

## Session Management

### Session Lifecycle
1. **Creation**: `POST /session` creates new proxy session
2. **Usage**: Tools accessed via session ID
3. **Refresh**: `POST /session/{id}/refresh` extends TTL
4. **Cleanup**: Automatic cleanup via background task
5. **Termination**: `DELETE /session/{id}` or TTL expiry

### Adding Session Features
- Extend `SessionData` class for new session properties
- Update `HubState` for new session operations
- Add corresponding API endpoints in `routes.py`

## Security Considerations

### URL Validation
- All remote URLs validated via `security.validate_remote_url()`
- Private networks blocked by default
- Configurable allow/deny lists

### Authentication
- Bearer tokens forwarded to remote servers
- No credential storage in hub
- Custom headers supported

### Best Practices
- Always validate external inputs
- Use type hints and Pydantic models
- Implement proper error handling
- Log security events

## Testing Guidelines

### Unit Tests
- Test individual functions and classes
- Mock external dependencies
- Focus on business logic
- Fast execution

### Integration Tests
- Test API endpoints end-to-end
- Use test client for HTTP requests
- Test with real FastMCP components
- May be slower

### Test Fixtures
- Reusable test data in `tests/fixtures/`
- Pytest fixtures in `conftest.py`
- Mock MCP servers for testing

## Debugging

### Local Development
```bash
# Run with debug logging
uv run uvicorn mcp_proxy_hub.main:create_app --factory --log-level debug

# Use debugger
import pdb; pdb.set_trace()
```

### Common Issues
- **Import errors**: Check `PYTHONPATH` and package structure
- **Session not found**: Check session TTL and cleanup timing
- **Connection errors**: Verify remote MCP server accessibility
- **Authentication errors**: Check token format and headers

## Performance Considerations

### Async/Await
- All I/O operations should be async
- Use `async with` for resource management
- Avoid blocking operations in async functions

### Session Management
- Sessions stored in memory (consider Redis for production)
- Background cleanup prevents memory leaks
- Connection pooling for remote servers

### Monitoring
- Add logging for performance metrics
- Monitor session creation/cleanup rates
- Track remote server response times

## Contributing

### Code Style
- Follow PEP 8 with Black formatting
- Use type hints throughout
- Document public APIs
- Write descriptive commit messages

### Pull Request Process
1. Create feature branch from main
2. Implement changes with tests
3. Run code quality checks
4. Update documentation if needed
5. Submit PR with clear description

### Documentation
- Update relevant markdown files
- Add docstrings to new functions
- Update API documentation
- Include examples where helpful