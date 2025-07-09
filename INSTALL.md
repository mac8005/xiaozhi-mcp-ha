# Installation and Setup Guide

## Prerequisites

- Home Assistant 2024.1.0 or newer
- HACS (Home Assistant Community Store) installed
- Xiaozhi ESP32 device or compatible hardware
- Active internet connection

## Step 1: Install via HACS

1. Open Home Assistant and navigate to HACS
2. Click on "Integrations"
3. Click the three dots menu in the top right
4. Select "Custom repositories"
5. Add the repository URL: `https://github.com/mac8005/ha-hacs-xiaozhi`
6. Select category: "Integration"
7. Click "Add"
8. Search for "Xiaozhi MCP" and click "Install"
9. Restart Home Assistant

## Step 2: Create Long-Lived Access Token

1. Go to your Home Assistant user profile
2. Navigate to `Settings` → `People` → `Users`
3. Click on your username
4. Scroll down to "Long-lived access tokens"
5. Click "Create Token"
6. Enter a name: "Xiaozhi MCP Integration"
7. Click "OK" and copy the token (save it securely!)

## Step 3: Get Xiaozhi MCP Endpoint

1. Visit [xiaozhi.me](https://xiaozhi.me)
2. Create an account or log in
3. Navigate to the MCP section
4. Copy your personal MCP endpoint URL

## Step 4: Configure Integration

1. In Home Assistant, go to `Settings` → `Devices & Services`
2. Click "Add Integration"
3. Search for "Xiaozhi MCP"
4. Fill in the configuration:
   - **Name**: A friendly name (e.g., "Living Room Xiaozhi")
   - **Xiaozhi MCP Endpoint**: Your endpoint from Step 3
   - **Long-Lived Access Token**: Token from Step 2
   - **Home Assistant URL**: Your HA URL (e.g., `http://homeassistant.local:8123`)
   - **Scan Interval**: How often to check status (default: 30 seconds)
   - **Enable Debug Logging**: Enable for troubleshooting

## Step 5: Verify Setup

1. Check that new entities appear in `Settings` → `Devices & Services`
2. Look for sensors like "Xiaozhi MCP Status" and "Xiaozhi MCP Last Seen"
3. Verify the status sensor shows "Connected"

## Troubleshooting

### Connection Issues

- Verify your internet connection
- Check the Xiaozhi MCP endpoint URL
- Ensure the access token is valid
- Confirm Home Assistant URL is accessible

### Authentication Problems

- Regenerate the long-lived access token
- Check token permissions
- Verify Home Assistant URL format

### Entity Not Appearing

- Restart Home Assistant after installation
- Check integration logs for errors
- Verify HACS installation completed successfully

## Advanced Configuration

### Custom Scan Interval

You can customize how often the integration checks the connection status:

```yaml
# In configuration.yaml (not recommended, use UI instead)
xiaozhi_mcp:
  scan_interval: 60 # Check every 60 seconds
```

### Debug Logging

Enable debug logging to troubleshoot issues:

```yaml
# In configuration.yaml
logger:
  default: info
  logs:
    custom_components.xiaozhi_mcp: debug
```

## Next Steps

Once configured, you can:

1. Use voice commands with your Xiaozhi device
2. Monitor connection status via sensors
3. Create automations based on Xiaozhi events
4. Control Home Assistant entities through natural language

## Support

If you encounter issues:

1. Check the [GitHub Issues](https://github.com/mac8005/ha-hacs-xiaozhi/issues)
2. Review the debug logs
3. Join the discussion in [GitHub Discussions](https://github.com/mac8005/ha-hacs-xiaozhi/discussions)
4. Contact the Xiaozhi community: QQ Group 575180511
