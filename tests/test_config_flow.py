"""Test the config flow."""

import pytest
from unittest.mock import patch, AsyncMock
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.config_entries import ConfigEntry
from custom_components.xiaozhi_mcp.config_flow import ConfigFlow
from custom_components.xiaozhi_mcp.const import DOMAIN, CONF_XIAOZHI_ENDPOINT

@pytest.mark.asyncio
async def test_config_flow(hass: HomeAssistant):
    """Test the config flow."""
    # Create a config flow instance
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    
    # Test initial form
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"
    
    # Test form with valid data
    with patch('custom_components.xiaozhi_mcp.config_flow.validate_input', return_value={"title": "Test"}):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "name": "Test Xiaozhi MCP",
                "xiaozhi_endpoint": "wss://test.xiaozhi.me/mcp",
                "access_token": "test_token",
                "scan_interval": 30,
                "enable_logging": False,
            }
        )
        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["title"] == "Test"

@pytest.mark.asyncio
async def test_config_flow_already_configured(hass: HomeAssistant):
    """Test that we abort if already configured."""
    # Create a mock config entry
    config_entry = ConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="Test Xiaozhi MCP",
        data={"xiaozhi_endpoint": "wss://test.xiaozhi.me/mcp"},
        source="test",
        entry_id="test_entry_id",
        unique_id="wss://test.xiaozhi.me/mcp",
    )
    config_entry.add_to_hass(hass)
    
    # Try to configure again
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    
    with patch('custom_components.xiaozhi_mcp.config_flow.validate_input', return_value={"title": "Test"}):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "name": "Test Xiaozhi MCP",
                "xiaozhi_endpoint": "wss://test.xiaozhi.me/mcp",
                "access_token": "test_token",
                "scan_interval": 30,
                "enable_logging": False,
            }
        )
        assert result["type"] == FlowResultType.ABORT
        assert result["reason"] == "already_configured"
