"""Coordinate the lifecycle of the two bridge transports."""

from __future__ import annotations

import asyncio
import json
import logging
import random
from datetime import UTC, datetime, timedelta
from typing import Any

import websockets
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    ATTR_CONNECTED,
    ATTR_ERROR_COUNT,
    ATTR_LAST_SEEN,
    ATTR_MESSAGE_COUNT,
    ATTR_RECONNECT_COUNT,
    CONF_ENABLE_LOGGING,
    CONNECTION_MONITOR_INTERVAL,
    CONNECTION_TIMEOUT,
    INITIAL_BACKOFF,
    MAX_BACKOFF,
    MAX_CONSECUTIVE_FAILURES,
    MAX_RECONNECT_ATTEMPTS,
)
from .mcp_client import XiaozhiMCPClient
from .security import (
    MAX_MESSAGE_BYTES,
    WEBSOCKET_LOGGER,
    validate_message,
    validate_url,
)

_LOGGER = logging.getLogger(__name__)


class XiaozhiMCPCoordinator(DataUpdateCoordinator):
    """Keep one connection pair, cancelling both pipes when either closes."""

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
        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name=name,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.config_entry = config_entry
        self.xiaozhi_endpoint = validate_url(xiaozhi_endpoint, websocket=True)
        self.enable_logging = config_entry.options.get(
            CONF_ENABLE_LOGGING, config_entry.data.get(CONF_ENABLE_LOGGING, False)
        )
        self._mcp_client = XiaozhiMCPClient(hass, access_token, mcp_server_url)
        self._connected = self._connecting = self._manual_disconnect = False
        self._websocket = None
        self._reconnect_task = self._message_task = self._connection_monitor_task = None
        self._reconnect_count = self._message_count = self._error_count = 0
        self._consecutive_failures = 0
        self._last_seen = None
        self._backoff = INITIAL_BACKOFF
        self._lifecycle_lock = asyncio.Lock()

    async def async_setup(self) -> None:
        self._initialize_logger_levels()
        await self.async_reconnect()
        self._connection_monitor_task = asyncio.create_task(
            self._connection_monitor_loop()
        )
        await self.async_refresh()

    def _initialize_logger_levels(self) -> None:
        level = logging.DEBUG if self.enable_logging else logging.INFO
        for suffix in ("", ".coordinator", ".mcp_client", ".switch"):
            logging.getLogger("custom_components.xiaozhi_mcp" + suffix).setLevel(level)

    async def _cancel_task(self, name: str) -> None:
        task = getattr(self, name)
        if task and task is not asyncio.current_task():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        setattr(self, name, None)

    async def _close_transports(self) -> None:
        await self._cancel_task("_message_task")
        if self._websocket:
            await self._websocket.close()
            self._websocket = None
        await self._mcp_client.disconnect_from_mcp()
        self._connected = False

    async def async_disconnect(self) -> None:
        """Stop forwarding and reconnecting until explicitly enabled again."""
        async with self._lifecycle_lock:
            self._manual_disconnect = True
            await self._cancel_task("_reconnect_task")
            await self._close_transports()
            self._connecting = False

    async def async_shutdown(self) -> None:
        await self.async_disconnect()
        await self._cancel_task("_connection_monitor_task")

    async def async_reconnect(self) -> None:
        async with self._lifecycle_lock:
            self._manual_disconnect = True
            await self._cancel_task("_reconnect_task")
            await self._close_transports()
            self._manual_disconnect = False
            self._connecting = True
            self._reconnect_task = asyncio.create_task(self._reconnect_loop())

    async def async_wait_for_connection(self, timeout: float = 30) -> bool:
        deadline = asyncio.get_running_loop().time() + timeout
        while asyncio.get_running_loop().time() < deadline:
            if self._connected:
                return True
            await asyncio.sleep(0.1)
        return self._connected

    async def _connection_monitor_loop(self) -> None:
        while True:
            try:
                if not self._connecting and not self._manual_disconnect:
                    if self._connected and self._websocket:
                        try:
                            pong = await self._websocket.ping()
                            await asyncio.wait_for(pong, CONNECTION_TIMEOUT)
                            self._consecutive_failures = 0
                            self._last_seen = datetime.now(UTC)
                        except Exception as err:
                            self._consecutive_failures += 1
                            _LOGGER.warning(
                                "Connection health check failed (%s)",
                                type(err).__name__,
                            )
                            if self._consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                                await self.async_reconnect()
                    else:
                        await self.async_reconnect()
                await asyncio.sleep(CONNECTION_MONITOR_INTERVAL)
            except asyncio.CancelledError:
                raise
            except Exception as err:
                _LOGGER.warning("Connection monitor failed (%s)", type(err).__name__)
                await asyncio.sleep(CONNECTION_MONITOR_INTERVAL)

    async def _reconnect_loop(self) -> None:
        self._connecting = True
        try:
            while not self._manual_disconnect:
                try:
                    await self._connect()
                    self._backoff = INITIAL_BACKOFF
                    self._reconnect_count = self._consecutive_failures = 0
                    return
                except Exception as err:
                    self._reconnect_count += 1
                    self._error_count += 1
                    _LOGGER.warning(
                        "Connection attempt failed (%s)", type(err).__name__
                    )
                    if self._reconnect_count > MAX_RECONNECT_ATTEMPTS:
                        return
                    await asyncio.sleep(self._backoff * (1 + random.random() * 0.1))
                    self._backoff = min(self._backoff * 2, MAX_BACKOFF)
        finally:
            self._connecting = False

    async def _connect(self) -> None:
        try:
            await self._mcp_client.connect_to_mcp()
            # websockets verifies the certificate chain and hostname by default.
            self._websocket = await websockets.connect(
                self.xiaozhi_endpoint,
                logger=WEBSOCKET_LOGGER,
                ping_interval=30,
                ping_timeout=CONNECTION_TIMEOUT,
                close_timeout=10,
                open_timeout=CONNECTION_TIMEOUT,
                max_size=MAX_MESSAGE_BYTES,
                max_queue=16,
            )
            self._connected = True
            self._last_seen = datetime.now(UTC)
            self._message_task = asyncio.create_task(self._handle_messages())
        except BaseException:
            await self._close_transports()
            raise

    async def _handle_messages(self) -> None:
        tasks = [
            asyncio.create_task(self._pipe_websocket_to_mcp()),
            asyncio.create_task(self._pipe_mcp_to_websocket()),
        ]
        try:
            done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                task.result()
        except asyncio.CancelledError:
            raise
        except Exception as err:
            self._error_count += 1
            _LOGGER.warning("Bridge forwarding stopped (%s)", type(err).__name__)
        finally:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            self._connected = False
            # The health monitor owns reconnection; no untracked delayed tasks.

    async def _pipe_websocket_to_mcp(self) -> None:
        async for message in self._websocket:
            validate_message(message)
            await self._mcp_client.send_to_mcp(message)
            self._message_count += 1
            self._last_seen = datetime.now(UTC)
            _LOGGER.debug("Forwarded Xiaozhi message (%d bytes)", len(message))

    async def _pipe_mcp_to_websocket(self) -> None:
        async for message in self._mcp_client.receive_from_mcp():
            validate_message(message)
            await self._websocket.send(message)
            _LOGGER.debug("Forwarded MCP response (%d bytes)", len(message))

    async def async_send_message(self, message: dict[str, Any]) -> None:
        payload = json.dumps(message)
        validate_message(payload)
        if not self._connected or not self._websocket:
            raise UpdateFailed("Not connected to Xiaozhi MCP endpoint")
        try:
            await self._websocket.send(payload)
            self._message_count += 1
        except Exception:
            self._error_count += 1
            raise UpdateFailed("Failed to send message") from None

    async def _async_update_data(self) -> dict[str, Any]:
        return {
            ATTR_CONNECTED: self._connected,
            ATTR_LAST_SEEN: self._last_seen.isoformat() if self._last_seen else None,
            ATTR_RECONNECT_COUNT: self._reconnect_count,
            ATTR_MESSAGE_COUNT: self._message_count,
            ATTR_ERROR_COUNT: self._error_count,
        }

    connected = property(lambda self: self._connected)
    connecting = property(lambda self: self._connecting)
    last_seen = property(lambda self: self._last_seen)
    reconnect_count = property(lambda self: self._reconnect_count)
    message_count = property(lambda self: self._message_count)
    error_count = property(lambda self: self._error_count)
