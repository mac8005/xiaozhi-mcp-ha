"""Test the Xiaozhi MCP integration."""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

# Define domain constant directly to avoid importing from integration
DOMAIN = "xiaozhi_mcp"

async def test_setup_entry(hass: HomeAssistant, mock_config_entry: ConfigEntry):
    """Test setting up the integration."""
    # Mock the coordinator and client setup
    with patch('custom_components.xiaozhi_mcp.coordinator.XiaozhiMCPCoordinator') as mock_coordinator_class, \
         patch('custom_components.xiaozhi_mcp.mcp_client.XiaozhiMCPClient') as mock_client_class, \
         patch('homeassistant.config_entries.ConfigEntries.async_forward_entry_setups') as mock_forward_setups, \
         patch('homeassistant.helpers.device_registry.async_get') as mock_device_registry, \
         patch('custom_components.xiaozhi_mcp._async_setup_services') as mock_setup_services:
        
        # Configure the mock coordinator
        mock_coordinator_instance = AsyncMock()
        mock_coordinator_class.return_value = mock_coordinator_instance
        mock_coordinator_instance.async_setup.return_value = None
        
        # Configure the mock client
        mock_client_instance = AsyncMock()
        mock_client_class.return_value = mock_client_instance
        
        # Configure platform setup mock
        mock_forward_setups.return_value = True
        
        # Configure device registry mock
        mock_device_registry.return_value.async_get_or_create.return_value = MagicMock()
        
        # Configure services setup mock
        mock_setup_services.return_value = None
        
        # Import and call the setup function
        from custom_components.xiaozhi_mcp import async_setup_entry
        result = await async_setup_entry(hass, mock_config_entry)
        assert result is True
        assert DOMAIN in hass.data
        assert mock_config_entry.entry_id in hass.data[DOMAIN]

async def test_unload_entry(hass: HomeAssistant, mock_config_entry: ConfigEntry):
    """Test unloading the integration."""
    # Mock the coordinator and client setup
    with patch('custom_components.xiaozhi_mcp.coordinator.XiaozhiMCPCoordinator') as mock_coordinator_class, \
         patch('custom_components.xiaozhi_mcp.mcp_client.XiaozhiMCPClient') as mock_client_class, \
         patch('homeassistant.config_entries.ConfigEntries.async_forward_entry_setups') as mock_forward_setups, \
         patch('homeassistant.config_entries.ConfigEntries.async_unload_platforms') as mock_unload_platforms, \
         patch('homeassistant.helpers.device_registry.async_get') as mock_device_registry, \
         patch('custom_components.xiaozhi_mcp._async_setup_services') as mock_setup_services:
        
        # Configure the mock coordinator
        mock_coordinator_instance = AsyncMock()
        mock_coordinator_class.return_value = mock_coordinator_instance
        mock_coordinator_instance.async_setup.return_value = None
        mock_coordinator_instance.async_shutdown.return_value = None
        
        # Configure the mock client
        mock_client_instance = AsyncMock()
        mock_client_class.return_value = mock_client_instance
        
        # Configure platform setup/unload mocks
        mock_forward_setups.return_value = True
        mock_unload_platforms.return_value = True
        
        # Configure device registry mock
        mock_device_registry.return_value.async_get_or_create.return_value = MagicMock()
        
        # Configure services setup mock
        mock_setup_services.return_value = None
        
        # Import the functions
        from custom_components.xiaozhi_mcp import async_setup_entry, async_unload_entry
        
        # First setup
        await async_setup_entry(hass, mock_config_entry)
        
        # Then unload
        result = await async_unload_entry(hass, mock_config_entry)
        assert result is True
        assert mock_config_entry.entry_id not in hass.data[DOMAIN]
