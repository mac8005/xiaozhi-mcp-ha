"""The Xiaozhi MCP integration."""

from __future__ import annotations

import json
import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady, ServiceValidationError
from homeassistant.helpers import device_registry as dr

from .config_schema import CONFIG_SCHEMA as CONFIG_SCHEMA
from .const import (
    CONF_ACCESS_TOKEN,
    CONF_MCP_SERVER_URL,
    CONF_SCAN_INTERVAL,
    CONF_XIAOZHI_ENDPOINT,
    DEFAULT_MCP_SERVER_URL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    SERVICE_RECONNECT,
    SERVICE_SEND_MESSAGE,
)
from .coordinator import XiaozhiMCPCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.SWITCH]


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the Xiaozhi MCP integration."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Xiaozhi MCP from a config entry."""
    name = entry.data[CONF_NAME]
    xiaozhi_endpoint = entry.data[CONF_XIAOZHI_ENDPOINT]
    access_token = entry.data[CONF_ACCESS_TOKEN]
    scan_interval = entry.options.get(
        CONF_SCAN_INTERVAL, entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    )
    mcp_server_url = entry.data.get(CONF_MCP_SERVER_URL, DEFAULT_MCP_SERVER_URL)

    _LOGGER.info("Setting up Xiaozhi MCP: %s", name)

    # Create coordinator
    coordinator = XiaozhiMCPCoordinator(
        hass,
        entry,
        name,
        xiaozhi_endpoint,
        access_token,
        scan_interval,
        mcp_server_url,
    )

    hass.data.setdefault(DOMAIN, {})

    # Store coordinator
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Setup coordinator
    try:
        await coordinator.async_setup()
    except Exception as err:
        await coordinator.async_shutdown()
        hass.data[DOMAIN].pop(entry.entry_id, None)
        _LOGGER.error("Coordinator setup failed (%s)", type(err).__name__)
        raise ConfigEntryNotReady from err

    # Setup platforms
    try:
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    except BaseException:
        await coordinator.async_shutdown()
        hass.data[DOMAIN].pop(entry.entry_id, None)
        raise
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    # Setup services
    await _async_setup_services(hass, coordinator)

    # Setup device registry
    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.entry_id)},
        name=name,
        manufacturer="Xiaozhi",
        model="MCP Bridge",
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.info("Unloading Xiaozhi MCP entry: %s", entry.data[CONF_NAME])

    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        # Cleanup coordinator
        coordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.async_shutdown()

        # Remove services if no more entries
        if not hass.data[DOMAIN]:
            hass.services.async_remove(DOMAIN, SERVICE_RECONNECT)
            hass.services.async_remove(DOMAIN, SERVICE_SEND_MESSAGE)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await hass.config_entries.async_reload(entry.entry_id)


async def _async_setup_services(
    hass: HomeAssistant, coordinator: XiaozhiMCPCoordinator
) -> None:
    """Set up services for the integration."""

    if hass.services.has_service(DOMAIN, SERVICE_RECONNECT):
        return

    def selected(call):
        entries = hass.data[DOMAIN]
        entry_id = call.data.get("entry_id")
        if entry_id:
            if entry_id not in entries:
                raise ServiceValidationError("Unknown Xiaozhi MCP entry")
            return entries[entry_id]
        if len(entries) != 1:
            raise ServiceValidationError(
                "Specify entry_id when multiple bridges are configured"
            )
        return next(iter(entries.values()))

    async def handle_reconnect(call):
        await selected(call).async_reconnect()

    async def handle_send_message(call):
        message = call.data["message"]
        if isinstance(message, str):
            try:
                message = json.loads(message)
            except ValueError:
                raise ServiceValidationError("Message must be JSON") from None
        await selected(call).async_send_message(message)

    schema = {vol.Optional("entry_id"): str}
    hass.services.async_register(
        DOMAIN, SERVICE_RECONNECT, handle_reconnect, schema=vol.Schema(schema)
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SEND_MESSAGE,
        handle_send_message,
        schema=vol.Schema({**schema, vol.Required("message"): vol.Any(str, dict)}),
    )
