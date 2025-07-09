"""Test configuration for Xiaozhi MCP integration."""

# Test configuration for pytest
pytest_plugins = "pytest_homeassistant_custom_component"

import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set up environment variables for Home Assistant testing
os.environ["PYTEST_CURRENT_TEST"] = "true"

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

# Define domain constant directly to avoid importing from integration
DOMAIN = "xiaozhi_mcp"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations for all tests."""
    yield


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    return ConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="Test Xiaozhi MCP",
        data={
            "name": "Test Xiaozhi MCP",
            "xiaozhi_endpoint": "wss://test.xiaozhi.me/mcp",
            "access_token": "test_token",
            "scan_interval": 30,
            "enable_logging": False,
        },
        source="test",
        entry_id="test_entry_id",
        unique_id="test_unique_id",
    )
