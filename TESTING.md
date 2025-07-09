# Test the integration locally

## Prerequisites

- Home Assistant development environment
- Python 3.11+
- Access to Xiaozhi MCP endpoint

## Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/mac8005/xiaozhi-mcp-hacs.git
cd xiaozhi-mcp-hacs

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Home Assistant
pip install homeassistant

# Create config directory
mkdir config
```

## Test Configuration

Create a `config/configuration.yaml`:

```yaml
# configuration.yaml
homeassistant:
  name: Test Home
  latitude: 40.7128
  longitude: -74.0060
  unit_system: metric
  time_zone: America/New_York

# Enable logging
logger:
  default: info
  logs:
    custom_components.xiaozhi_mcp: debug

# Enable frontend
frontend:
config:
```

## Install Integration

```bash
# Copy integration to config
mkdir -p config/custom_components
cp -r custom_components/xiaozhi_mcp config/custom_components/

# Start Home Assistant
cd config
hass -c .
```

## Test with Real Xiaozhi Device

1. Get your Xiaozhi MCP endpoint from xiaozhi.me
2. Create a long-lived access token in Home Assistant
3. Configure the integration through UI
4. Test voice commands with your device

## Unit Testing

```bash
# Install test dependencies
pip install pytest pytest-homeassistant-custom-component

# Run tests
pytest tests/
```

## Manual Testing Checklist

- [ ] Integration loads without errors
- [ ] Configuration flow works
- [ ] Entities appear in Home Assistant
- [ ] WebSocket connection establishes
- [ ] MCP tools respond correctly
- [ ] Voice commands work
- [ ] Reconnection works after disconnect
- [ ] Error handling works properly
- [ ] Services work correctly
- [ ] Switches toggle properly
- [ ] Sensors update values
