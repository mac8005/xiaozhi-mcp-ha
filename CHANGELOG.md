# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Initial release preparation

## [1.0.0] - 2025-01-09

### Added

- Initial release of Xiaozhi MCP Home Assistant integration
- WebSocket connection to Xiaozhi MCP endpoint
- MCP protocol implementation with tool support
- Configuration flow for easy setup
- Support for entity state retrieval
- Support for service calls
- Support for entity listing
- Support for area and device information
- Status monitoring sensors
- Connection control switches
- Automatic reconnection with exponential backoff
- Debug logging capabilities
- Comprehensive error handling
- HACS compatibility
- Complete documentation and examples

### Features

- **MCP Tools**:

  - `get_state`: Get current state of any Home Assistant entity
  - `call_service`: Call any Home Assistant service
  - `list_entities`: List all entities with optional domain filtering
  - `get_areas`: Get all areas in Home Assistant
  - `get_devices`: Get all devices with optional area filtering

- **Sensors**:

  - Connection status sensor
  - Last seen timestamp sensor
  - Reconnection count sensor
  - Message count sensor
  - Error count sensor

- **Switches**:

  - Connection control switch
  - Debug logging toggle switch

- **Services**:
  - `xiaozhi_mcp.reconnect`: Manually reconnect to endpoint
  - `xiaozhi_mcp.send_message`: Send message to Xiaozhi

### Technical Details

- Compatible with Home Assistant 2024.1.0+
- Uses WebSocket for real-time communication
- Implements MCP protocol version 1.0.0
- Supports long-lived access tokens for secure authentication
- Includes comprehensive error handling and logging
- Automatic reconnection with exponential backoff
- Thread-safe coordinator pattern for data management

### Documentation

- Complete README with installation instructions
- Detailed installation guide
- Usage examples and automation samples
- Contributing guidelines
- MIT license

[Unreleased]: https://github.com/mac8005/ha-hacs-xiaozhi/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/mac8005/ha-hacs-xiaozhi/releases/tag/v1.0.0
