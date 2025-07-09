# Xiaozhi MCP Integration

[![GitHub Release][releases-shield]][releases]
[![HACS][hacs-shield]][hacs]
[![GitHub Activity][commits-shield]][commits]

**A Home Assistant Custom Integration (HACS) that connects Xiaozhi ESP32 AI chatbot to Home Assistant via MCP (Model Context Protocol).**

## ✨ Features

- 🤖 **AI-Powered Control**: Natural language control of Home Assistant through Xiaozhi ESP32 AI chatbot
- 🔌 **MCP Bridge**: Full Model Context Protocol support for seamless AI-home integration
- 🌐 **Cloud Integration**: WebSocket connection to Xiaozhi cloud service
- 🏠 **Local Processing**: SSE proxy to local Home Assistant MCP Server
- 🔒 **Secure**: Uses Home Assistant long-lived access tokens
- 🔄 **Reliable**: Automatic reconnection with exponential backoff
- 📊 **Monitoring**: Real-time status monitoring and comprehensive logging
- 🛠️ **Easy Setup**: Simple configuration through Home Assistant UI

## 🚀 Quick Start

### Prerequisites

**⚠️ IMPORTANT**: You must install the **Home Assistant MCP Server** integration first:

1. Go to `Settings` → `Devices & Services` → `Add Integration`
2. Search for "Model Context Protocol Server" (or "MCP Server")
3. Install and configure the MCP Server integration
4. Restart Home Assistant

### Installation

1. **Install via HACS** (recommended)
2. **Configure Long-lived Access Token**:
   - Go to your Profile → Long-lived access tokens
   - Create a new token named "Xiaozhi MCP"
   - Copy the token (save it securely!)
3. **Get Xiaozhi Endpoint**:
   - Visit [xiaozhi.me](https://xiaozhi.me/) and create an account
   - Go to MCP section and copy your endpoint URL
4. **Add Integration**:
   - Go to `Settings` → `Devices & Services` → `Add Integration`
   - Search for "Xiaozhi MCP"
   - Enter your configuration

## 🏗️ Architecture

```text
[Xiaozhi ESP32] ←→ [Xiaozhi Cloud] ←→ [This Integration] ←→ [HA MCP Server] ←→ [Home Assistant]
                                         (MCP Proxy)      (SSE: /mcp_server/sse)
```

This integration acts as a **secure proxy** between Xiaozhi cloud and your local Home Assistant MCP Server.

## 🎯 Usage Examples

Once configured, control your home with natural language:

- **Lights**: "Turn on the living room lights"
- **Climate**: "Set the thermostat to 72 degrees"
- **Sensors**: "What's the temperature in the bedroom?"
- **Automations**: "Activate movie mode"
- **Status**: "Is the front door locked?"

## 📋 Requirements

- Home Assistant 2024.1.0 or later
- **Home Assistant MCP Server integration** (must be installed first)
- Xiaozhi ESP32 device or compatible hardware
- Active internet connection
- Long-lived access token

## 🔧 Configuration

| Option           | Description           | Required | Default |
| ---------------- | --------------------- | -------- | ------- |
| Name             | Friendly name         | Yes      | -       |
| Xiaozhi Endpoint | MCP endpoint URL      | Yes      | -       |
| Access Token     | Long-lived token      | Yes      | -       |
| Scan Interval    | Status check interval | No       | 30s     |
| Enable Logging   | Debug logging         | No       | False   |

## 🆘 Support

- 🐛 [Report Issues](https://github.com/mac8005/xiaozhi-mcp-hacs/issues)
- 💬 [Discussions](https://github.com/mac8005/xiaozhi-mcp-hacs/discussions)
- 📖 [Documentation](https://github.com/mac8005/xiaozhi-mcp-hacs/blob/main/README.md)
- 🏠 [Home Assistant Community](https://community.home-assistant.io/)

## 🔗 Related Projects

- [Xiaozhi ESP32](https://github.com/78/xiaozhi-esp32) - The original Xiaozhi project
- [Home Assistant MCP Server](https://www.home-assistant.io/integrations/mcp_server/) - Official HA MCP Server

---

**⭐ Star this repository if you find it useful!**

[releases-shield]: https://img.shields.io/github/release/mac8005/xiaozhi-mcp-hacs.svg?style=for-the-badge
[releases]: https://github.com/mac8005/xiaozhi-mcp-hacs/releases
[commits-shield]: https://img.shields.io/github/commit-activity/y/mac8005/xiaozhi-mcp-hacs.svg?style=for-the-badge
[commits]: https://github.com/mac8005/xiaozhi-mcp-hacs/commits/main
[hacs-shield]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[hacs]: https://github.com/hacs/integration
