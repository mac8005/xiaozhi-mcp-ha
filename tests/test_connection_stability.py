"""Test connection stability improvements."""

import asyncio
import unittest.mock
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.xiaozhi_mcp.const import (
    CONF_ACCESS_TOKEN,
    CONF_SCAN_INTERVAL,
    CONF_XIAOZHI_ENDPOINT,
    CONNECTION_MONITOR_INTERVAL,
    CONNECTION_TIMEOUT,
    DOMAIN,
    MAX_CONSECUTIVE_FAILURES,
    SWITCH_CONNECTION_TIMEOUT,
    SWITCH_MAX_RETRIES,
)
from custom_components.xiaozhi_mcp.coordinator import XiaozhiMCPCoordinator


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = MagicMock(spec=HomeAssistant)
    hass.data = {DOMAIN: {}}
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
        },
    )


@pytest.fixture
def coordinator(mock_hass, mock_config_entry):
    """Create a coordinator instance."""
    with patch("custom_components.xiaozhi_mcp.coordinator.XiaozhiMCPClient"):
        return XiaozhiMCPCoordinator(
            mock_hass,
            mock_config_entry,
            "Test Xiaozhi",
            "wss://test.example.com/ws",
            "test_token",
            30,
            "http://localhost:8123/mcp_server/sse",
        )


class TestConnectionStability:
    """Test connection stability features."""

    @pytest.mark.asyncio
    async def test_connection_monitoring_detects_stale_connection(
        self, coordinator, mock_hass
    ):
        """Test that connection monitoring detects stale connections."""
        # Setup mock websocket that will fail ping
        mock_websocket = AsyncMock()
        mock_websocket.ping.side_effect = asyncio.TimeoutError()
        coordinator._websocket = mock_websocket
        coordinator._connected = True

        # Mock the reconnect method
        coordinator.async_reconnect = AsyncMock()

        # Start the connection monitor for a short time
        monitor_task = asyncio.create_task(coordinator._connection_monitor_loop())

        # Wait for a few monitor cycles
        await asyncio.sleep(0.1)

        # Cancel the monitor
        monitor_task.cancel()
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass

        # Verify that consecutive failures were tracked
        assert coordinator._consecutive_failures > 0

    @pytest.mark.asyncio
    async def test_automatic_reconnection_on_failure(self, coordinator, mock_hass):
        """Test that automatic reconnection is triggered after max failures."""
        coordinator._consecutive_failures = MAX_CONSECUTIVE_FAILURES
        coordinator._connected = False
        coordinator._connecting = False

        # Mock the reconnect method
        coordinator.async_reconnect = AsyncMock()

        # Start the connection monitor for a short time
        monitor_task = asyncio.create_task(coordinator._connection_monitor_loop())

        # Wait for monitor cycle
        await asyncio.sleep(0.1)

        # Cancel the monitor
        monitor_task.cancel()
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass

        # Verify that reconnection was triggered
        coordinator.async_reconnect.assert_called()

    @pytest.mark.asyncio
    async def test_connecting_state_prevents_double_reconnection(
        self, coordinator, mock_hass
    ):
        """Test that connecting state prevents multiple reconnection attempts."""
        coordinator._connecting = True
        coordinator._connected = False

        # Mock the reconnect method
        coordinator.async_reconnect = AsyncMock()

        # Start the connection monitor for a short time
        monitor_task = asyncio.create_task(coordinator._connection_monitor_loop())

        # Wait for monitor cycle
        await asyncio.sleep(0.1)

        # Cancel the monitor
        monitor_task.cancel()
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass

        # Verify that reconnection was NOT triggered while connecting
        coordinator.async_reconnect.assert_not_called()

    @pytest.mark.asyncio
    async def test_wait_for_connection_success(self, coordinator, mock_hass):
        """Test waiting for connection establishment."""
        # Simulate connection being established after a short delay
        async def establish_connection():
            await asyncio.sleep(0.1)
            coordinator._connected = True

        # Start the connection establishment
        establish_task = asyncio.create_task(establish_connection())

        # Wait for connection
        result = await coordinator.async_wait_for_connection(timeout=1)

        await establish_task

        assert result is True

    @pytest.mark.asyncio
    async def test_wait_for_connection_timeout(self, coordinator, mock_hass):
        """Test waiting for connection times out."""
        coordinator._connected = False
        coordinator._connecting = False

        # Wait for connection with short timeout
        result = await coordinator.async_wait_for_connection(timeout=0.1)

        assert result is False

    def test_connecting_property(self, coordinator, mock_hass):
        """Test the connecting property."""
        coordinator._connecting = True
        assert coordinator.connecting is True

        coordinator._connecting = False
        assert coordinator.connecting is False

    @pytest.mark.asyncio
    async def test_reconnect_loop_sets_connecting_state(self, coordinator, mock_hass):
        """Test that reconnect loop properly manages connecting state."""
        # Mock the connect method to fail quickly
        coordinator._connect = AsyncMock(side_effect=Exception("Connection failed"))

        # Set a low max attempts for quick test
        with patch(
            "custom_components.xiaozhi_mcp.coordinator.MAX_RECONNECT_ATTEMPTS", 1
        ):
            await coordinator._reconnect_loop()

        # Verify connecting state was reset
        assert coordinator._connecting is False

    def test_new_timeout_constants(self):
        """Test that new timeout constants have reasonable values."""
        # Verify new timeout values are properly set
        assert CONNECTION_TIMEOUT == 20  # Increased from 10
        assert SWITCH_CONNECTION_TIMEOUT == 45  # New constant
        assert SWITCH_MAX_RETRIES == 3  # New constant
        
        # Ensure values are reasonable
        assert CONNECTION_TIMEOUT > 10  # More than the old value
        assert SWITCH_CONNECTION_TIMEOUT > CONNECTION_TIMEOUT  # Switch timeout should be longer
        assert 1 <= SWITCH_MAX_RETRIES <= 5  # Reasonable retry count