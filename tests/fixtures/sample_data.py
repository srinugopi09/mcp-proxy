"""Sample data for testing."""

from datetime import datetime, timedelta
from typing import Any, Dict, List

# Sample session requests
SAMPLE_SESSION_REQUESTS = [
    {
        "remote_url": "https://api.example.com/mcp",
        "token": "bearer-token-123",
    },
    {
        "remote_url": "https://mcp.service.com/api/v1/mcp",
        "headers": {
            "Authorization": "Bearer custom-token",
            "X-API-Key": "api-key-456",
            "X-Client-Version": "1.0.0"
        }
    },
    {
        "remote_url": "http://dev.example.com:8080/mcp",
        "token": "dev-token",
        "headers": {
            "X-Environment": "development"
        }
    }
]

# Sample tool call requests
SAMPLE_TOOL_REQUESTS = [
    {
        "arguments": {},
        "stream": False
    },
    {
        "arguments": {
            "query": "test query",
            "limit": 10,
            "include_metadata": True
        },
        "stream": False
    },
    {
        "arguments": {
            "file_path": "/tmp/test.txt",
            "content": "Hello, world!",
            "encoding": "utf-8"
        },
        "stream": True
    },
    {
        "arguments": {
            "url": "https://api.example.com/data",
            "method": "GET",
            "headers": {
                "Accept": "application/json"
            }
        },
        "stream": False
    }
]

# Sample tool definitions
SAMPLE_TOOLS = [
    {
        "name": "echo",
        "description": "Echo back the input message",
        "arguments": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "Message to echo back"
                }
            },
            "required": ["message"]
        },
        "returns": {
            "type": "object",
            "properties": {
                "echoed": {
                    "type": "string",
                    "description": "The echoed message"
                }
            }
        },
        "structured": True
    },
    {
        "name": "calculate",
        "description": "Perform basic arithmetic calculations",
        "arguments": {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["add", "subtract", "multiply", "divide"],
                    "description": "The operation to perform"
                },
                "a": {
                    "type": "number",
                    "description": "First operand"
                },
                "b": {
                    "type": "number",
                    "description": "Second operand"
                }
            },
            "required": ["operation", "a", "b"]
        },
        "returns": {
            "type": "object",
            "properties": {
                "result": {
                    "type": "number",
                    "description": "The calculation result"
                }
            }
        },
        "structured": True
    },
    {
        "name": "fetch_data",
        "description": "Fetch data from a remote API",
        "arguments": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "format": "uri",
                    "description": "URL to fetch data from"
                },
                "timeout": {
                    "type": "integer",
                    "default": 30,
                    "description": "Request timeout in seconds"
                }
            },
            "required": ["url"]
        },
        "returns": {
            "type": "object",
            "properties": {
                "status_code": {
                    "type": "integer",
                    "description": "HTTP status code"
                },
                "data": {
                    "type": "object",
                    "description": "Response data"
                }
            }
        },
        "structured": False
    }
]

# Sample tool results
SAMPLE_TOOL_RESULTS = [
    {
        "content": "Echo: Hello, world!",
        "structured_content": {
            "echoed": "Hello, world!"
        }
    },
    {
        "content": "Calculation result: 42",
        "structured_content": {
            "result": 42,
            "operation": "add",
            "operands": [20, 22]
        }
    },
    {
        "content": "Data fetched successfully",
        "structured_content": {
            "status_code": 200,
            "data": {
                "users": [
                    {"id": 1, "name": "Alice"},
                    {"id": 2, "name": "Bob"}
                ],
                "total": 2
            }
        }
    }
]

# Sample session data
def create_sample_session_data(session_id: str = "test-session-123") -> Dict[str, Any]:
    """Create sample session data for testing."""
    return {
        "session_id": session_id,
        "prefix": session_id,
        "remote_url": "https://api.example.com/mcp",
        "expires_at": datetime.utcnow() + timedelta(hours=1)
    }

# Invalid URLs for testing security
INVALID_URLS = [
    "ftp://example.com/mcp",
    "file:///etc/passwd",
    "javascript:alert('xss')",
    "data:text/html,<script>alert('xss')</script>",
    "http://localhost/mcp",
    "http://127.0.0.1/mcp",
    "http://192.168.1.1/mcp",
    "http://10.0.0.1/mcp",
    "http://172.16.0.1/mcp",
]

# Valid URLs for testing
VALID_URLS = [
    "https://api.example.com/mcp",
    "http://public.example.com/mcp",
    "https://mcp.service.com:8080/api/v1/mcp",
    "http://8.8.8.8/mcp",
    "https://1.1.1.1:443/mcp",
]