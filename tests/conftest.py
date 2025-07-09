"""Test configuration for Xiaozhi MCP integration."""

# Test configuration for pytest
pytest_plugins = "pytest_homeassistant_custom_component"

# Test fixtures and configuration
import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from custom_components.xiaozhi_mcp.const import DOMAIN

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
    )

# Auto-use fixtures to mark tests as async
@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable loading custom integrations."""
    yield
