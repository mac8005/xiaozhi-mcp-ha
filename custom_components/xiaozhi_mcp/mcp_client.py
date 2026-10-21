"""Bounded, authenticated HTTP/SSE transport for Home Assistant MCP."""

from __future__ import annotations

import asyncio
import logging
from contextlib import suppress

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DEFAULT_MCP_SERVER_URL, INITIAL_BACKOFF, MAX_BACKOFF
from .security import (
    MAX_MESSAGE_BYTES,
    resolve_endpoint,
    validate_message,
    validate_url,
)

_LOGGER = logging.getLogger(__name__)


class MCPAuthenticationError(ConnectionError):
    """Home Assistant rejected the bearer token."""


class XiaozhiMCPClient:
    """Own one SSE session and its advertised POST endpoint."""

    def __init__(
        self, hass: HomeAssistant, access_token: str, mcp_server_url: str | None = None
    ):
        self.hass = hass
        self.access_token = access_token
        self.mcp_server_url = validate_url(mcp_server_url or DEFAULT_MCP_SERVER_URL)
        self.session = None
        self._sse_response = None
        self._sse_queue = asyncio.Queue(maxsize=64)
        self._mcp_task = None
        self._disconnecting = False
        self._latest_endpoint = None
        self._ready = asyncio.Event()

    async def _ensure_session(self):
        if self.session is None:
            self.session = async_get_clientsession(self.hass)
        return self.session

    async def connect_to_mcp(self) -> None:
        if not self._mcp_task or self._mcp_task.done():
            self._disconnecting = False
            self._mcp_task = asyncio.create_task(self._sse_run_loop())
        await asyncio.wait_for(self._ready.wait(), timeout=20)

    def _clear_session_state(self):
        self._ready.clear()
        self._latest_endpoint = None
        while not self._sse_queue.empty():
            self._sse_queue.get_nowait()

    async def disconnect_from_mcp(self) -> None:
        self._disconnecting = True
        if self._mcp_task:
            self._mcp_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._mcp_task
            self._mcp_task = None
        self._clear_session_state()

    async def send_to_mcp(self, message: str) -> None:
        validate_message(message)
        if not self._ready.is_set() or not self._latest_endpoint:
            raise ConnectionError("MCP session is not ready")
        url = resolve_endpoint(self.mcp_server_url, self._latest_endpoint)
        session = await self._ensure_session()
        async with session.post(
            url,
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
            },
            data=message,
            allow_redirects=False,
            timeout=aiohttp.ClientTimeout(total=20),
        ) as response:
            if response.status not in (200, 202, 204):
                raise ConnectionError(f"MCP POST failed (HTTP {response.status})")

    async def receive_from_mcp(self):
        while True:
            message = await self._sse_queue.get()
            if message is None:
                raise ConnectionError("MCP session ended")
            yield message

    async def _read_sse_stream(self) -> None:
        event, data, size = "message", [], 0
        async for raw in self._sse_response.content:
            line = raw.decode("utf-8").rstrip("\r\n")
            size += len(raw)
            if size > MAX_MESSAGE_BYTES:
                raise ValueError("SSE event too large")
            if not line:
                if data:
                    payload = "\n".join(data)
                    if event == "endpoint":
                        self._latest_endpoint = resolve_endpoint(
                            self.mcp_server_url, payload
                        )
                        self._ready.set()
                    elif event == "message":
                        validate_message(payload)
                        await self._sse_queue.put(payload)
                event, data, size = "message", [], 0
            elif not line.startswith(":"):
                field, _, value = line.partition(":")
                value = value.removeprefix(" ")
                if field == "event":
                    event = value
                elif field == "data":
                    data.append(value)

    async def _open_sse(self):
        session = await self._ensure_session()
        response = await session.get(
            self.mcp_server_url,
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Accept": "text/event-stream",
            },
            allow_redirects=False,
            timeout=aiohttp.ClientTimeout(total=None, sock_connect=20, sock_read=None),
        )
        if response.status in (401, 403):
            response.close()
            raise MCPAuthenticationError("Home Assistant rejected the access token")
        if response.status != 200 or response.content_type != "text/event-stream":
            response.close()
            raise ConnectionError(f"MCP SSE rejected (HTTP {response.status})")
        return response

    async def _sse_run_loop(self):
        backoff = INITIAL_BACKOFF
        try:
            while not self._disconnecting:
                try:
                    self._sse_response = await self._open_sse()
                    await self._read_sse_stream()
                except asyncio.CancelledError:
                    raise
                except Exception as err:
                    _LOGGER.warning("MCP SSE connection ended (%s)", type(err).__name__)
                finally:
                    was_ready = self._ready.is_set()
                    if self._sse_response:
                        self._sse_response.close()
                        self._sse_response = None
                    self._clear_session_state()
                    if was_ready:
                        self._sse_queue.put_nowait(None)
                # Keep backoff across short-lived streams to avoid retry storms.
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, MAX_BACKOFF)
        finally:
            self._ready.clear()

    async def check_connection(self) -> None:
        """Validate SSE without swallowing authentication or network failures."""
        async with asyncio.timeout(20):
            response = await self._open_sse()
            response.close()

    async def test_connection(self) -> bool:
        try:
            await self.check_connection()
            return True
        except Exception as err:
            _LOGGER.warning("MCP connection test failed (%s)", type(err).__name__)
            return False
