"""Test the Xiaozhi MCP integration."""

import pytest
from unittest.mock import patch
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from custom_components.xiaozhi_mcp import async_setup_entry, async_unload_entry
from custom_components.xiaozhi_mcp.const import DOMAIN

@pytest.mark.asyncio
async def test_setup_entry(hass: HomeAssistant, mock_config_entry: ConfigEntry):
    """Test setting up the integration."""
    # Mock the coordinator setup
    with patch('custom_components.xiaozhi_mcp.coordinator.XiaozhiMCPCoordinator.async_setup'):
        result = await async_setup_entry(hass, mock_config_entry)
        assert result is True
        assert DOMAIN in hass.data
        assert mock_config_entry.entry_id in hass.data[DOMAIN]

@pytest.mark.asyncio
async def test_unload_entry(hass: HomeAssistant, mock_config_entry: ConfigEntry):
    """Test unloading the integration."""
    # First setup
    with patch('custom_components.xiaozhi_mcp.coordinator.XiaozhiMCPCoordinator.async_setup'), \
         patch('custom_components.xiaozhi_mcp.coordinator.XiaozhiMCPCoordinator.async_shutdown'):
        await async_setup_entry(hass, mock_config_entry)
        
        # Then unload
        result = await async_unload_entry(hass, mock_config_entry)
        assert result is True
        assert mock_config_entry.entry_id not in hass.data[DOMAIN]
