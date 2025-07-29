"""MCP Client implementation for Xiaozhi integration."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger(__name__)


class XiaozhiMCPClient:
    """MCP Client for connecting to the official Home Assistant MCP Server via SSE."""

    def __init__(
        self, hass: HomeAssistant, access_token: str, mcp_server_url: str = None
    ) -> None:
        """Initialize the MCP client."""
        self.hass = hass
        self.access_token = access_token

        try:
            self.session = async_get_clientsession(hass)
        except Exception as err:
            _LOGGER.warning(
                "Failed to get aiohttp session, will create one later: %s", err
            )
            self.session = None

        # Use provided URL or default
        if mcp_server_url:
            self.mcp_server_url = mcp_server_url
        else:
            # Fallback to localhost if no URL provided
            self.mcp_server_url = "http://localhost:8123/mcp_server/sse"

        _LOGGER.debug("MCP Server URL: %s", self.mcp_server_url)
        self._sse_response = None
        self._sse_queue = asyncio.Queue()
        self._mcp_task = None

        # Endpoint management for MCP protocol compliance
        self._message_endpoints = {}  # Maps message/session IDs to endpoints
        self._latest_endpoint = None  # Last valid endpoint
        self._latest_message_id = None  # Last message id

    async def _ensure_session(self):
        """Ensure we have a valid aiohttp session."""
        if self.session is None:
            try:
                self.session = async_get_clientsession(self.hass)
            except Exception:
                # Fallback to creating our own session
                import aiohttp

                self.session = aiohttp.ClientSession()
        return self.session

    async def connect_to_mcp(self) -> None:
        """Establish connection to MCP Server for streaming."""
        session = await self._ensure_session()

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "text/event-stream",
        }

        # Start persistent SSE connection
        self._sse_response = await session.get(
            self.mcp_server_url,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=None),  # No timeout for SSE
        )

        if self._sse_response.status != 200:
            raise Exception(
                f"MCP Server connection failed: {self._sse_response.status}"
            )

        # Start reading SSE stream
        self._mcp_task = asyncio.create_task(self._read_sse_stream())

    async def disconnect_from_mcp(self) -> None:
        """Disconnect from MCP Server."""
        if self._mcp_task:
            self._mcp_task.cancel()
            self._mcp_task = None

        if self._sse_response:
            self._sse_response.close()
            self._sse_response = None

    async def send_to_mcp(self, message: str) -> None:
        """
        Send message to MCP Server using the correct per-message endpoint.

        This method implements robust endpoint handling to prevent 4004 errors:

        1. Parses message JSON to extract message ID
        2. Maps message ID to correct endpoint (if available)
        3. Falls back to latest endpoint or generic endpoint
        4. Constructs URLs correctly handling both absolute and relative paths
        5. Validates message format and provides detailed error logging

        This prevents the common 4004 error caused by incorrect endpoint forwarding.
        """
        if not self._sse_response:
            raise Exception("Not connected to MCP Server")

        session = await self._ensure_session()

        # Parse the message to extract potential ID for endpoint mapping
        try:
            msg_data = json.loads(message)
            msg_id = msg_data.get("id")

            # Try to find the correct endpoint for this message
            endpoint = None
            if msg_id and msg_id in self._message_endpoints:
                endpoint = self._message_endpoints[msg_id]
            elif self._latest_endpoint:
                endpoint = self._latest_endpoint

            if not endpoint:
                _LOGGER.warning(
                    "No valid MCP message endpoint available. Attempting to use default endpoint."
                )
                # Fallback to a generic message endpoint
                endpoint = "/mcp_server/messages"

            # Build full URL correctly
            # If endpoint is absolute (starts with /), use it as-is
            # If it's relative, append to base URL
            if endpoint.startswith("/"):
                # Absolute path - build URL from base
                base_url = self.mcp_server_url.split("/mcp_server/sse")[
                    0
                ]  # Get protocol://host:port
                url = base_url + endpoint
            else:
                # Relative path - should not happen, but handle it
                base_url = self.mcp_server_url.replace("/sse", "")
                url = base_url + "/" + endpoint.lstrip("/")

        except (json.JSONDecodeError, KeyError) as err:
            _LOGGER.warning(
                "Failed to parse message JSON, using fallback endpoint: %s", err
            )
            # Use a generic endpoint for non-JSON messages
            base_url = self.mcp_server_url.split("/mcp_server/sse")[0]
            url = base_url + "/mcp_server/messages"

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

        try:
            _LOGGER.debug(f"→ Sending to MCP endpoint: {url}")
            _LOGGER.debug(f"→ Message preview: {message[:100]}...")

            async with session.post(url, headers=headers, data=message) as resp:
                if resp.status != 200:
                    response_text = await resp.text()
                    _LOGGER.error(
                        f"Failed to send message to MCP endpoint {url}: {resp.status} - {response_text}"
                    )
                    _LOGGER.error(f"Failed message was: {message}")
                else:
                    _LOGGER.debug(f"✅ Successfully sent message to MCP endpoint {url}")
        except Exception as err:
            _LOGGER.error(f"Exception sending message to MCP endpoint {url}: {err}")
            _LOGGER.error(f"Failed message was: {message}")

    async def receive_from_mcp(self):
        """Async generator to receive messages from MCP Server (yields actual message content)."""
        while True:
            try:
                message = await self._sse_queue.get()
                yield message  # This is now actual message content, not endpoint info
            except asyncio.CancelledError:
                break

    async def _read_sse_stream(self) -> None:
        """Read SSE stream and extract message endpoints and payloads."""
        try:
            async for line in self._sse_response.content:
                line = line.decode("utf-8").strip()
                if line.startswith("data: "):
                    data = line[6:]  # Remove 'data: ' prefix
                    if data and data != "[DONE]":
                        # Check if this is a message endpoint path
                        if data.startswith("/mcp_server/messages/") or data.startswith(
                            "/mcp_server/message/"
                        ):
                            # This is a message endpoint - store it for sending
                            self._latest_endpoint = data
                            msg_id = data.split("/")[-1]  # Extract ID from path
                            self._latest_message_id = msg_id
                            self._message_endpoints[msg_id] = data
                            _LOGGER.debug(f"← Stored MCP endpoint: {data}")
                            # Don't queue endpoint paths as messages
                        elif data.startswith("/mcp_server/"):
                            # This might be another type of MCP endpoint
                            self._latest_endpoint = data
                            _LOGGER.debug(f"← Stored MCP endpoint (generic): {data}")
                        else:
                            # This is actual message content - queue it
                            try:
                                # Validate that it's proper JSON before queuing
                                json.loads(data)
                                await self._sse_queue.put(data)
                                _LOGGER.debug(f"← Queued MCP message: {data[:100]}...")
                            except json.JSONDecodeError:
                                # Not JSON, might be a different format or endpoint
                                if data.startswith("/"):
                                    # Looks like a path - treat as endpoint
                                    self._latest_endpoint = data
                                    _LOGGER.debug(
                                        f"← Stored MCP endpoint (path): {data}"
                                    )
                                else:
                                    # Unknown format, queue anyway but log warning
                                    _LOGGER.warning(
                                        f"← Unknown SSE data format: {data[:100]}..."
                                    )
                                    await self._sse_queue.put(data)
        except asyncio.CancelledError:
            pass
        except Exception as err:
            _LOGGER.error("Error reading SSE stream: %s", err)

    async def test_connection(self) -> bool:
        """Test connection to the MCP Server."""
        try:
            session = await self._ensure_session()

            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Accept": "text/event-stream",
            }

            _LOGGER.debug("Testing MCP Server connection to %s", self.mcp_server_url)

            # Test with a simple GET request to the SSE endpoint
            async with session.get(
                self.mcp_server_url,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                _LOGGER.debug("MCP Server response status: %s", response.status)
                _LOGGER.debug("MCP Server response headers: %s", dict(response.headers))

                # A successful connection should return 200 and SSE content type
                if response.status == 200:
                    content_type = response.headers.get("content-type", "")
                    is_sse = (
                        "text/event-stream" in content_type
                        or "text/plain" in content_type
                    )
                    _LOGGER.debug(
                        "MCP Server content type: %s, is SSE: %s", content_type, is_sse
                    )
                    return is_sse
                elif response.status == 401:
                    _LOGGER.error(
                        "MCP Server authentication failed - check access token. Token length: %d",
                        len(self.access_token),
                    )
                    # For debugging, let's try without auth to see if the endpoint exists
                    async with session.get(
                        self.mcp_server_url,
                        timeout=aiohttp.ClientTimeout(total=5),
                    ) as no_auth_response:
                        _LOGGER.debug(
                            "MCP Server without auth status: %s",
                            no_auth_response.status,
                        )
                    return False
                elif response.status == 404:
                    _LOGGER.error(
                        "MCP Server endpoint not found at %s - check if MCP Server integration is installed",
                        self.mcp_server_url,
                    )
                    return False
                else:
                    _LOGGER.error(
                        "MCP Server test failed with status %s", response.status
                    )
                    return False

        except aiohttp.ClientConnectorError as exc:
            _LOGGER.error(
                "Cannot connect to MCP Server at %s: %s", self.mcp_server_url, exc
            )
            return False
        except asyncio.TimeoutError:
            _LOGGER.error("MCP Server connection timed out")
            return False
        except Exception as exc:
            _LOGGER.error("MCP Server connection test failed: %s", exc)
            return False
