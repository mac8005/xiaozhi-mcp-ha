# Quick Fix Guide: Device Only Controls Volume/Screen

If your Xiaozhi device responds but only controls volume and screen instead of your Home Assistant devices, follow these steps:

## 1. Check Entity Exposure Status
Look for the **"Entity Exposure Status"** sensor in your Xiaozhi MCP integration. If it shows "No Entities Exposed", continue to step 2.

## 2. Configure MCP Server Entity Exposure
1. Go to **Settings** → **Devices & Services**
2. Find **"Model Context Protocol Server"** and click **Configure**
3. Enable the entities you want to control (lights, switches, climate, etc.)
4. Click **Submit**

## 3. Restart and Test
1. Restart Home Assistant
2. Use the service **"Xiaozhi MCP: Check Entity Exposure"** to verify
3. Check the Entity Exposure Status sensor again - it should show "Exposed (X entities)"
4. Test voice commands like "turn on the living room light"

## 4. If Still Not Working
- Check Home Assistant logs for connection errors
- Verify your access token is valid
- Ensure the MCP Server integration is running
- Try the reconnect service: **"Xiaozhi MCP: Reconnect"**

The issue is almost always that entities aren't exposed to the MCP server, which is required for the Xiaozhi device to know about them.