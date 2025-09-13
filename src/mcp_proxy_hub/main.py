"""Main entry point for MCP Proxy Hub."""

import uvicorn

from .app import create_app
from .config import settings


def main() -> None:
    """Main entry point for running the server."""
    app = create_app()
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        log_level="info",
    )


if __name__ == "__main__":
    main()