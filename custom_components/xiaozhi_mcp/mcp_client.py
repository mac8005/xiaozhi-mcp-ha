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

    def __init__(self, hass: HomeAssistant, access_token: str, mcp_server_url: str = None) -> None:
        """Initialize the MCP client."""
        self.hass = hass
        self.access_token = access_token
        
        try:
            self.session = async_get_clientsession(hass)
        except Exception as err:
            _LOGGER.warning("Failed to get aiohttp session, will create one later: %s", err)
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
            raise Exception(f"MCP Server connection failed: {self._sse_response.status}")

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
        Send message to MCP Server with robust error handling and fallback mechanisms.
        
        Implements session management and handles 404 errors when sessions expire.
        Falls back to different endpoint strategies when sessions are invalid.
        """
        if not self._sse_response:
            raise Exception("Not connected to MCP Server")

        session = await self._ensure_session()
        base_url = self.mcp_server_url.split('/mcp_server/sse')[0]  # Get protocol://host:port
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        
        # Strategy 1: Try to use the latest session endpoint if available
        success = False
        if self._latest_endpoint:
            url = base_url + self._latest_endpoint
            success = await self._try_send_message(session, url, headers, message, "latest session endpoint")
        
        # Strategy 2: If latest endpoint failed, try generic messages endpoint
        if not success:
            url = base_url + "/mcp_server/messages"
            success = await self._try_send_message(session, url, headers, message, "generic messages endpoint")
        
        # Strategy 3: If both failed, try with different path variations
        if not success:
            # Try the original SSE endpoint but with POST instead of GET
            url = self.mcp_server_url
            success = await self._try_send_message(session, url, headers, message, "SSE endpoint as POST")
        
        # Strategy 4: Last resort - try without session-specific paths
        if not success:
            url = base_url + "/mcp_server"
            success = await self._try_send_message(session, url, headers, message, "base MCP endpoint")
            
        if not success:
            _LOGGER.error("All MCP endpoint strategies failed. Message could not be delivered.")
            _LOGGER.error(f"Failed message was: {message}")
            # Clear stored endpoints since they seem to be invalid
            self._latest_endpoint = None
            self._message_endpoints.clear()

    async def _try_send_message(self, session, url: str, headers: dict, message: str, strategy_name: str) -> bool:
        """Try to send a message to a specific endpoint and return success status."""
        try:
            _LOGGER.debug(f"→ Trying {strategy_name}: {url}")
            _LOGGER.debug(f"→ Message preview: {message[:100]}...")
            
            async with session.post(url, headers=headers, data=message, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    _LOGGER.debug(f"✅ Successfully sent message via {strategy_name}")
                    return True
                elif resp.status == 404:
                    response_text = await resp.text()
                    _LOGGER.debug(f"Session expired for {strategy_name}: {resp.status} - {response_text}")
                    # If this was a session-specific endpoint, clear it
                    if "session ID" in response_text or "Could not find" in response_text:
                        self._latest_endpoint = None
                        self._message_endpoints.clear()
                        _LOGGER.debug("Cleared expired session endpoints")
                    return False
                else:
                    response_text = await resp.text()
                    _LOGGER.debug(f"Failed {strategy_name}: {resp.status} - {response_text}")
                    return False
                    
        except asyncio.TimeoutError:
            _LOGGER.debug(f"Timeout for {strategy_name}")
            return False
        except Exception as err:
            _LOGGER.debug(f"Exception for {strategy_name}: {err}")
            return False

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
                line = line.decode('utf-8').strip()
                if line.startswith('data: '):
                    data = line[6:]  # Remove 'data: ' prefix
                    if data and data != '[DONE]':
                        # Check if this is a message endpoint path
                        if data.startswith('/mcp_server/messages/') or data.startswith('/mcp_server/message/'):
                            # This is a session endpoint - store it
                            self._latest_endpoint = data
                            session_id = data.split('/')[-1]  # Extract session ID from path
                            _LOGGER.debug(f"← Received new session endpoint: {data} (session: {session_id})")
                            # Don't queue endpoint paths as messages
                        elif data.startswith('/mcp_server/'):
                            # This might be another type of MCP endpoint
                            old_endpoint = self._latest_endpoint
                            self._latest_endpoint = data
                            _LOGGER.debug(f"← Updated endpoint from {old_endpoint} to {data}")
                        else:
                            # This is actual message content - queue it
                            try:
                                # Validate that it's proper JSON before queuing
                                parsed = json.loads(data)
                                await self._sse_queue.put(data)
                                _LOGGER.debug(f"← Queued MCP message: {data[:100]}...")
                                
                                # If this is an error response about session not found, clear endpoints
                                if isinstance(parsed, dict) and parsed.get('error'):
                                    error_msg = str(parsed.get('error', {}))
                                    if 'session' in error_msg.lower() or 'not found' in error_msg.lower():
                                        _LOGGER.debug("Received error about session, clearing endpoints")
                                        self._latest_endpoint = None
                                        self._message_endpoints.clear()
                                        
                            except json.JSONDecodeError:
                                # Not JSON, might be a different format or endpoint
                                if data.startswith('/'):
                                    # Looks like a path - treat as endpoint
                                    self._latest_endpoint = data
                                    _LOGGER.debug(f"← Stored MCP endpoint (path): {data}")
                                else:
                                    # Unknown format, queue anyway but log warning
                                    _LOGGER.warning(f"← Unknown SSE data format: {data[:100]}...")
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
                    is_sse = "text/event-stream" in content_type or "text/plain" in content_type
                    _LOGGER.debug("MCP Server content type: %s, is SSE: %s", content_type, is_sse)
                    return is_sse
                elif response.status == 401:
                    _LOGGER.error("MCP Server authentication failed - check access token. Token length: %d", len(self.access_token))
                    # For debugging, let's try without auth to see if the endpoint exists
                    async with session.get(
                        self.mcp_server_url,
                        timeout=aiohttp.ClientTimeout(total=5),
                    ) as no_auth_response:
                        _LOGGER.debug("MCP Server without auth status: %s", no_auth_response.status)
                    return False
                elif response.status == 404:
                    _LOGGER.error("MCP Server endpoint not found at %s - check if MCP Server integration is installed", self.mcp_server_url)
                    return False
                else:
                    _LOGGER.error(
                        "MCP Server test failed with status %s", response.status
                    )
                    return False

        except aiohttp.ClientConnectorError as exc:
            _LOGGER.error("Cannot connect to MCP Server at %s: %s", self.mcp_server_url, exc)
            return False
        except asyncio.TimeoutError:
            _LOGGER.error("MCP Server connection timed out")
            return False
        except Exception as exc:
            _LOGGER.error("MCP Server connection test failed: %s", exc)
            return False

    async def check_entity_exposure(self) -> tuple[bool, list[str]]:
        """
        Check if Home Assistant entities are properly exposed to the MCP server.
        Returns (has_entities, entity_list).
        """
        try:
            session = await self._ensure_session()
            base_url = self.mcp_server_url.split('/mcp_server/sse')[0]
            
            # Try to query available tools/resources from MCP server
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
            }
            
            # Test message to check what capabilities are available
            test_message = {
                "jsonrpc": "2.0",
                "id": "test_entities",
                "method": "tools/list"
            }
            
            # Try the generic messages endpoint first
            url = base_url + "/mcp_server/messages"
            
            try:
                async with session.post(
                    url, 
                    headers=headers, 
                    data=json.dumps(test_message),
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    
                    if response.status == 200:
                        response_data = await response.json()
                        _LOGGER.debug("MCP tools/list response: %s", response_data)
                        
                        # Check if we got a valid tools list
                        if isinstance(response_data, dict):
                            tools = response_data.get('result', {}).get('tools', [])
                            if tools:
                                tool_names = [tool.get('name', 'unknown') for tool in tools]
                                _LOGGER.info("Found %d MCP tools: %s", len(tools), tool_names)
                                return True, tool_names
                            else:
                                _LOGGER.warning("MCP server responded but no tools found. This may indicate entities are not exposed.")
                                return False, []
                        else:
                            _LOGGER.warning("Unexpected MCP response format: %s", response_data)
                            return False, []
                    else:
                        response_text = await response.text()
                        _LOGGER.warning("Failed to check MCP entities: %s - %s", response.status, response_text)
                        return False, []
                        
            except asyncio.TimeoutError:
                _LOGGER.warning("Timeout checking MCP entity exposure")
                return False, []
            except Exception as err:
                _LOGGER.warning("Error checking MCP entity exposure: %s", err)
                return False, []
                
        except Exception as exc:
            _LOGGER.error("Failed to check entity exposure: %s", exc)
            return False, []
