"""Config flow for Xiaozhi MCP integration."""

from __future__ import annotations

import asyncio
import logging
import ssl
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_ACCESS_TOKEN,
    CONF_ENABLE_LOGGING,
    CONF_SCAN_INTERVAL,
    CONF_XIAOZHI_ENDPOINT,
    DEFAULT_ENABLE_LOGGING,
    DEFAULT_NAME,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    ERROR_CODES,
)

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
        vol.Required(CONF_XIAOZHI_ENDPOINT): str,
        vol.Required(CONF_ACCESS_TOKEN): str,
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): int,
        vol.Optional(CONF_ENABLE_LOGGING, default=DEFAULT_ENABLE_LOGGING): bool,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    xiaozhi_endpoint = data[CONF_XIAOZHI_ENDPOINT]
    access_token = data[CONF_ACCESS_TOKEN]

    # Validate Xiaozhi endpoint
    if not xiaozhi_endpoint.startswith(("ws://", "wss://")):
        raise InvalidEndpoint("Xiaozhi endpoint must start with ws:// or wss://")

    # Validate access token
    if not access_token or len(access_token) < 10:
        raise AuthenticationFailed("Access token must be at least 10 characters long")

    # Test Xiaozhi connection
    try:
        import websockets

        # Create SSL context properly to avoid blocking calls
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        connect_kwargs = {"timeout": 10}
        if xiaozhi_endpoint.startswith("wss://"):
            connect_kwargs["ssl"] = ssl_context

        async with websockets.connect(xiaozhi_endpoint, **connect_kwargs) as websocket:
            # Send a simple ping to test connection
            await websocket.send('{"jsonrpc": "2.0", "method": "ping", "id": 1}')
            response = await asyncio.wait_for(websocket.recv(), timeout=5)
            _LOGGER.debug("Xiaozhi connection test response: %s", response)
    except Exception as err:
        _LOGGER.error("Failed to connect to Xiaozhi endpoint: %s", err)
        raise ConnectionFailed(f"Cannot connect to Xiaozhi endpoint: {err}")

    # Test Home Assistant MCP Server connection
    try:
        from .mcp_client import XiaozhiMCPClient

        mcp_client = XiaozhiMCPClient(hass, access_token)
        mcp_connected = await mcp_client.test_connection()

        if not mcp_connected:
            raise ConnectionFailed(
                "Cannot connect to Home Assistant MCP Server. Please ensure the MCP Server integration is installed and running."
            )

        # Return info that you want to store in the config entry
        return {
            "title": data[CONF_NAME],
            "xiaozhi_endpoint": xiaozhi_endpoint,
            "access_token": access_token,
        }
    except Exception as err:
        _LOGGER.error("Home Assistant MCP Server connection failed: %s", err)
        raise ConnectionFailed(f"Cannot connect to Home Assistant MCP Server: {err}")


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Xiaozhi MCP."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=DATA_SCHEMA)

        errors = {}

        try:
            info = await validate_input(self.hass, user_input)
        except ConnectionFailed:
            errors["base"] = ERROR_CODES["CONNECTION_FAILED"]
        except AuthenticationFailed:
            errors["base"] = ERROR_CODES["AUTHENTICATION_FAILED"]
        except InvalidEndpoint:
            errors["base"] = ERROR_CODES["INVALID_ENDPOINT"]
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = ERROR_CODES["UNKNOWN_ERROR"]
        else:
            # Check if already configured
            await self.async_set_unique_id(user_input[CONF_XIAOZHI_ENDPOINT])
            self._abort_if_unique_id_configured()

            return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Xiaozhi MCP."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Handle options flow."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        data_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=self.config_entry.options.get(
                        CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                    ),
                ): int,
                vol.Optional(
                    CONF_ENABLE_LOGGING,
                    default=self.config_entry.options.get(
                        CONF_ENABLE_LOGGING, DEFAULT_ENABLE_LOGGING
                    ),
                ): bool,
            }
        )

        return self.async_show_form(step_id="init", data_schema=data_schema)


class ConnectionFailed(Exception):
    """Error to indicate we cannot connect."""


class AuthenticationFailed(Exception):
    """Error to indicate authentication failed."""


class InvalidEndpoint(Exception):
    """Error to indicate invalid endpoint."""
