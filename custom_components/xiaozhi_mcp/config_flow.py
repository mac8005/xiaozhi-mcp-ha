"""Config flow for Xiaozhi MCP integration."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_ACCESS_TOKEN,
    CONF_ENABLE_LOGGING,
    CONF_MCP_SERVER_URL,
    CONF_SCAN_INTERVAL,
    CONF_XIAOZHI_ENDPOINT,
    DEFAULT_ENABLE_LOGGING,
    DEFAULT_MCP_SERVER_URL,
    DEFAULT_NAME,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    ERROR_CODES,
)
from .security import WEBSOCKET_LOGGER, validate_url

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
        vol.Required(CONF_XIAOZHI_ENDPOINT): str,
        vol.Required(CONF_ACCESS_TOKEN): str,
        vol.Optional(CONF_MCP_SERVER_URL, default=DEFAULT_MCP_SERVER_URL): str,
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.All(
            vol.Coerce(int), vol.Range(min=5, max=3600)
        ),
        vol.Optional(CONF_ENABLE_LOGGING, default=DEFAULT_ENABLE_LOGGING): bool,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    xiaozhi_endpoint = data[CONF_XIAOZHI_ENDPOINT]
    access_token = data[CONF_ACCESS_TOKEN]
    mcp_server_url = data.get(CONF_MCP_SERVER_URL, DEFAULT_MCP_SERVER_URL)

    try:
        validate_url(xiaozhi_endpoint, websocket=True)
        validate_url(mcp_server_url)
    except ValueError as err:
        raise InvalidEndpoint(str(err)) from None

    # Validate access token
    if not access_token or len(access_token) < 10:
        raise AuthenticationFailed("Access token must be at least 10 characters long")

    # Test Xiaozhi connection
    try:
        import websockets

        connect_kwargs = {
            "close_timeout": 10,
            "open_timeout": 20,
            "logger": WEBSOCKET_LOGGER,
        }

        async with websockets.connect(xiaozhi_endpoint, **connect_kwargs) as websocket:
            # Send a simple ping to test connection
            await websocket.send('{"jsonrpc": "2.0", "method": "ping", "id": 1}')
            await asyncio.wait_for(websocket.recv(), timeout=5)
    except Exception as err:
        _LOGGER.error("Failed to connect to Xiaozhi endpoint (%s)", type(err).__name__)
        raise ConnectionFailed("Cannot connect to Xiaozhi endpoint") from None

    # Test Home Assistant MCP Server connection
    try:
        from .mcp_client import XiaozhiMCPClient

        mcp_client = XiaozhiMCPClient(hass, access_token, mcp_server_url)
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
        _LOGGER.error("MCP Server connection failed (%s)", type(err).__name__)
        raise ConnectionFailed("Cannot connect to Home Assistant MCP Server") from None


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
        except Exception as err:
            _LOGGER.error("Configuration failed (%s)", type(err).__name__)
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
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OptionsFlowHandler()


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Xiaozhi MCP."""

    async def async_step_init(self, user_input=None):
        """Handle options flow."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        data_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=self.config_entry.options.get(
                        CONF_SCAN_INTERVAL,
                        self.config_entry.data.get(
                            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                        ),
                    ),
                ): vol.All(vol.Coerce(int), vol.Range(min=5, max=3600)),
                vol.Optional(
                    CONF_ENABLE_LOGGING,
                    default=self.config_entry.options.get(
                        CONF_ENABLE_LOGGING,
                        self.config_entry.data.get(
                            CONF_ENABLE_LOGGING, DEFAULT_ENABLE_LOGGING
                        ),
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
