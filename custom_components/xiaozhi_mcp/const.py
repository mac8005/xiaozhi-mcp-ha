"""Constants for the Xiaozhi MCP integration."""
from typing import Final

# Integration domain
DOMAIN: Final = "xiaozhi_mcp"

# Configuration keys
CONF_XIAOZHI_ENDPOINT: Final = "xiaozhi_endpoint"
CONF_ACCESS_TOKEN: Final = "access_token"
CONF_SCAN_INTERVAL: Final = "scan_interval"
CONF_ENABLE_LOGGING: Final = "enable_logging"

# Default values
DEFAULT_SCAN_INTERVAL: Final = 30
DEFAULT_NAME: Final = "Xiaozhi MCP"
DEFAULT_ENABLE_LOGGING: Final = False

# Connection settings
INITIAL_BACKOFF: Final = 1  # Initial wait time in seconds
MAX_BACKOFF: Final = 60  # Maximum wait time in seconds
MAX_RECONNECT_ATTEMPTS: Final = 100

# Error codes
ERROR_CODES: Final = {
    "CONNECTION_FAILED": "connection_failed",
    "AUTHENTICATION_FAILED": "authentication_failed",
    "INVALID_ENDPOINT": "invalid_endpoint",
    "TIMEOUT": "timeout",
    "UNKNOWN_ERROR": "unknown_error",
}

# Service names
SERVICE_RECONNECT: Final = "reconnect"
SERVICE_SEND_MESSAGE: Final = "send_message"

# Attributes
ATTR_CONNECTED: Final = "connected"
ATTR_LAST_SEEN: Final = "last_seen"
ATTR_RECONNECT_COUNT: Final = "reconnect_count"
ATTR_MESSAGE_COUNT: Final = "message_count"
ATTR_ERROR_COUNT: Final = "error_count"
