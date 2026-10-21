"""Config flow for Xiaozhi MCP integration."""

from __future__ import annotations

import asyncio
import logging
import ssl
from typing import Any
from urllib.parse import parse_qs, urlsplit

import aiohttp
import voluptuous as vol
import websockets
from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from websockets.exceptions import InvalidStatus

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
from .mcp_client import MCPAuthenticationError, XiaozhiMCPClient
from .security import WEBSOCKET_LOGGER, validate_url, websocket_ssl_options

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

    endpoint_token = parse_qs(urlsplit(xiaozhi_endpoint).query).get("token", [""])[0]
    if urlsplit(xiaozhi_endpoint).hostname == "api.xiaozhi.me" and not endpoint_token:
        raise ConnectionFailed("xiaozhi_token_missing", CONF_XIAOZHI_ENDPOINT)
    if not access_token or len(access_token) < 10 or access_token == endpoint_token:
        raise AuthenticationFailed

    try:
        ssl_options = await websocket_ssl_options(xiaozhi_endpoint)
        async with websockets.connect(
            xiaozhi_endpoint,
            close_timeout=10,
            open_timeout=20,
            logger=WEBSOCKET_LOGGER,
            **ssl_options,
        ) as websocket:
            pong = await websocket.ping()
            await asyncio.wait_for(pong, timeout=5)
    except ssl.SSLError:
        raise ConnectionFailed("xiaozhi_tls_failed", CONF_XIAOZHI_ENDPOINT) from None
    except InvalidStatus as err:
        code = (
            "xiaozhi_auth_failed"
            if err.response.status_code in (401, 403)
            else "xiaozhi_connection_failed"
        )
        raise ConnectionFailed(code, CONF_XIAOZHI_ENDPOINT) from None
    except Exception as err:
        _LOGGER.error("Xiaozhi connection test failed (%s)", type(err).__name__)
        raise ConnectionFailed(
            "xiaozhi_connection_failed", CONF_XIAOZHI_ENDPOINT
        ) from None

    try:
        await XiaozhiMCPClient(hass, access_token, mcp_server_url).check_connection()
    except MCPAuthenticationError:
        raise AuthenticationFailed from None
    except (ssl.SSLError, aiohttp.ClientSSLError):
        raise ConnectionFailed("mcp_tls_failed", CONF_MCP_SERVER_URL) from None
    except Exception as err:
        _LOGGER.error(
            "Home Assistant MCP connection test failed (%s)", type(err).__name__
        )
        raise ConnectionFailed("mcp_connection_failed", CONF_MCP_SERVER_URL) from None
    return {"title": data[CONF_NAME]}


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
        except ConnectionFailed as err:
            errors[err.field] = err.code
        except AuthenticationFailed:
            errors[CONF_ACCESS_TOKEN] = ERROR_CODES["AUTHENTICATION_FAILED"]
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
    """A credential-free, field-specific setup failure."""

    def __init__(self, code="xiaozhi_connection_failed", field=CONF_XIAOZHI_ENDPOINT):
        super().__init__(code)
        self.code = code
        self.field = field


class AuthenticationFailed(Exception):
    """Error to indicate authentication failed."""


class InvalidEndpoint(Exception):
    """Error to indicate invalid endpoint."""
