"""Test debug logging toggle functionality."""

import asyncio
import logging
import unittest.mock
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.components.switch import SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.xiaozhi_mcp.const import (
    CONF_ACCESS_TOKEN,
    CONF_ENABLE_LOGGING,
    CONF_SCAN_INTERVAL,
    CONF_XIAOZHI_ENDPOINT,
    DOMAIN,
)
from custom_components.xiaozhi_mcp.coordinator import XiaozhiMCPCoordinator
from custom_components.xiaozhi_mcp.switch import XiaozhiMCPSwitch


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = MagicMock(spec=HomeAssistant)
    hass.data = {DOMAIN: {}}
    hass.config_entries = MagicMock()
    hass.config_entries.async_update_entry = AsyncMock()
    return hass


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    return MagicMock(
        spec=ConfigEntry,
        entry_id="test_entry",
        data={
            "name": "Test Xiaozhi",
            CONF_XIAOZHI_ENDPOINT: "wss://test.example.com/ws",
            CONF_ACCESS_TOKEN: "test_token",
            CONF_SCAN_INTERVAL: 30,
            CONF_ENABLE_LOGGING: False,
        },
    )


@pytest.fixture
def coordinator(mock_hass, mock_config_entry):
    """Create a coordinator instance."""
    with patch("custom_components.xiaozhi_mcp.coordinator.async_get_clientsession"):
        coordinator = XiaozhiMCPCoordinator(
            mock_hass,
            mock_config_entry,
            "Test Xiaozhi",
            "wss://test.example.com/ws",
            "test_token",
            30,
            "http://localhost:8123/mcp_server/sse",
        )
        # Mock the async_request_refresh method
        coordinator.async_request_refresh = AsyncMock()
        return coordinator


@pytest.fixture
def debug_switch(coordinator, mock_hass):
    """Create a debug logging switch."""
    description = SwitchEntityDescription(
        key="debug_logging",
        name="Debug Logging", 
        icon="mdi:bug",
    )
    switch = XiaozhiMCPSwitch(coordinator, description)
    switch.hass = mock_hass
    return switch


class TestDebugLoggingToggle:
    """Test debug logging toggle functionality."""

    def test_initial_state(self, debug_switch, coordinator):
        """Test initial debug logging state."""
        # Should be off by default
        assert debug_switch.is_on is False
        assert coordinator.enable_logging is False

    @pytest.mark.asyncio
    async def test_turn_on_debug_logging(self, debug_switch, coordinator, mock_hass):
        """Test turning on debug logging."""
        # Initial state
        assert debug_switch.is_on is False
        assert coordinator.enable_logging is False
        
        # Get initial logger level
        logger = logging.getLogger("custom_components.xiaozhi_mcp")
        initial_level = logger.level
        
        # Turn on debug logging
        await debug_switch.async_turn_on()
        
        # Verify state changed
        assert debug_switch.is_on is True
        assert coordinator.enable_logging is True
        
        # Verify logger level changed to DEBUG
        assert logger.level == logging.DEBUG
        
        # Verify config entry update was called
        mock_hass.config_entries.async_update_entry.assert_called_once()
        call_args = mock_hass.config_entries.async_update_entry.call_args
        assert call_args[0][0] == coordinator.config_entry
        assert call_args[1]["data"][CONF_ENABLE_LOGGING] is True

    @pytest.mark.asyncio
    async def test_turn_off_debug_logging(self, debug_switch, coordinator, mock_hass):
        """Test turning off debug logging."""
        # First turn it on
        await debug_switch.async_turn_on()
        assert debug_switch.is_on is True
        assert coordinator.enable_logging is True
        
        # Reset mock call count
        mock_hass.config_entries.async_update_entry.reset_mock()
        
        # Turn off debug logging
        await debug_switch.async_turn_off()
        
        # Verify state changed
        assert debug_switch.is_on is False
        assert coordinator.enable_logging is False
        
        # Verify logger level changed to INFO
        logger = logging.getLogger("custom_components.xiaozhi_mcp")
        assert logger.level == logging.INFO
        
        # Verify config entry update was called
        mock_hass.config_entries.async_update_entry.assert_called_once()
        call_args = mock_hass.config_entries.async_update_entry.call_args
        assert call_args[0][0] == coordinator.config_entry
        assert call_args[1]["data"][CONF_ENABLE_LOGGING] is False

    @pytest.mark.asyncio
    async def test_logger_level_initialization(self, mock_hass, mock_config_entry):
        """Test that logger levels are initialized correctly."""
        # Test with debug enabled
        mock_config_entry.data[CONF_ENABLE_LOGGING] = True
        
        with patch("custom_components.xiaozhi_mcp.coordinator.async_get_clientsession"):
            coordinator = XiaozhiMCPCoordinator(
                mock_hass,
                mock_config_entry,
                "Test Xiaozhi",
                "wss://test.example.com/ws",
                "test_token",
                30,
                "http://localhost:8123/mcp_server/sse",
            )
            
            # Initialize logger levels
            coordinator._initialize_logger_levels()
            
            # Verify logger is set to DEBUG
            logger = logging.getLogger("custom_components.xiaozhi_mcp")
            assert logger.level == logging.DEBUG

    def test_multiple_logger_initialization(self, coordinator):
        """Test that multiple loggers are initialized."""
        # Enable debug logging
        coordinator.enable_logging = True
        coordinator._initialize_logger_levels()
        
        # Check that all loggers are set to DEBUG
        loggers = [
            "custom_components.xiaozhi_mcp",
            "custom_components.xiaozhi_mcp.coordinator",
            "custom_components.xiaozhi_mcp.mcp_client", 
            "custom_components.xiaozhi_mcp.switch",
        ]
        
        for logger_name in loggers:
            logger = logging.getLogger(logger_name)
            assert logger.level == logging.DEBUG