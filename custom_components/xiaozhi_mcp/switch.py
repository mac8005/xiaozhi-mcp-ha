"""Switch platform for Xiaozhi MCP integration."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, SWITCH_CONNECTION_TIMEOUT, SWITCH_MAX_RETRIES
from .coordinator import XiaozhiMCPCoordinator

_LOGGER = logging.getLogger(__name__)

SWITCH_DESCRIPTIONS: tuple[SwitchEntityDescription, ...] = (
    SwitchEntityDescription(
        key="connection",
        name="Connection",
        icon="mdi:connection",
    ),
    SwitchEntityDescription(
        key="debug_logging",
        name="Debug Logging",
        icon="mdi:bug",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Xiaozhi MCP switch platform."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities = []
    for description in SWITCH_DESCRIPTIONS:
        entities.append(XiaozhiMCPSwitch(coordinator, description))

    async_add_entities(entities)


class XiaozhiMCPSwitch(CoordinatorEntity, SwitchEntity):
    """Xiaozhi MCP switch."""

    def __init__(
        self,
        coordinator: XiaozhiMCPCoordinator,
        description: SwitchEntityDescription,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_name = f"{coordinator.name} {description.name}"
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{description.key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.config_entry.entry_id)},
            "name": coordinator.name,
            "manufacturer": "Xiaozhi",
            "model": "MCP Bridge",
            "sw_version": "1.0.0",
        }

    @property
    def is_on(self) -> bool:
        """Return true if switch is on."""
        if self.entity_description.key == "connection":
            # Consider switch "on" if connected OR currently connecting
            # This prevents the switch from immediately flipping back to "off"
            return self.coordinator.connected or self.coordinator.connecting
        elif self.entity_description.key == "debug_logging":
            return self.coordinator.enable_logging
        return False

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        if self.entity_description.key == "connection":
            # User explicitly turned on connection again
            self.coordinator._manual_disconnect = False
            # Implement retry logic to prevent double-toggle requirement
            last_exception = None
            
            for attempt in range(SWITCH_MAX_RETRIES):
                try:
                    _LOGGER.debug("Connection attempt %d/%d", attempt + 1, SWITCH_MAX_RETRIES)
                    
                    # Start reconnection process
                    await self.coordinator.async_reconnect()

                    # Wait for connection to be established with longer timeout
                    success = await self.coordinator.async_wait_for_connection(
                        timeout=SWITCH_CONNECTION_TIMEOUT
                    )
                    
                    if success:
                        _LOGGER.info("Connection established successfully on attempt %d", attempt + 1)
                        break
                    else:
                        last_exception = Exception("Connection attempt did not complete within timeout")
                        _LOGGER.warning(
                            "Connection attempt %d/%d failed: timeout after %d seconds",
                            attempt + 1, SWITCH_MAX_RETRIES, SWITCH_CONNECTION_TIMEOUT
                        )
                        
                        # Don't retry immediately if this was the last attempt
                        if attempt < SWITCH_MAX_RETRIES - 1:
                            # Brief delay before retry to allow cleanup
                            await asyncio.sleep(2)
                            
                except Exception as err:
                    last_exception = err
                    _LOGGER.warning(
                        "Connection attempt %d/%d failed with error: %s", 
                        attempt + 1, SWITCH_MAX_RETRIES, err
                    )
                    
                    # Don't retry immediately if this was the last attempt
                    if attempt < SWITCH_MAX_RETRIES - 1:
                        # Brief delay before retry
                        await asyncio.sleep(2)
            
            # If all attempts failed, log final warning but don't raise exception
            # The switch will show the correct state based on coordinator.connected
            if not self.coordinator.connected and last_exception:
                _LOGGER.warning(
                    "All %d connection attempts failed. Last error: %s", 
                    SWITCH_MAX_RETRIES, last_exception
                )

        elif self.entity_description.key == "debug_logging":
            self.coordinator.enable_logging = True
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        if self.entity_description.key == "connection":
            # Properly disconnect by shutting down the coordinator connection
            # but not the entire coordinator (which would affect other entities)
            await self._disconnect_only()
        elif self.entity_description.key == "debug_logging":
            self.coordinator.enable_logging = False
        await self.coordinator.async_request_refresh()

    async def _disconnect_only(self) -> None:
        """Disconnect the websocket connection without shutting down the entire coordinator."""
        coordinator = self.coordinator

        # Mark manual disconnect so auto-reconnect logic pauses
        coordinator._manual_disconnect = True

        # Cancel any ongoing reconnection attempts
        if coordinator._reconnect_task:
            coordinator._reconnect_task.cancel()
            try:
                await coordinator._reconnect_task
            except asyncio.CancelledError:
                pass

        # Close websocket connection
        if coordinator._websocket:
            await coordinator._websocket.close()
            coordinator._websocket = None

        # Disconnect from MCP
        if coordinator._mcp_client:
            await coordinator._mcp_client.disconnect_from_mcp()

        # Update state
        coordinator._connected = False
        coordinator._connecting = False

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success
