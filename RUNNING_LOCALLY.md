# Running Xiaozhi MCP Integration Locally

This guide explains how to run the Xiaozhi MCP integration locally for development and testing purposes.

## Prerequisites

- Python 3.8 or higher
- pip3 package manager
- Access to the Xiaozhi MCP endpoint and Home Assistant MCP server

## Setup

1. **Install dependencies:**

   ```bash
   ./setup_local.sh
   ```

   Or manually:

   ```bash
   pip3 install -r requirements.txt
   ```

2. **Configure environment variables:**

   The `.env` file contains your configuration. Update it with your actual values:

   ```bash
   XIAOZHI_ENDPOINT="wss://api.xiaozhi.me/mcp/?token=YOUR_TOKEN"
   HA_MCP_ENDPOINT="https://your-ha-instance.com/mcp_server/sse"
   HA_ACCESS_TOKEN="your_ha_access_token"
   ```

## Running the Integration

Start the integration with:

```bash
python3 run_local.py
```

### Simulation Mode

You can test the integration by simulating messages:

```bash
# Simulate GetLiveContext message after 10 seconds
python3 run_local.py --simulate

# Simulate with custom entity ID
python3 run_local.py --simulate --entity-id sensor.my_sensor

# Simulate with custom delay
python3 run_local.py --simulate --simulate-after 30

# Send a custom message and exit
python3 run_local.py --custom-message '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"GetLiveContext","arguments":{"entity_id":"sensor.test","context":"Testing"}}}'
```

The integration will:

- Connect to the Xiaozhi MCP WebSocket endpoint
- Connect to your Home Assistant MCP server
- Bridge messages between the two services
- Provide status updates in the console and log file
- (In simulation mode) Send test messages to verify functionality

## Monitoring

- **Console output:** Real-time status updates
- **Log file:** Detailed logs are written to `xiaozhi_mcp_local.log`
- **Status indicators:**
  - ✅ Successful operations
  - ❌ Errors
  - 🔄 Processing/reconnecting
  - 🛑 Shutdown

### Response Monitoring

The integration now includes enhanced response monitoring to help you see what's happening:

```bash
# Enable debug logging to see all communication details
python3 run_local.py --debug

# Simulation automatically enables debug logging
python3 run_local.py --simulate --debug
```

**Response Indicators:**

- 🔴 **MCP Response**: Shows responses received from the MCP server
- 📤 **Outgoing Message**: Shows messages sent to MCP server
- ✅ **Success**: Operation completed successfully
- ❌ **Error**: Something went wrong

**Status Display:**

- **Connected**: Whether both endpoints are connected
- **Messages**: Number of messages sent to MCP server
- **Responses**: Number of responses received from MCP server
- **Errors**: Number of connection/communication errors
- **Reconnects**: Number of reconnection attempts

## Environment Variables

| Variable           | Description                                 | Required |
| ------------------ | ------------------------------------------- | -------- |
| `XIAOZHI_ENDPOINT` | WebSocket endpoint for Xiaozhi MCP service  | Yes      |
| `HA_MCP_ENDPOINT`  | HTTP endpoint for Home Assistant MCP server | Yes      |
| `HA_ACCESS_TOKEN`  | Long-lived access token for Home Assistant  | Yes      |

## Troubleshooting

### Connection Issues

1. **Xiaozhi WebSocket fails:**

   - Check if the token in `XIAOZHI_ENDPOINT` is valid
   - Verify the endpoint URL is correct
   - Check firewall/proxy settings

2. **Home Assistant MCP Server fails:**
   - Ensure the MCP Server integration is installed and running in HA
   - Verify the `HA_MCP_ENDPOINT` URL is accessible
   - Check if the `HA_ACCESS_TOKEN` has the necessary permissions

### Common Error Messages

- **"Invalid Xiaozhi endpoint format":** Ensure the endpoint starts with `wss://`
- **"Connection refused":** The service is not running or URL is incorrect
- **"Authentication failed":** Check your access token

## Stopping the Integration

Press `Ctrl+C` to gracefully stop the integration.

## Architecture

The local runner uses the same core classes as the Home Assistant integration:

- `XiaozhiMCPCoordinator`: Main coordination logic
- `XiaozhiMCPClient`: Handles MCP server communication
- Mocked Home Assistant components for standalone operation

This ensures the local testing environment behaves identically to the production integration.
