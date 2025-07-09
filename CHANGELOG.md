# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Initial release of Xiaozhi MCP integration
- Support for Xiaozhi ESP32 AI chatbot integration
- MCP (Model Context Protocol) bridge functionality
- WebSocket connection to Xiaozhi cloud service
- SSE (Server-Sent Events) proxy to Home Assistant MCP Server
- Configuration flow for easy setup
- Real-time status monitoring
- Automatic reconnection with exponential backoff
- Sensor and switch platforms
- Service calls for reconnection and message sending
- Comprehensive logging and debugging support

### Technical Features

- Async/await architecture for optimal performance
- Proper error handling and recovery
- Device registry integration
- Home Assistant config entry flow
- HACS compatibility with zip releases
- Comprehensive test coverage

### Requirements

- Home Assistant 2024.1.0 or later
- Home Assistant MCP Server integration (dependency)
- Xiaozhi ESP32 device or compatible hardware
- Active internet connection for MCP communication

## [1.0.0] - 2025-01-XX

### Initial Release

- Initial release
- Basic MCP bridge functionality
- Configuration flow
- Sensor and switch platforms
- Service calls
- Documentation

### Fixed

- Test suite fixes for CI/CD
- Proper async handling
- Configuration validation

### Changed

- Improved error handling
- Better logging
- Enhanced reconnection logic

### Security

- Secure token handling
- Proper authentication flow
- Input validation

---

## Release Notes

### Installation via HACS

1. Add this repository as a custom integration in HACS
2. Install the "Xiaozhi MCP" integration
3. Restart Home Assistant
4. Configure via UI: Settings → Devices & Services → Add Integration

### Manual Installation

1. Download the latest `xiaozhi_mcp.zip` from releases
2. Extract to `config/custom_components/xiaozhi_mcp/`
3. Restart Home Assistant
4. Configure via UI: Settings → Devices & Services → Add Integration

### Support

- 🐛 [Report Issues](https://github.com/mac8005/xiaozhi-mcp-hacs/issues)
- 💬 [Discussions](https://github.com/mac8005/xiaozhi-mcp-hacs/discussions)
- 📖 [Documentation](https://github.com/mac8005/xiaozhi-mcp-hacs/blob/main/README.md)
