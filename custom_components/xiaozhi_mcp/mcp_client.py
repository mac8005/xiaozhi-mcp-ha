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

    def __init__(self, hass: HomeAssistant, access_token: str) -> None:
        """Initialize the MCP client."""
        self.hass = hass
        self.access_token = access_token
        self.session = async_get_clientsession(hass)

        # MCP Server SSE endpoint (local Home Assistant MCP Server)
        self.mcp_server_url = "http://localhost:8123/mcp_server/sse"
        self._sse_session = None

    async def forward_message(self, message: dict[str, Any]) -> dict[str, Any] | None:
        """Forward a message from Xiaozhi to the local MCP Server via SSE."""
        try:
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
                "Accept": "text/event-stream",
            }

            _LOGGER.debug("Forwarding message to MCP Server: %s", message)

            # For SSE, we need to send the message as JSON in the request body
            # and listen for the SSE response
            async with self.session.post(
                self.mcp_server_url,
                json=message,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                if response.status == 200:
                    # Read the SSE response
                    response_text = await response.text()

                    # Parse SSE data (format: "data: {json}")
                    for line in response_text.split("\n"):
                        if line.startswith("data: "):
                            data_str = line[6:]  # Remove "data: " prefix
                            if data_str.strip():
                                try:
                                    result = json.loads(data_str)
                                    _LOGGER.debug("MCP Server response: %s", result)
                                    return result
                                except json.JSONDecodeError:
                                    _LOGGER.warning(
                                        "Failed to parse SSE data: %s", data_str
                                    )

                    # If no valid data found, return empty response
                    return {"jsonrpc": "2.0", "result": {}, "id": message.get("id")}
                elif response.status == 405:
                    # Method not allowed, try GET with query parameters
                    _LOGGER.debug("POST not allowed, trying GET method")
                    params = {"message": json.dumps(message)}
                    async with self.session.get(
                        self.mcp_server_url,
                        params=params,
                        headers={k: v for k, v in headers.items() if k != "Content-Type"},
                        timeout=aiohttp.ClientTimeout(total=30),
                    ) as get_response:
                        if get_response.status == 200:
                            response_text = await get_response.text()
                            # Parse SSE data (format: "data: {json}")
                            for line in response_text.split("\n"):
                                if line.startswith("data: "):
                                    data_str = line[6:]  # Remove "data: " prefix
                                    if data_str.strip():
                                        try:
                                            result = json.loads(data_str)
                                            _LOGGER.debug("MCP Server response: %s", result)
                                            return result
                                        except json.JSONDecodeError:
                                            _LOGGER.warning(
                                                "Failed to parse SSE data: %s", data_str
                                            )
                            return {"jsonrpc": "2.0", "result": {}, "id": message.get("id")}
                        else:
                            _LOGGER.error("MCP Server GET returned status %s", get_response.status)
                            return {
                                "jsonrpc": "2.0",
                                "error": {
                                    "code": -32603,
                                    "message": f"MCP Server error: {get_response.status}",
                                },
                                "id": message.get("id"),
                            }
                else:
                    _LOGGER.error("MCP Server returned status %s", response.status)
                    return {
                        "jsonrpc": "2.0",
                        "error": {
                            "code": -32603,
                            "message": f"MCP Server error: {response.status}",
                        },
                        "id": message.get("id"),
                    }

        except Exception as exc:
            _LOGGER.error("Error forwarding message to MCP Server: %s", exc)
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32603, "message": f"Internal error: {exc}"},
                "id": message.get("id"),
            }

    async def test_connection(self) -> bool:
        """Test connection to the MCP Server."""
        try:
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Accept": "text/event-stream",
            }

            # Test with a simple GET request to the SSE endpoint
            async with self.session.get(
                self.mcp_server_url,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                # A successful connection should return 200 and SSE content type
                if response.status == 200:
                    content_type = response.headers.get("content-type", "")
                    return "text/event-stream" in content_type
                else:
                    _LOGGER.error(
                        "MCP Server test failed with status %s", response.status
                    )
                    return False

        except Exception as exc:
            _LOGGER.error("MCP Server connection test failed: %s", exc)
            return False
