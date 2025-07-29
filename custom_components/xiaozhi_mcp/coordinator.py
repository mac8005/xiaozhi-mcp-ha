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
    CONNECTION_MONITOR_INTERVAL,
    CONNECTION_TIMEOUT,
    DOMAIN,
    INITIAL_BACKOFF,
    MAX_BACKOFF,
    MAX_CONSECUTIVE_FAILURES,
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
        mcp_server_url: str,
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
        self.mcp_server_url = mcp_server_url
        self.enable_logging = config_entry.data.get(CONF_ENABLE_LOGGING, False)

        # Connection state
        self._connected = False
        self._connecting = False  # Track if currently attempting to connect
        self._websocket = None
        self._mcp_client = None
        self._reconnect_count = 0
        self._message_count = 0
        self._error_count = 0
        self._last_seen = None
        self._reconnect_task = None
        self._connection_monitor_task = None
        self._consecutive_failures = 0  # Track consecutive connection failures
        self._backoff = INITIAL_BACKOFF

        # Setup MCP client
        self._mcp_client = XiaozhiMCPClient(hass, access_token, mcp_server_url)

    async def async_setup(self) -> None:
        """Set up the coordinator."""
        _LOGGER.info("Setting up Xiaozhi MCP coordinator")

        # Test MCP Server connection with retry logic
        max_retries = 5
        retry_delay = 2

        for attempt in range(max_retries):
            try:
                _LOGGER.debug(
                    "Testing MCP Server connection (attempt %d/%d)",
                    attempt + 1,
                    max_retries,
                )

                # Test connection to MCP Server directly
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
                        _LOGGER.warning(
                            "Cannot connect to MCP Server after %d attempts. Continuing without MCP Server dependency check.",
                            max_retries,
                        )
                        # Don't fail setup - just log warning and continue
                        break

            except Exception as err:
                _LOGGER.debug(
                    "MCP Server connection attempt %d failed: %s", attempt + 1, err
                )
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                else:
                    _LOGGER.warning(
                        "Cannot connect to Home Assistant MCP Server after %d attempts. Integration will continue but MCP functionality may be limited. Error: %s",
                        max_retries,
                        err,
                    )
                    # Don't raise ConfigEntryNotReady - just continue
                    break

        # Start initial connection
        await self.async_reconnect()

        # Start connection monitoring
        self._connection_monitor_task = asyncio.create_task(
            self._connection_monitor_loop()
        )

        # Start status update
        await self.async_refresh()

    async def async_shutdown(self) -> None:
        """Shutdown the coordinator."""
        _LOGGER.info("Shutting down Xiaozhi MCP coordinator")

        # Cancel monitoring and reconnection tasks
        if self._connection_monitor_task:
            self._connection_monitor_task.cancel()
            try:
                await self._connection_monitor_task
            except asyncio.CancelledError:
                pass

        if self._reconnect_task:
            self._reconnect_task.cancel()
            try:
                await self._reconnect_task
            except asyncio.CancelledError:
                pass

        if self._websocket:
            await self._websocket.close()

        # Clean up MCP connection
        if self._mcp_client:
            await self._mcp_client.disconnect_from_mcp()

        self._connected = False
        self._connecting = False

    async def async_reconnect(self) -> None:
        """Reconnect to the Xiaozhi MCP endpoint."""
        if self._reconnect_task:
            self._reconnect_task.cancel()

        self._reconnect_task = asyncio.create_task(self._reconnect_loop())

    async def async_wait_for_connection(self, timeout: int = 30) -> bool:
        """Wait for connection to be established, with timeout."""
        start_time = datetime.now()
        while (datetime.now() - start_time).total_seconds() < timeout:
            if self._connected:
                return True
            if not self._connecting:
                # Not connecting anymore but also not connected - failed
                return False
            await asyncio.sleep(0.5)  # Check every 500ms
        return False  # Timeout reached

    async def _connection_monitor_loop(self) -> None:
        """Monitor connection health and trigger automatic reconnection if needed."""
        _LOGGER.debug("Starting connection health monitor")

        while True:
            try:
                await asyncio.sleep(CONNECTION_MONITOR_INTERVAL)

                # Skip monitoring if we're already reconnecting
                if self._connecting:
                    continue

                # Check if connection appears healthy
                if self._connected and self._websocket:
                    try:
                        # Check if websocket is still alive with a ping
                        pong_waiter = await self._websocket.ping()
                        await asyncio.wait_for(pong_waiter, timeout=CONNECTION_TIMEOUT)

                        # Reset failure count on successful ping
                        if self._consecutive_failures > 0:
                            _LOGGER.debug("Connection ping successful, resetting failure count")
                        self._consecutive_failures = 0

                        # Update last seen time
                        self._last_seen = datetime.now()

                    except (asyncio.TimeoutError, ConnectionClosed, WebSocketException) as err:
                        self._consecutive_failures += 1
                        _LOGGER.warning(
                            "Connection health check failed (attempt %d/%d): %s",
                            self._consecutive_failures,
                            MAX_CONSECUTIVE_FAILURES,
                            err
                        )

                        if self._consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                            _LOGGER.warning(
                                "Connection appears stale after %d consecutive failures, triggering reconnection",
                                self._consecutive_failures,
                            )
                            self._connected = False
                            # Wait a moment before triggering reconnection to avoid rapid retries
                            await asyncio.sleep(1)
                            await self.async_reconnect()
                    except Exception as err:
                        # Handle unexpected errors in ping
                        self._consecutive_failures += 1
                        _LOGGER.error(
                            "Unexpected error during connection health check (attempt %d/%d): %s",
                            self._consecutive_failures,
                            MAX_CONSECUTIVE_FAILURES,
                            err
                        )
                        
                        if self._consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                            _LOGGER.warning(
                                "Connection health check errors exceeded threshold, triggering reconnection"
                            )
                            self._connected = False
                            await asyncio.sleep(1)
                            await self.async_reconnect()

                elif not self._connected and not self._connecting:
                    # Connection is down and we're not trying to reconnect
                    _LOGGER.info(
                        "Connection is down, triggering automatic reconnection"
                    )
                    await self.async_reconnect()

            except asyncio.CancelledError:
                _LOGGER.debug("Connection monitor task cancelled")
                break
            except Exception as err:
                _LOGGER.error("Error in connection monitor: %s", err)
                # Don't break the loop on unexpected errors
                await asyncio.sleep(CONNECTION_MONITOR_INTERVAL)

    async def _reconnect_loop(self) -> None:
        """Reconnection loop with exponential backoff and jitter like the working example."""
        self._connecting = True

        try:
            while True:
                try:
                    if self._reconnect_count > 0:
                        # Add jitter like in the working example
                        wait_time = self._backoff * (1 + random.random() * 0.1)
                        _LOGGER.info(
                            "Waiting %.2f seconds before reconnection attempt %d",
                            wait_time,
                            self._reconnect_count,
                        )
                        await asyncio.sleep(wait_time)

                    await self._connect()

                    # Reset backoff on successful connection (like working example)
                    self._backoff = INITIAL_BACKOFF
                    self._reconnect_count = 0
                    self._consecutive_failures = (
                        0  # Reset failure count on successful connection
                    )
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

                    # Exponential backoff with max limit
                    self._backoff = min(self._backoff * 2, MAX_BACKOFF)
        finally:
            self._connecting = False

    async def _connect(self) -> None:
        """Connect to the WebSocket endpoint and MCP Server."""
        _LOGGER.info("Connecting to Xiaozhi MCP endpoint: %s", self.xiaozhi_endpoint)

        try:
            # First, establish MCP connection
            await self._mcp_client.connect_to_mcp()
            _LOGGER.info("✅ Connected to MCP Server")

            # Validate Xiaozhi endpoint format
            if not self.xiaozhi_endpoint.startswith(("ws://", "wss://")):
                raise ValueError(
                    f"Invalid Xiaozhi endpoint format: {self.xiaozhi_endpoint}. Must start with ws:// or wss://"
                )

            _LOGGER.info(
                "🔗 Connecting to Xiaozhi WebSocket: %s",
                (
                    self.xiaozhi_endpoint[:50] + "..."
                    if len(self.xiaozhi_endpoint) > 50
                    else self.xiaozhi_endpoint
                ),
            )

            # Create SSL context properly to avoid blocking calls
            connect_kwargs = {}
            if self.xiaozhi_endpoint.startswith("wss://"):
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                connect_kwargs["ssl"] = ssl_context

            try:
                self._websocket = await websockets.connect(
                    self.xiaozhi_endpoint,
                    ping_interval=30,  # Increased from 20 for more stable long-running connections
                    ping_timeout=CONNECTION_TIMEOUT,  # Now 20 seconds, increased from 10
                    close_timeout=15,  # Increased from 10 for cleaner disconnections
                    **connect_kwargs,
                )
                _LOGGER.info("✅ Connected to Xiaozhi WebSocket successfully")
            except ConnectionRefusedError:
                raise Exception(
                    "Xiaozhi WebSocket connection refused. Check if the endpoint URL is correct and the service is available."
                )
            except websockets.InvalidURI:
                raise Exception(
                    f"Invalid Xiaozhi WebSocket URI: {self.xiaozhi_endpoint}"
                )
            except Exception as err:
                raise Exception(f"Failed to connect to Xiaozhi WebSocket: {err}")

            self._connected = True
            self._last_seen = datetime.now()
            self._reconnect_count = 0

            _LOGGER.info("Successfully connected to Xiaozhi MCP endpoint")

            # Start bidirectional message handling
            await self._handle_messages()

        except Exception as err:
            self._connected = False
            self._error_count += 1
            _LOGGER.error("Failed to connect: %s", err)

            # Clean up MCP connection on failure
            await self._mcp_client.disconnect_from_mcp()
            raise

    async def _handle_messages(self) -> None:
        """Handle bidirectional communication between Xiaozhi WebSocket and HA MCP Server."""
        try:
            # Create bidirectional pipe using asyncio.gather like the working example
            await asyncio.gather(
                self._pipe_websocket_to_mcp(),
                self._pipe_mcp_to_websocket(),
                return_exceptions=True,
            )
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

    async def _pipe_websocket_to_mcp(self) -> None:
        """Pipe messages from Xiaozhi WebSocket to HA MCP Server."""
        try:
            async for message in self._websocket:
                self._message_count += 1
                self._last_seen = datetime.now()

                if self.enable_logging:
                    _LOGGER.debug("Xiaozhi → MCP: %s", message[:200])

                # Validate message format before forwarding
                try:
                    # Check if it's valid JSON
                    json.loads(message)
                    # Forward message directly to MCP Server
                    await self._mcp_client.send_to_mcp(message)
                except json.JSONDecodeError:
                    _LOGGER.warning(
                        "Received non-JSON message from Xiaozhi, forwarding as-is: %s",
                        message[:100],
                    )
                    # Forward anyway, MCP server might handle it
                    await self._mcp_client.send_to_mcp(message)
                except Exception as err:
                    _LOGGER.error("Failed to forward message to MCP: %s", err)
                    # Don't re-raise here, continue processing other messages

        except ConnectionClosed as err:
            if err.code == 4004:
                _LOGGER.error(
                    "Xiaozhi WebSocket closed with internal server error (4004)."
                )
            else:
                _LOGGER.warning("Xiaozhi WebSocket connection closed: %s", err)
            self._error_count += 1
            raise  # Re-raise to trigger reconnection
        except WebSocketException as err:
            _LOGGER.error("Xiaozhi WebSocket error: %s", err)
            self._error_count += 1
            raise  # Re-raise to trigger reconnection
        except Exception as err:
            _LOGGER.error("Error in WebSocket to MCP pipe: %s", err)
            self._error_count += 1
            raise  # Re-raise to trigger reconnection

    async def _pipe_mcp_to_websocket(self) -> None:
        """Pipe messages from HA MCP Server to Xiaozhi WebSocket."""
        try:
            async for message in self._mcp_client.receive_from_mcp():
                if self.enable_logging:
                    _LOGGER.debug("MCP → Xiaozhi: %s", message[:200])

                # Validate message before sending to Xiaozhi
                try:
                    # Check if it's valid JSON
                    json.loads(message)
                    # Forward message back to Xiaozhi
                    await self._websocket.send(message)
                except json.JSONDecodeError:
                    _LOGGER.warning(
                        "Received non-JSON message from MCP, forwarding as-is: %s",
                        message[:100],
                    )
                    # Forward anyway, Xiaozhi might handle it
                    await self._websocket.send(message)
                except Exception as err:
                    _LOGGER.error("Failed to forward MCP response to Xiaozhi: %s", err)
                    # Don't re-raise here, continue processing other messages

        except ConnectionClosed as err:
            if err.code == 4004:
                _LOGGER.error(
                    "Xiaozhi WebSocket closed with internal server error (4004) while sending MCP response."
                )
                _LOGGER.error(
                    "This indicates the Xiaozhi service rejected our response format or content."
                )
            else:
                _LOGGER.warning(
                    "Xiaozhi WebSocket connection closed while sending MCP response: %s",
                    err,
                )
            self._error_count += 1
            raise  # Re-raise to trigger reconnection
        except WebSocketException as err:
            _LOGGER.error("Xiaozhi WebSocket error while sending MCP response: %s", err)
            self._error_count += 1
            raise  # Re-raise to trigger reconnection
        except Exception as err:
            _LOGGER.error("Error in MCP to WebSocket pipe: %s", err)
            self._error_count += 1
            raise  # Re-raise to trigger reconnection

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
    def connecting(self) -> bool:
        """Return if currently attempting to connect."""
        return self._connecting

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
