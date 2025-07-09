"""Test the config flow."""

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from custom_components.xiaozhi_mcp.config_flow import ConfigFlow
from custom_components.xiaozhi_mcp.const import DOMAIN

async def test_config_flow(hass: HomeAssistant):
    """Test the config flow."""
    flow = ConfigFlow()
    flow.hass = hass
    
    # Test initial form
    result = await flow.async_step_user()
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"
    
    # Test form with valid data
    with patch('custom_components.xiaozhi_mcp.config_flow.validate_input', return_value={"title": "Test"}):
        result = await flow.async_step_user({
            "name": "Test Xiaozhi MCP",
            "xiaozhi_endpoint": "wss://test.xiaozhi.me/mcp",
            "access_token": "test_token",
            "ha_url": "http://test.homeassistant.local:8123",
            "scan_interval": 30,
            "enable_logging": False,
        })
        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["title"] == "Test"
