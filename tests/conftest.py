"""Test configuration for Xiaozhi MCP integration."""

# Test configuration for pytest
pytest_plugins = "pytest_homeassistant_custom_component"

# Test fixtures and configuration
import pytest
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from custom_components.xiaozhi_mcp.const import DOMAIN

@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    return ConfigEntry(
        version=1,
        domain=DOMAIN,
        title="Test Xiaozhi MCP",
        data={
            "name": "Test Xiaozhi MCP",
            "xiaozhi_endpoint": "wss://test.xiaozhi.me/mcp",
            "access_token": "test_token",
            "ha_url": "http://test.homeassistant.local:8123",
            "scan_interval": 30,
            "enable_logging": False,
        },
        source="test",
        entry_id="test_entry_id",
    )
