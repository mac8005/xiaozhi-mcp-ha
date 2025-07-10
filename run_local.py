#!/usr/bin/env python3
"""
Standalone script to run the Xiaozhi MCP integration locally.
This script uses the existing classes without Home Assistant.
"""

import asyncio
import logging
import os
import sys
import aiohttp
import json
import argparse
from typing import Dict, Any
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, MagicMock

# Add the custom_components directory to the path
sys.path.insert(0, str(Path(__file__).parent / "custom_components"))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Set up logging
def setup_logging(debug_mode=False):
    """Set up logging with appropriate level."""
    level = logging.DEBUG if debug_mode else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('xiaozhi_mcp_local.log')
        ]
    )
    
    # Set specific loggers to appropriate levels
    if debug_mode:
        # Enable detailed MCP communication logging
        logging.getLogger('custom_components.xiaozhi_mcp.mcp_client').setLevel(logging.DEBUG)
        logging.getLogger('custom_components.xiaozhi_mcp.coordinator').setLevel(logging.DEBUG)
    
    return logging.getLogger(__name__)

# Initialize logger (will be reconfigured in main)
_LOGGER = logging.getLogger(__name__)

# Mock Home Assistant components
class MockHomeAssistant:
    """Mock Home Assistant instance for standalone operation."""
    
    def __init__(self):
        self.data = {}
        self.config = Mock()
        self.config.api = Mock()
        self.config.api.base_url = "http://localhost:8123"
        self.config_entries = Mock()
        self.services = Mock()
        self.helpers = Mock()
        self.loop = asyncio.get_event_loop()
        
    async def async_add_executor_job(self, func, *args):
        """Mock executor job."""
        return func(*args)

class MockConfigEntry:
    """Mock config entry for standalone operation."""
    
    def __init__(self, data: Dict[str, Any]):
        self.data = data
        self.entry_id = "test_entry_id"
        self.state = Mock()
        self.state.value = "loaded"

class StandaloneXiaozhiMCP:
    """Standalone wrapper for the Xiaozhi MCP integration."""
    
    def __init__(self):
        self.hass = MockHomeAssistant()
        self.coordinator = None
        self.running = False
        self.session = None
        self.response_monitor = ResponseMonitor()
        
    async def setup(self, debug_mode=False):
        """Set up the integration."""
        # Create real aiohttp session
        self.session = aiohttp.ClientSession()
        
        # Get environment variables
        xiaozhi_endpoint = os.getenv("XIAOZHI_ENDPOINT")
        ha_access_token = os.getenv("HA_ACCESS_TOKEN")
        ha_mcp_endpoint = os.getenv("HA_MCP_ENDPOINT")
        
        if not xiaozhi_endpoint:
            raise ValueError("XIAOZHI_ENDPOINT environment variable is required")
        if not ha_access_token:
            raise ValueError("HA_ACCESS_TOKEN environment variable is required")
        if not ha_mcp_endpoint:
            raise ValueError("HA_MCP_ENDPOINT environment variable is required")
        
        _LOGGER.info("🚀 Starting Xiaozhi MCP integration locally")
        _LOGGER.info("Xiaozhi Endpoint: %s", xiaozhi_endpoint[:50] + "..." if len(xiaozhi_endpoint) > 50 else xiaozhi_endpoint)
        _LOGGER.info("HA MCP Endpoint: %s", ha_mcp_endpoint)
        
        # Create config entry
        config_entry = MockConfigEntry({
            "name": "Xiaozhi MCP Local",
            "xiaozhi_endpoint": xiaozhi_endpoint,
            "access_token": ha_access_token,
            "scan_interval": 30,
            "mcp_server_url": ha_mcp_endpoint,
            "enable_logging": True
        })
        
        # Patch the aiohttp session helper to use our real session
        import custom_components.xiaozhi_mcp.mcp_client as mcp_client_module
        mcp_client_module.async_get_clientsession = lambda hass: self.session
        
        # Import and create coordinator
        from custom_components.xiaozhi_mcp.coordinator import XiaozhiMCPCoordinator
        
        self.coordinator = XiaozhiMCPCoordinator(
            self.hass,
            config_entry,
            "Xiaozhi MCP Local",
            xiaozhi_endpoint,
            ha_access_token,
            30,  # scan_interval
            ha_mcp_endpoint,
        )
        
        # Patch the coordinator to use our response monitor
        original_pipe_mcp = self.coordinator._pipe_mcp_to_websocket
        
        async def enhanced_pipe_mcp():
            """Enhanced MCP to WebSocket pipe with response monitoring."""
            try:
                async for message in self.coordinator._mcp_client.receive_from_mcp():
                    # Monitor the response
                    self.response_monitor.log_response(message)
                    
                    if self.coordinator.enable_logging:
                        _LOGGER.debug("MCP → Xiaozhi: %s", message[:200])

                    # Validate message before sending to Xiaozhi
                    try:
                        # Check if it's valid JSON
                        json.loads(message)
                        # Forward message back to Xiaozhi
                        await self.coordinator._websocket.send(message)
                    except json.JSONDecodeError:
                        _LOGGER.warning("Received non-JSON message from MCP, forwarding as-is: %s", message[:100])
                        # Forward anyway, Xiaozhi might handle it
                        await self.coordinator._websocket.send(message)
                    except Exception as err:
                        _LOGGER.error("Failed to forward MCP response to Xiaozhi: %s", err)

            except Exception as err:
                _LOGGER.error("Error in enhanced MCP to WebSocket pipe: %s", err)
                self.coordinator._error_count += 1
                raise
        
        # Replace the pipe method
        self.coordinator._pipe_mcp_to_websocket = enhanced_pipe_mcp
        
        # Set up coordinator
        await self.coordinator.async_setup()
        
        _LOGGER.info("✅ Xiaozhi MCP integration setup complete")
        
    async def run(self):
        """Run the integration."""
        if not self.coordinator:
            await self.setup()
        
        self.running = True
        _LOGGER.info("🔄 Starting main loop...")
        
        try:
            while self.running:
                # Update coordinator data
                await self.coordinator.async_refresh()
                
                # Log current status
                data = self.coordinator.data or {}
                response_stats = self.response_monitor.get_stats()
                _LOGGER.info("Status: Connected=%s, Messages=%s, Responses=%s, Errors=%s, Reconnects=%s",
                           data.get("connected", False),
                           data.get("message_count", 0),
                           response_stats["total_responses"],
                           data.get("error_count", 0),
                           data.get("reconnect_count", 0))
                
                # Wait before next update
                await asyncio.sleep(30)
                
        except KeyboardInterrupt:
            _LOGGER.info("🛑 Received shutdown signal")
        except Exception as err:
            _LOGGER.error("❌ Unexpected error in main loop: %s", err)
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """Shutdown the integration."""
        _LOGGER.info("🔄 Shutting down...")
        self.running = False
        
        if self.coordinator:
            await self.coordinator.async_shutdown()
        
        if self.session:
            await self.session.close()
        
        _LOGGER.info("✅ Shutdown complete")
    
    async def simulate_get_live_context(self):
        """Simulate a GetLiveContext message from Xiaozhi MCP to HA MCP."""
        if not self.coordinator or not self.coordinator._connected:
            _LOGGER.error("❌ Cannot simulate message: not connected")
            return False
        
        _LOGGER.info("🎭 Simulating GetLiveContext message from Xiaozhi MCP...")
        
        # Create a realistic GetLiveContext MCP message
        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "GetLiveContext",
                "arguments": {
                    "entity_id": "sensor.example_sensor",
                    "context": "Current status and recent activity"
                }
            }
        }
        
        try:
            # Send the message through the coordinator's MCP client
            message_json = json.dumps(message)
            _LOGGER.info("📤 Sending message: %s", message_json)
            
            # Use the coordinator's MCP client to send the message
            await self.coordinator._mcp_client.send_to_mcp(message_json)
            
            _LOGGER.info("✅ Successfully sent GetLiveContext simulation message")
            return True
            
        except Exception as err:
            _LOGGER.error("❌ Failed to send simulation message: %s", err)
            return False
    
    async def run_with_simulation(self, simulate_after_seconds: int = 10):
        """Run the integration with optional message simulation."""
        if not self.coordinator:
            await self.setup()
        
        self.running = True
        _LOGGER.info("🔄 Starting main loop with simulation...")
        _LOGGER.info("⏰ Will simulate GetLiveContext message after %d seconds", simulate_after_seconds)
        
        loop_count = 0
        simulation_sent = False
        
        try:
            while self.running:
                # Update coordinator data
                await self.coordinator.async_refresh()
                
                # Log current status
                data = self.coordinator.data or {}
                response_stats = self.response_monitor.get_stats()
                _LOGGER.info("Status: Connected=%s, Messages=%s, Responses=%s, Errors=%s, Reconnects=%s",
                           data.get("connected", False),
                           data.get("message_count", 0),
                           response_stats["total_responses"],
                           data.get("error_count", 0),
                           data.get("reconnect_count", 0))
                
                # Send simulation message after specified time and when connected
                if (not simulation_sent and 
                    loop_count * 30 >= simulate_after_seconds and 
                    data.get("connected", False)):
                    simulation_sent = await self.simulate_get_live_context()
                
                loop_count += 1
                
                # Wait before next update
                await asyncio.sleep(30)
                
        except KeyboardInterrupt:
            _LOGGER.info("🛑 Received shutdown signal")
        except Exception as err:
            _LOGGER.error("❌ Unexpected error in main loop: %s", err)
        finally:
            await self.shutdown()
    
    async def send_custom_message(self, message_dict: Dict[str, Any]):
        """Send a custom message to the MCP server."""
        if not self.coordinator or not self.coordinator._connected:
            _LOGGER.error("❌ Cannot send message: not connected")
            return False
        
        try:
            message_json = json.dumps(message_dict)
            _LOGGER.info("📤 Sending custom message: %s", message_json)
            
            await self.coordinator._mcp_client.send_to_mcp(message_json)
            
            _LOGGER.info("✅ Successfully sent custom message")
            return True
            
        except Exception as err:
            _LOGGER.error("❌ Failed to send custom message: %s", err)
            return False

class ResponseMonitor:
    """Monitor and display MCP responses in a user-friendly way."""
    
    def __init__(self):
        self.response_count = 0
        self.last_responses = []
        self.max_responses = 10
    
    def log_response(self, message):
        """Log a response with enhanced formatting."""
        self.response_count += 1
        
        # Store for recent history first
        response_entry = {
            "count": self.response_count,
            "message": message,
            "timestamp": datetime.now()
        }
        
        # Parse the message for better display
        try:
            parsed = json.loads(message)
            response_type = "Response"
            
            if "result" in parsed:
                response_type = "Result"
            elif "error" in parsed:
                response_type = "Error"
            elif "method" in parsed:
                response_type = f"Method: {parsed['method']}"
            
            response_entry["type"] = response_type
            _LOGGER.info("🔴 MCP %s #%d: %s", response_type, self.response_count, message[:200] + "..." if len(message) > 200 else message)
                
        except json.JSONDecodeError:
            response_entry["type"] = "Non-JSON"
            _LOGGER.info("🔴 MCP Response #%d (non-JSON): %s", self.response_count, message[:200] + "..." if len(message) > 200 else message)
        
        # Add to history
        self.last_responses.append(response_entry)
        
        # Keep only recent responses
        if len(self.last_responses) > self.max_responses:
            self.last_responses.pop(0)
    
    def get_stats(self):
        """Get response statistics."""
        return {
            "total_responses": self.response_count,
            "recent_responses": len(self.last_responses)
        }

async def main():
    """Main entry point."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Run Xiaozhi MCP integration locally')
    parser.add_argument('--simulate', action='store_true', 
                       help='Simulate GetLiveContext message after connection')
    parser.add_argument('--simulate-after', type=int, default=10,
                       help='Seconds to wait before sending simulation message (default: 10)')
    parser.add_argument('--custom-message', type=str,
                       help='Send a custom JSON message (provide JSON string)')
    parser.add_argument('--entity-id', type=str, default='sensor.example_sensor',
                       help='Entity ID for GetLiveContext simulation (default: sensor.example_sensor)')
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug logging to see detailed MCP communication')
    
    args = parser.parse_args()
    
    # Setup logging with appropriate level
    global _LOGGER
    _LOGGER = setup_logging(debug_mode=args.debug or args.simulate)
    
    try:
        # Check if required environment variables are set
        required_vars = ["XIAOZHI_ENDPOINT", "HA_ACCESS_TOKEN", "HA_MCP_ENDPOINT"]
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            _LOGGER.error("❌ Missing required environment variables: %s", ", ".join(missing_vars))
            _LOGGER.error("Please create a .env file with the required variables or set them in your environment")
            return 1
        
        # Create and setup the standalone integration
        app = StandaloneXiaozhiMCP()
        await app.setup(debug_mode=args.debug or args.simulate)
        
        # Handle custom message
        if args.custom_message:
            try:
                custom_msg = json.loads(args.custom_message)
                _LOGGER.info("📝 Sending custom message and exiting...")
                success = await app.send_custom_message(custom_msg)
                await app.shutdown()
                return 0 if success else 1
            except json.JSONDecodeError:
                _LOGGER.error("❌ Invalid JSON in custom message")
                return 1
        
        # Handle simulation mode
        if args.simulate:
            # Update the GetLiveContext message with custom entity ID
            original_method = app.simulate_get_live_context
            
            async def custom_simulate():
                """Custom simulation with user-specified entity ID."""
                if not app.coordinator or not app.coordinator._connected:
                    _LOGGER.error("❌ Cannot simulate message: not connected")
                    return False
                
                _LOGGER.info("🎭 Simulating GetLiveContext message for entity: %s", args.entity_id)
                
                message = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {
                        "name": "GetLiveContext",
                        "arguments": {
                            "entity_id": args.entity_id,
                            "context": "Current status and recent activity"
                        }
                    }
                }
                
                try:
                    message_json = json.dumps(message)
                    _LOGGER.info("📤 Sending message: %s", message_json)
                    
                    await app.coordinator._mcp_client.send_to_mcp(message_json)
                    
                    _LOGGER.info("✅ Successfully sent GetLiveContext simulation message")
                    return True
                    
                except Exception as err:
                    _LOGGER.error("❌ Failed to send simulation message: %s", err)
                    return False
            
            # Replace the simulation method
            app.simulate_get_live_context = custom_simulate
            
            await app.run_with_simulation(args.simulate_after)
        else:
            # Run normally
            await app.run()
        
    except Exception as err:
        _LOGGER.error("❌ Failed to start: %s", err)
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
