"""The Xiaozhi MCP integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr

from .const import (CONF_ACCESS_TOKEN, CONF_SCAN_INTERVAL,
                    CONF_XIAOZHI_ENDPOINT, DEFAULT_SCAN_INTERVAL, DOMAIN,
                    SERVICE_RECONNECT, SERVICE_SEND_MESSAGE)
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
    scan_interval = entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

    _LOGGER.info("Setting up Xiaozhi MCP: %s", name)

    # Create coordinator
    coordinator = XiaozhiMCPCoordinator(
        hass,
        entry,
        name,
        xiaozhi_endpoint,
        access_token,
        scan_interval,
    )

    # Store coordinator
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Setup coordinator
    try:
        await coordinator.async_setup()
    except Exception as err:
        _LOGGER.error("Error setting up Xiaozhi MCP coordinator: %s", err)
        raise ConfigEntryNotReady from err

    # Setup platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

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
        sw_version="1.0.0",
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
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)


async def _async_setup_services(
    hass: HomeAssistant, coordinator: XiaozhiMCPCoordinator
) -> None:
    """Set up services for the integration."""

    async def handle_reconnect(call) -> None:
        """Handle reconnect service call."""
        await coordinator.async_reconnect()

    async def handle_send_message(call) -> None:
        """Handle send message service call."""
        message = call.data.get("message")
        if message:
            await coordinator.async_send_message(message)

    # Register services
    hass.services.async_register(
        DOMAIN,
        SERVICE_RECONNECT,
        handle_reconnect,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SEND_MESSAGE,
        handle_send_message,
    )
