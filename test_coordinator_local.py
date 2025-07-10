#!/usr/bin/env python3
"""
Local test script for Xiaozhi MCP Coordinator debugging.
This script simulates the coordinator behavior to help identify message routing issues.
"""

import asyncio
import json
import logging
import sys
from datetime import datetime
from typing import Any, Dict
from unittest.mock import Mock, AsyncMock, MagicMock

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('coordinator_test.log')
    ]
)

_LOGGER = logging.getLogger(__name__)

class MockHomeAssistant:
    """Mock Home Assistant for testing."""
    
    def __init__(self):
        self.data = {}
        self.config = Mock()
        self.config.config_dir = "/tmp/test_ha"

class MockConfigEntry:
    """Mock config entry for testing."""
    
    def __init__(self):
        self.data = {
            'name': 'Test Xiaozhi MCP',
            'xiaozhi_endpoint': 'wss://test.xiaozhi.me/ws/test123',
            'access_token': 'test_token_123456789',
            'scan_interval': 30,
            'enable_logging': True,
        }

class MockWebSocket:
    """Mock WebSocket for testing."""
    
    def __init__(self):
        self.messages = []
        self.closed = False
        self.close_code = None
        self.test_messages = [
            '{"id": "msg1", "method": "turn_on", "params": {"entity_id": "light.living_room"}}',
            '{"id": "msg2", "method": "get_state", "params": {"entity_id": "sensor.temperature"}}',
            '{"method": "call_service", "params": {"domain": "switch", "service": "toggle"}}',
            'invalid_json_message',
            '{"id": "msg3", "method": "automation.trigger", "params": {"entity_id": "automation.test"}}'
        ]
        self.message_index = 0
        
    async def send(self, message):
        """Mock send method."""
        self.messages.append(message)
        _LOGGER.debug(f"📤 WebSocket SEND: {message}")
        
    async def close(self):
        """Mock close method."""
        self.closed = True
        _LOGGER.debug("🔌 WebSocket CLOSED")
        
    def __aiter__(self):
        """Make it async iterable."""
        return self
        
    async def __anext__(self):
        """Return next test message."""
        if self.message_index < len(self.test_messages):
            message = self.test_messages[self.message_index]
            self.message_index += 1
            await asyncio.sleep(0.1)  # Simulate delay
            _LOGGER.debug(f"📥 WebSocket RECEIVE: {message}")
            return message
        else:
            # Simulate connection close after all messages
            await asyncio.sleep(1)
            raise StopAsyncIteration

class MockMCPClient:
    """Mock MCP Client for testing."""
    
    def __init__(self, hass, access_token, mcp_server_url):
        self.hass = hass
        self.access_token = access_token
        self.mcp_server_url = mcp_server_url
        self.connected = False
        self.messages_sent = []
        self.messages_received = []
        self._message_endpoints = {}
        self._latest_endpoint = "/mcp_server/messages/default"
        
        # Simulate some endpoints
        self._message_endpoints = {
            "msg1": "/mcp_server/messages/msg1",
            "msg2": "/mcp_server/messages/msg2",
            "msg3": "/mcp_server/messages/msg3"
        }
        
    async def test_connection(self):
        """Mock test connection."""
        _LOGGER.debug("🔍 Testing MCP Server connection...")
        await asyncio.sleep(0.5)  # Simulate network delay
        self.connected = True
        _LOGGER.info("✅ MCP Server connection test passed")
        return True
        
    async def connect_to_mcp(self):
        """Mock connect to MCP."""
        _LOGGER.debug("🔗 Connecting to MCP Server...")
        await asyncio.sleep(0.2)
        self.connected = True
        _LOGGER.info("✅ Connected to MCP Server")
        
    async def disconnect_from_mcp(self):
        """Mock disconnect from MCP."""
        _LOGGER.debug("🔌 Disconnecting from MCP Server...")
        self.connected = False
        _LOGGER.info("❌ Disconnected from MCP Server")
        
    async def send_to_mcp(self, message: str):
        """Mock send to MCP with routing logic."""
        _LOGGER.debug(f"📤 MCP Client send_to_mcp called with: {message}")
        
        # Simulate the actual routing logic
        try:
            msg_data = json.loads(message)
            msg_id = msg_data.get('id')
            
            # Find endpoint
            endpoint = None
            if msg_id and msg_id in self._message_endpoints:
                endpoint = self._message_endpoints[msg_id]
            elif self._latest_endpoint:
                endpoint = self._latest_endpoint
            
            if not endpoint:
                _LOGGER.warning("⚠️ No valid MCP message endpoint available. Using fallback.")
                endpoint = "/mcp_server/messages"
            
            # Build URL
            if endpoint.startswith('/'):
                base_url = self.mcp_server_url.split('/mcp_server/sse')[0]
                url = base_url + endpoint
            else:
                base_url = self.mcp_server_url.replace("/sse", "")
                url = base_url + "/" + endpoint.lstrip('/')
            
            _LOGGER.debug(f"🎯 Routing to endpoint: {url}")
            _LOGGER.debug(f"📝 Message ID: {msg_id}")
            _LOGGER.debug(f"📡 Endpoint: {endpoint}")
            
            # Simulate successful send
            self.messages_sent.append({
                'message': message,
                'endpoint': endpoint,
                'url': url,
                'timestamp': datetime.now().isoformat()
            })
            
            # Simulate response
            response = f'{{"id": "{msg_id}", "result": "success", "timestamp": "{datetime.now().isoformat()}"}}'
            self.messages_received.append(response)
            _LOGGER.debug(f"✅ MCP Server response: {response}")
            
        except json.JSONDecodeError as err:
            _LOGGER.warning(f"⚠️ Failed to parse message JSON: {err}")
            base_url = self.mcp_server_url.split('/mcp_server/sse')[0]
            url = base_url + "/mcp_server/messages"
            _LOGGER.debug(f"🎯 Using fallback URL: {url}")
            
            self.messages_sent.append({
                'message': message,
                'endpoint': '/mcp_server/messages',
                'url': url,
                'timestamp': datetime.now().isoformat(),
                'error': 'json_decode_error'
            })
        except Exception as err:
            _LOGGER.error(f"❌ Error in send_to_mcp: {err}")
            raise
            
    async def receive_from_mcp(self):
        """Mock receive from MCP - async generator."""
        for message in self.messages_received:
            yield message
            await asyncio.sleep(0.1)

class MockCoordinator:
    """Mock coordinator for testing."""
    
    def __init__(self):
        self.hass = MockHomeAssistant()
        self.config_entry = MockConfigEntry()
        self.xiaozhi_endpoint = self.config_entry.data['xiaozhi_endpoint']
        self.access_token = self.config_entry.data['access_token']
        self.mcp_server_url = "http://localhost:8123/mcp_server/sse"
        self.enable_logging = self.config_entry.data['enable_logging']
        
        # Stats
        self._connected = False
        self._message_count = 0
        self._error_count = 0
        self._last_seen = None
        
        # Mock WebSocket and MCP client
        self._websocket = MockWebSocket()
        self._mcp_client = MockMCPClient(self.hass, self.access_token, self.mcp_server_url)
        
    async def test_setup(self):
        """Test the setup process."""
        _LOGGER.info("🚀 Starting coordinator setup test...")
        
        # Test MCP connection
        max_retries = 3
        for attempt in range(max_retries):
            try:
                _LOGGER.debug(f"Testing MCP Server connection (attempt {attempt + 1}/{max_retries})")
                mcp_connected = await self._mcp_client.test_connection()
                if mcp_connected:
                    _LOGGER.info("✅ MCP Server test passed")
                    break
            except Exception as err:
                _LOGGER.error(f"❌ MCP Server test failed: {err}")
                if attempt == max_retries - 1:
                    _LOGGER.warning("⚠️ Continuing without MCP Server")
                    
        _LOGGER.info("✅ Setup test completed")
        
    async def test_connection(self):
        """Test the connection process."""
        _LOGGER.info("🔗 Testing connection process...")
        
        # Connect to MCP
        await self._mcp_client.connect_to_mcp()
        
        # Simulate WebSocket connection
        _LOGGER.info(f"🔗 Connecting to Xiaozhi WebSocket: {self.xiaozhi_endpoint}")
        await asyncio.sleep(0.2)
        self._connected = True
        _LOGGER.info("✅ Connected to Xiaozhi WebSocket")
        
    async def test_message_handling(self):
        """Test bidirectional message handling."""
        _LOGGER.info("📨 Testing message handling...")
        
        # Test WebSocket to MCP pipe
        await self._pipe_websocket_to_mcp()
        
        # Test MCP to WebSocket pipe
        await self._pipe_mcp_to_websocket()
        
    async def _pipe_websocket_to_mcp(self):
        """Test WebSocket to MCP message pipe."""
        _LOGGER.info("📤 Testing WebSocket → MCP pipe...")
        
        try:
            async for message in self._websocket:
                self._message_count += 1
                self._last_seen = datetime.now()
                
                if self.enable_logging:
                    _LOGGER.debug(f"Xiaozhi → MCP: {message}")
                
                # Validate and forward message
                try:
                    json.loads(message)
                    await self._mcp_client.send_to_mcp(message)
                except json.JSONDecodeError:
                    _LOGGER.warning(f"⚠️ Non-JSON message from Xiaozhi: {message[:100]}")
                    await self._mcp_client.send_to_mcp(message)
                except Exception as err:
                    _LOGGER.error(f"❌ Failed to forward message: {err}")
                    self._error_count += 1
                    
        except Exception as err:
            _LOGGER.error(f"❌ Error in WebSocket → MCP pipe: {err}")
            self._error_count += 1
            
    async def _pipe_mcp_to_websocket(self):
        """Test MCP to WebSocket message pipe."""
        _LOGGER.info("📥 Testing MCP → WebSocket pipe...")
        
        try:
            async for message in self._mcp_client.receive_from_mcp():
                if self.enable_logging:
                    _LOGGER.debug(f"MCP → Xiaozhi: {message}")
                
                # Validate and forward message
                try:
                    json.loads(message)
                    await self._websocket.send(message)
                except json.JSONDecodeError:
                    _LOGGER.warning(f"⚠️ Non-JSON message from MCP: {message[:100]}")
                    await self._websocket.send(message)
                except Exception as err:
                    _LOGGER.error(f"❌ Failed to forward MCP response: {err}")
                    self._error_count += 1
                    
        except Exception as err:
            _LOGGER.error(f"❌ Error in MCP → WebSocket pipe: {err}")
            self._error_count += 1
            
    def print_stats(self):
        """Print test statistics."""
        _LOGGER.info("📊 Test Statistics:")
        _LOGGER.info(f"  Connected: {self._connected}")
        _LOGGER.info(f"  Messages processed: {self._message_count}")
        _LOGGER.info(f"  Errors: {self._error_count}")
        _LOGGER.info(f"  Last seen: {self._last_seen}")
        _LOGGER.info(f"  MCP messages sent: {len(self._mcp_client.messages_sent)}")
        _LOGGER.info(f"  MCP messages received: {len(self._mcp_client.messages_received)}")
        _LOGGER.info(f"  WebSocket messages sent: {len(self._websocket.messages)}")
        
        # Print detailed message routing info
        _LOGGER.info("📋 Message Routing Details:")
        for i, msg in enumerate(self._mcp_client.messages_sent, 1):
            _LOGGER.info(f"  Message {i}:")
            _LOGGER.info(f"    Content: {msg['message'][:100]}...")
            _LOGGER.info(f"    Endpoint: {msg['endpoint']}")
            _LOGGER.info(f"    URL: {msg['url']}")
            if 'error' in msg:
                _LOGGER.info(f"    Error: {msg['error']}")

async def main():
    """Main test function."""
    _LOGGER.info("🧪 Starting Xiaozhi MCP Coordinator Local Test")
    _LOGGER.info("=" * 60)
    
    coordinator = MockCoordinator()
    
    try:
        # Test setup
        await coordinator.test_setup()
        
        # Test connection
        await coordinator.test_connection()
        
        # Test message handling
        await coordinator.test_message_handling()
        
        # Print statistics
        coordinator.print_stats()
        
        _LOGGER.info("=" * 60)
        _LOGGER.info("✅ All tests completed successfully!")
        
    except Exception as err:
        _LOGGER.error(f"❌ Test failed with error: {err}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Cleanup
        await coordinator._mcp_client.disconnect_from_mcp()
        await coordinator._websocket.close()

if __name__ == "__main__":
    asyncio.run(main())
