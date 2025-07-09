"""The Xiaozhi MCP integration."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr

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


async def _wait_for_mcp_server(hass: HomeAssistant) -> None:
    """Wait for MCP Server integration to be available."""
    max_wait = 30  # Maximum wait time in seconds
    check_interval = 1  # Check every second
    
    for attempt in range(max_wait):
        # Check if MCP Server integration is loaded
        if "mcp_server" in hass.data:
            _LOGGER.debug("MCP Server integration is available in hass.data")
            return
        
        # Check if MCP Server config entry exists and is loaded
        mcp_entries = hass.config_entries.async_entries("mcp_server")
        if mcp_entries:
            for entry in mcp_entries:
                if entry.state.value == "loaded":
                    _LOGGER.debug("MCP Server integration is loaded via config entry")
                    return
        
        # Alternative check: try to access the MCP server endpoint directly
        try:
            from homeassistant.helpers.aiohttp_client import async_get_clientsession
            session = async_get_clientsession(hass)
            base_url = str(hass.config.api.base_url).rstrip('/')
            mcp_url = f"{base_url}/mcp_server/sse"
            
            async with session.get(mcp_url, timeout=aiohttp.ClientTimeout(total=2)) as response:
                # 401 means the server is running but needs auth - that's good!
                # 404 means the endpoint doesn't exist - MCP server not available
                if response.status in (200, 401):
                    _LOGGER.debug("MCP Server endpoint is responding (status: %s)", response.status)
                    return
        except Exception as e:
            _LOGGER.debug("MCP Server endpoint check failed: %s", e)
        
        if attempt < max_wait - 1:  # Don't log on the last attempt
            _LOGGER.debug("Waiting for MCP Server integration... (attempt %d/%d)", attempt + 1, max_wait)
        await asyncio.sleep(check_interval)
    
    _LOGGER.warning("MCP Server integration not found after %d seconds", max_wait)


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
    mcp_server_url = entry.data.get(CONF_MCP_SERVER_URL, DEFAULT_MCP_SERVER_URL)

    _LOGGER.info("Setting up Xiaozhi MCP: %s", name)

    # Wait for MCP Server integration to be fully loaded
    await _wait_for_mcp_server(hass)

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
