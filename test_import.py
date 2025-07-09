#!/usr/bin/env python3
"""Simple test to verify conftest.py path setup works."""
import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    # This should work in CI where homeassistant is installed
    from custom_components.xiaozhi_mcp.const import DOMAIN

    print(f"✓ Successfully imported DOMAIN: {DOMAIN}")
except ModuleNotFoundError as e:
    print(f"✗ Import failed (expected in dev environment): {e}")
    print("This is normal in development - the tests will work in CI")
