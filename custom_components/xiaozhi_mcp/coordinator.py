"""Data update coordinator for Xiaozhi MCP."""

from __future__ import annotations

import asyncio
import json
import logging
import random
import ssl
from datetime import datetime, timedelta
from typing import Any

import aiohttp
import websockets
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from websockets.exceptions import ConnectionClosed, WebSocketException

from .const import (
    ATTR_CONNECTED,
    ATTR_ERROR_COUNT,
    ATTR_LAST_SEEN,
    ATTR_MESSAGE_COUNT,
    ATTR_RECONNECT_COUNT,
    CONF_ACCESS_TOKEN,
    CONF_ENABLE_LOGGING,
    CONF_SCAN_INTERVAL,
    CONF_XIAOZHI_ENDPOINT,
    DOMAIN,
    INITIAL_BACKOFF,
    MAX_BACKOFF,
    MAX_RECONNECT_ATTEMPTS,
)
from .mcp_client import XiaozhiMCPClient

_LOGGER = logging.getLogger(__name__)


class XiaozhiMCPCoordinator(DataUpdateCoordinator):
    """Coordinator for Xiaozhi MCP integration."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        name: str,
        xiaozhi_endpoint: str,
        access_token: str,
        scan_interval: int,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=name,
            update_interval=timedelta(seconds=scan_interval),
        )

        self.config_entry = config_entry
        self.xiaozhi_endpoint = xiaozhi_endpoint
        self.access_token = access_token
        self.scan_interval = scan_interval
        self.enable_logging = config_entry.data.get(CONF_ENABLE_LOGGING, False)

        # Connection state
        self._connected = False
        self._websocket = None
        self._mcp_client = None
        self._reconnect_count = 0
        self._message_count = 0
        self._error_count = 0
        self._last_seen = None
        self._reconnect_task = None
        self._backoff = INITIAL_BACKOFF

        # Setup MCP client
        self._mcp_client = XiaozhiMCPClient(hass, access_token)

    async def async_setup(self) -> None:
        """Set up the coordinator."""
        _LOGGER.info("Setting up Xiaozhi MCP coordinator")

        # Test MCP Server connection with retry logic
        max_retries = 5
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                _LOGGER.debug("Testing MCP Server connection (attempt %d/%d)", attempt + 1, max_retries)
                
                # Check if MCP Server integration is loaded
                if "mcp_server" not in self.hass.data:
                    _LOGGER.debug("MCP Server integration not yet loaded, waiting...")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                        continue
                    else:
                        raise ConfigEntryNotReady("MCP Server integration not loaded")
                
                # Test connection to MCP Server
                mcp_connected = await self._mcp_client.test_connection()
                if mcp_connected:
                    _LOGGER.info("Successfully connected to MCP Server")
                    break
                else:
                    _LOGGER.debug("MCP Server connection failed, retrying...")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                        continue
                    else:
                        raise ConfigEntryNotReady("Cannot connect to MCP Server")
                        
            except Exception as err:
                _LOGGER.debug("MCP Server connection attempt %d failed: %s", attempt + 1, err)
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                else:
                    _LOGGER.error(
                        "Cannot connect to Home Assistant MCP Server after %d attempts. Please ensure the MCP Server integration is installed and running.",
                        max_retries
                    )
                    raise ConfigEntryNotReady("MCP Server integration not available")

        # Start initial connection
        await self.async_reconnect()

        # Start status update
        await self.async_refresh()

    async def async_shutdown(self) -> None:
        """Shutdown the coordinator."""
        _LOGGER.info("Shutting down Xiaozhi MCP coordinator")

        if self._reconnect_task:
            self._reconnect_task.cancel()

        if self._websocket:
            await self._websocket.close()

        self._connected = False

    async def async_reconnect(self) -> None:
        """Reconnect to the Xiaozhi MCP endpoint."""
        if self._reconnect_task:
            self._reconnect_task.cancel()

        self._reconnect_task = asyncio.create_task(self._reconnect_loop())

    async def _reconnect_loop(self) -> None:
        """Reconnection loop with exponential backoff."""
        while True:
            try:
                if self._reconnect_count > 0:
                    wait_time = self._backoff * (1 + random.random() * 0.1)
                    _LOGGER.info(
                        "Waiting %.2f seconds before reconnection attempt %d",
                        wait_time,
                        self._reconnect_count,
                    )
                    await asyncio.sleep(wait_time)

                await self._connect()

                # Reset backoff on successful connection
                self._backoff = INITIAL_BACKOFF
                break

            except Exception as err:
                self._reconnect_count += 1
                self._error_count += 1

                if self._reconnect_count > MAX_RECONNECT_ATTEMPTS:
                    _LOGGER.error("Max reconnection attempts reached, giving up")
                    break

                _LOGGER.warning(
                    "Connection failed (attempt %d): %s",
                    self._reconnect_count,
                    err,
                )

                # Exponential backoff
                self._backoff = min(self._backoff * 2, MAX_BACKOFF)

    async def _connect(self) -> None:
        """Connect to the WebSocket endpoint."""
        _LOGGER.info("Connecting to Xiaozhi MCP endpoint: %s", self.xiaozhi_endpoint)

        try:
            # Create SSL context properly to avoid blocking calls
            connect_kwargs = {"timeout": 30}
            if self.xiaozhi_endpoint.startswith("wss://"):
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                connect_kwargs["ssl"] = ssl_context

            self._websocket = await websockets.connect(
                self.xiaozhi_endpoint,
                **connect_kwargs,
            )

            self._connected = True
            self._last_seen = datetime.now()
            self._reconnect_count = 0

            _LOGGER.info("Successfully connected to Xiaozhi MCP endpoint")

            # Start message handling
            await self._handle_messages()

        except Exception as err:
            self._connected = False
            self._error_count += 1
            _LOGGER.error("Failed to connect to Xiaozhi MCP endpoint: %s", err)
            raise

    async def _handle_messages(self) -> None:
        """Handle incoming messages from the WebSocket."""
        try:
            async for message in self._websocket:
                self._message_count += 1
                self._last_seen = datetime.now()

                if self.enable_logging:
                    _LOGGER.debug("Received message: %s", message[:200])

                try:
                    data = json.loads(message)
                    response = await self._mcp_client.forward_message(data)

                    if response:
                        await self._websocket.send(json.dumps(response))

                except json.JSONDecodeError:
                    _LOGGER.error("Failed to parse JSON message: %s", message)
                except Exception as err:
                    _LOGGER.error("Error handling message: %s", err)
                    self._error_count += 1

        except ConnectionClosed:
            _LOGGER.warning("WebSocket connection closed")
            self._connected = False
        except WebSocketException as err:
            _LOGGER.error("WebSocket error: %s", err)
            self._connected = False
            self._error_count += 1
        except Exception as err:
            _LOGGER.error("Unexpected error in message handling: %s", err)
            self._connected = False
            self._error_count += 1

    async def async_send_message(self, message: dict[str, Any]) -> None:
        """Send a message to the Xiaozhi endpoint."""
        if not self._connected or not self._websocket:
            raise UpdateFailed("Not connected to Xiaozhi MCP endpoint")

        try:
            await self._websocket.send(json.dumps(message))
            self._message_count += 1

            if self.enable_logging:
                _LOGGER.debug("Sent message: %s", json.dumps(message)[:200])

        except Exception as err:
            _LOGGER.error("Failed to send message: %s", err)
            self._error_count += 1
            raise UpdateFailed(f"Failed to send message: {err}")

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data."""
        return {
            ATTR_CONNECTED: self._connected,
            ATTR_LAST_SEEN: self._last_seen.isoformat() if self._last_seen else None,
            ATTR_RECONNECT_COUNT: self._reconnect_count,
            ATTR_MESSAGE_COUNT: self._message_count,
            ATTR_ERROR_COUNT: self._error_count,
        }

    @property
    def connected(self) -> bool:
        """Return if connected."""
        return self._connected

    @property
    def last_seen(self) -> datetime | None:
        """Return last seen time."""
        return self._last_seen

    @property
    def reconnect_count(self) -> int:
        """Return reconnect count."""
        return self._reconnect_count

    @property
    def message_count(self) -> int:
        """Return message count."""
        return self._message_count

    @property
    def error_count(self) -> int:
        """Return error count."""
        return self._error_count
