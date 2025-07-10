# Xiaozhi MCP Integration for Home Assistant

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)
[![HACS][hacs-shield]][hacs]
[![BuyMeCoffee][buymecoffee-shield]][buymecoffee]

A Home Assistant Custom Integration (HACS) that connects Xiaozhi ESP32 AI chatbot to Home Assistant via MCP (Model Context Protocol).

## Features

- 🤖 Connect Xiaozhi ESP32 devices to Home Assistant
- 🔌 Full MCP (Model Context Protocol) support for AI-powered home automation
- 🏠 Control Home Assistant entities through natural language
- 🔒 Secure authentication with long-lived access tokens
- 🔄 Automatic reconnection with exponential backoff
- 📊 Real-time status monitoring and logging
- 🛠️ Easy configuration through Home Assistant UI
- 🌐 Support for both WebSocket and HTTP endpoints

## What is Xiaozhi?

Xiaozhi is an open-source ESP32-based AI chatbot that uses voice interaction and MCP protocol to control various smart home devices and services. It supports multiple ESP32 platforms and can integrate with various AI models like Qwen and DeepSeek.

<img src="https://ph-files.imgix.net/80909cc8-6bcb-42b9-96eb-4572b4e8b3cf.png?auto=compress&codec=mozjpeg&cs=strip&auto=format&w=969&h=640&fit=max&frame=1&dpr=1" alt="Xiaozhi ESP32 AI Chatbot" width="600">

- **All-in-one hardware:** ESP32-S3 (16 MB flash / 8 MB PSRAM), digital mic, speaker with class-D amp and 1.28–1.85″ colour LCD.
- **Local wake word + cloud intelligence:** an offline wake-word engine runs on the device; after activation audio is sent to Xiaozhi’s servers where ASR, LLM reasoning (Qwen, DeepSeek, Doubao …), and TTS are performed.  
- **Voice-only Home-Assistant control:** this HACS integration connects the device to Home Assistant MCP, letting you toggle lights, scenes and more entirely by voice.  
- **Many shapes, same guts:** boards are sold as square dev-kits, cubes, pucks and the cute **“Astronaut Ball”** shown above – all share the same firmware stack.  
- **Ultra-low cost:** the Astronaut Ball costs **≈ USD 19** – cheaper than most bare ESP32 kits. [AliExpress product page](https://www.aliexpress.com/item/1005008600891141.html)

## Requirements

- Home Assistant 2024.1.0 or later
- HACS (Home Assistant Community Store)
- **Home Assistant MCP Server Integration** (must be installed first)
- Xiaozhi ESP32 device or compatible hardware
- Active internet connection for MCP communication

## Installation

### Prerequisites: Install Home Assistant MCP Server

Before installing this integration, you **must** install the official Home Assistant MCP Server integration:

[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=mcp_server)

1. Go to `Settings` > `Devices & Services` > `Add Integration`
2. Search for "Model Context Protocol Server" (or "MCP Server")
3. Install and configure the MCP Server integration
4. The MCP server will run locally within your Home Assistant instance at `http://localhost:8123/mcp_server/sse`
5. Make sure to configure entity exposure in the MCP Server settings

### HACS Installation (Recommended)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=mac8005&repository=xiaozhi-mcp-hacs&category=integration)

1. Open HACS in Home Assistant
2. Click on "Integrations"
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add this repository URL: `https://github.com/mac8005/xiaozhi-mcp-hacs`
6. Set category to "Integration"
7. Click "Add"
8. Search for "Xiaozhi MCP" and install
9. Restart Home Assistant

### Manual Installation

1. Download the `xiaozhi_mcp` folder from this repository
2. Copy it to `config/custom_components/xiaozhi_mcp/` in your Home Assistant installation
3. Restart Home Assistant

## Configuration

### Step 1: Create Long-Lived Access Token

1. Go to your Home Assistant Profile: `Settings` > `People` > `Users` > Click on your user
2. Scroll down to "Long-lived access tokens"
3. Click "Create Token"
4. Give it a name like "Xiaozhi MCP"
5. Copy the token (you won't see it again!)

### Step 2: Get Xiaozhi MCP Endpoint

1. Visit [xiaozhi.me](https://xiaozhi.me/) and create an account
2. Go to the MCP section in your dashboard
3. Copy your MCP endpoint URL

### Step 3: Configure Integration

[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=xiaozhi_mcp)

1. Go to `Settings` > `Devices & Services` > `Add Integration`
2. Search for "Xiaozhi MCP"
3. Enter your configuration:
   - **Name**: Friendly name for the integration
   - **Xiaozhi MCP Endpoint**: Your xiaozhi.me MCP endpoint URL
   - **Long-Lived Access Token**: Token created in Step 1
   - **Scan Interval**: How often to check connection status (default: 30 seconds)
   - **Enable Logging**: Enable detailed logging for debugging

## How It Works

This integration acts as a **bridge/proxy** between your Xiaozhi ESP32 device and the official Home Assistant MCP Server:

1. **Xiaozhi ESP32** connects to the Xiaozhi cloud service
2. **Xiaozhi cloud** sends MCP requests to this integration via WebSocket
3. **This integration** forwards the MCP requests to the local **Home Assistant MCP Server** via Server-Sent Events (SSE)
4. **Home Assistant MCP Server** (at `http://localhost:8123/mcp_server/sse`) processes the requests and controls your Home Assistant entities
5. **Responses** are sent back through the same chain

```text
[Xiaozhi ESP32] ←→ [Xiaozhi Cloud] ←→ [This Integration] ←→ [HA MCP Server] ←→ [Home Assistant]
                                         (MCP Proxy)      (SSE: /mcp_server/sse)
```

**Key Architecture Points:**

- ✅ **No MCP Server Reimplementation**: This integration does NOT implement its own MCP server
- ✅ **Uses Official MCP Server**: All MCP functionality is provided by the official Home Assistant MCP Server integration
- ✅ **Acts as SSE Proxy**: This integration forwards MCP messages to the official MCP server via Server-Sent Events
- ✅ **Secure Local Communication**: All Home Assistant communication happens locally through the official MCP server
- ✅ **No External URLs Required**: No need to expose your Home Assistant instance to the internet

## Usage

Once configured, your Xiaozhi device can:

- Control lights: "Turn on the living room lights"
- Check sensors: "What's the temperature in the bedroom?"
- Control climate: "Set the thermostat to 72 degrees"
- Run automations: "Activate movie mode"
- Get device status: "Is the front door locked?"

## Configuration Options

| Option             | Description                       | Required | Default |
| ------------------ | --------------------------------- | -------- | ------- |
| `name`             | Friendly name for the integration | Yes      | -       |
| `xiaozhi_endpoint` | Xiaozhi MCP endpoint URL          | Yes      | -       |
| `access_token`     | Long-lived access token           | Yes      | -       |
| `scan_interval`    | Status check interval (seconds)   | No       | 30      |
| `enable_logging`   | Enable detailed logging           | No       | False   |

## Troubleshooting


### Important Notes

- **Critical Dependency**: This integration requires the official Home Assistant MCP Server integration to be installed and running
- **No MCP Server Reimplementation**: This integration does NOT implement its own MCP server - it only acts as a proxy
- **SSE Communication**: Uses Server-Sent Events to communicate with the MCP Server at `http://localhost:8123/mcp_server/sse`
- **Entity Exposure**: Make sure to expose the entities you want to control via the MCP Server settings in Home Assistant
- **Local Communication**: All Home Assistant communication happens locally through the official MCP server
- **No External URLs**: No need to configure external Home Assistant URLs or expose your instance to the internet

### Debug Logging

Enable debug logging by adding to `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.xiaozhi_mcp: debug
```

## Support

- **Issues**: [GitHub Issues](https://github.com/mac8005/xiaozhi-mcp-hacs/issues)
- **Discussions**: [GitHub Discussions](https://github.com/mac8005/xiaozhi-mcp-hacs/discussions)

### ☕ Support Development

If this project helps you, consider supporting its development! Your support helps maintain and improve this integration.

<a href="https://www.buymeacoffee.com/mac8005" target="_blank">
  <img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" style="height: 60px !important;width: 217px !important;" />
</a>

All donations are appreciated and help keep this project active! 🙏

## Contributing

Contributions are welcome! Please read the [Contributing Guide](CONTRIBUTING.md) for details on how to contribute to this project.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Thanks to [78/xiaozhi-esp32](https://github.com/78/xiaozhi-esp32) for the original Xiaozhi project
- Thanks to the Home Assistant community for the excellent platform

## Related Projects

- [Xiaozhi ESP32](https://github.com/78/xiaozhi-esp32) - The original Xiaozhi project
- [MCP Calculator](https://github.com/78/mcp-calculator) - MCP sample implementation
- [Home Assistant MCP Server](https://www.home-assistant.io/integrations/mcp_server) - Official HA MCP Server integration
- [Home Assistant](https://www.home-assistant.io/) - Open source home automation platform

---

[releases-shield]: https://img.shields.io/github/release/mac8005/xiaozhi-mcp-hacs.svg?style=for-the-badge
[releases]: https://github.com/mac8005/xiaozhi-mcp-hacs/releases
[commits-shield]: https://img.shields.io/github/commit-activity/y/mac8005/xiaozhi-mcp-hacs.svg?style=for-the-badge
[commits]: https://github.com/mac8005/xiaozhi-mcp-hacs/commits/main
[license-shield]: https://img.shields.io/github/license/mac8005/xiaozhi-mcp-hacs.svg?style=for-the-badge
[hacs-shield]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[hacs]: https://github.com/hacs/integration
[buymecoffee]: https://www.buymeacoffee.com/mac8005
[buymecoffee-shield]: https://img.shields.io/badge/Buy%20Me%20A%20Coffee-Donate-orange?style=for-the-badge&logo=buy-me-a-coffee&logoColor=white
