#!/usr/bin/env python3
"""
Simple test script to verify uvicorn server startup works correctly.
"""

import sys
import os

# Add the project to Python path
sys.path.insert(0, os.path.dirname(__file__))

def test_app_creation():
    """Test that the FastAPI app can be created."""
    try:
        from mcp_registry.api.app import create_app
        app = create_app()
        print("✅ FastAPI app creation successful")
        print(f"   Title: {app.title}")
        print(f"   Version: {app.version}")
        return True
    except Exception as e:
        print(f"❌ FastAPI app creation failed: {e}")
        return False

def test_uvicorn_import():
    """Test that uvicorn can be imported."""
    try:
        import uvicorn
        print("✅ Uvicorn import successful")
        print(f"   Version: {uvicorn.__version__}")
        return True
    except ImportError as e:
        print(f"❌ Uvicorn import failed: {e}")
        return False

def test_settings():
    """Test that settings work correctly."""
    try:
        from mcp_registry.core.config import get_settings
        settings = get_settings()
        print("✅ Settings loading successful")
        print(f"   Host: {settings.host}")
        print(f"   Port: {settings.port}")
        print(f"   Debug: {settings.debug}")
        return True
    except Exception as e:
        print(f"❌ Settings loading failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🧪 Testing MCP Registry Server Components")
    print("=" * 50)
    
    tests = [
        test_settings,
        test_app_creation,
        test_uvicorn_import,
    ]
    
    results = []
    for test in tests:
        print(f"\n🔍 Running {test.__name__}...")
        results.append(test())
    
    print("\n" + "=" * 50)
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"🎉 All tests passed! ({passed}/{total})")
        print("\n✅ Server components are ready!")
        print("\nTo start the server:")
        print("   python -m mcp_registry.cli.main start --debug")
    else:
        print(f"❌ Some tests failed ({passed}/{total})")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())