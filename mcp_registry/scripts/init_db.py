#!/usr/bin/env python3
"""
Simple database initialization script.

This script initializes the database by running Alembic migrations.
It replaces the CLI database initialization functionality.
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from mcp_registry.core.database import init_database
from mcp_registry.core.config import get_settings


async def main():
    """Initialize the database."""
    try:
        print("🔄 Initializing MCP Registry database...")
        
        settings = get_settings()
        print(f"📍 Database URL: {settings.database_url}")
        
        await init_database(settings.database_url)
        
        print("✅ Database initialized successfully!")
        print("🚀 You can now start the API server with: uv run dev")
        
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())