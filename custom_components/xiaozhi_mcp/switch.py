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

from .const import CONF_ENABLE_LOGGING, DOMAIN, SWITCH_CONNECTION_TIMEOUT, SWITCH_MAX_RETRIES
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
            self.coordinator._manual_disconnect = False
            last_exception = None

            # If HA thinks we're connected but websocket task is gone, force reset
            if self.coordinator.connected and not self.coordinator._message_task:
                _LOGGER.debug("Detected connected state without active message task; forcing reset before reconnect")
                await self._disconnect_only()

            for attempt in range(SWITCH_MAX_RETRIES):
                try:
                    _LOGGER.debug(
                        "Connection attempt %d/%d (connecting=%s, connected=%s)",
                        attempt + 1,
                        SWITCH_MAX_RETRIES,
                        self.coordinator.connecting,
                        self.coordinator.connected,
                    )

                    await self.coordinator.async_reconnect()

                    success = await self.coordinator.async_wait_for_connection(
                        timeout=SWITCH_CONNECTION_TIMEOUT
                    )

                    if success:
                        # Confirm message task alive
                        if not self.coordinator._message_task:
                            _LOGGER.debug("Connection established but message task missing; retrying")
                            raise Exception("Message handling task not running")
                        _LOGGER.info("Connection established successfully on attempt %d", attempt + 1)
                        break
                    else:
                        last_exception = Exception("Connection attempt did not complete within timeout")
                        _LOGGER.warning(
                            "Connection attempt %d/%d failed: timeout after %d seconds (connecting=%s, connected=%s)",
                            attempt + 1,
                            SWITCH_MAX_RETRIES,
                            SWITCH_CONNECTION_TIMEOUT,
                            self.coordinator.connecting,
                            self.coordinator.connected,
                        )
                        if attempt < SWITCH_MAX_RETRIES - 1:
                            await asyncio.sleep(2)

                except Exception as err:
                    last_exception = err
                    _LOGGER.warning(
                        "Connection attempt %d/%d failed with error: %s", attempt + 1, SWITCH_MAX_RETRIES, err
                    )
                    if attempt < SWITCH_MAX_RETRIES - 1:
                        await asyncio.sleep(2)

            if not self.coordinator.connected and last_exception:
                _LOGGER.warning(
                    "All %d connection attempts failed. Last error: %s", SWITCH_MAX_RETRIES, last_exception
                )

        elif self.entity_description.key == "debug_logging":
            # Enable debug logging for this integration
            self.coordinator.enable_logging = True
            self._update_logger_level(True)
            # Persist the state to config entry
            await self._persist_logging_state(True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        if self.entity_description.key == "connection":
            # Properly disconnect by shutting down the coordinator connection
            # but not the entire coordinator (which would affect other entities)
            await self._disconnect_only()
        elif self.entity_description.key == "debug_logging":
            # Disable debug logging for this integration
            self.coordinator.enable_logging = False
            self._update_logger_level(False)
            # Persist the state to config entry
            await self._persist_logging_state(False)
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

    def _update_logger_level(self, debug_enabled: bool) -> None:
        """Update logger levels for the integration."""
        level = logging.DEBUG if debug_enabled else logging.INFO
        
        # Update logger levels for all xiaozhi_mcp loggers
        logging.getLogger("custom_components.xiaozhi_mcp").setLevel(level)
        logging.getLogger("custom_components.xiaozhi_mcp.coordinator").setLevel(level)
        logging.getLogger("custom_components.xiaozhi_mcp.mcp_client").setLevel(level)
        logging.getLogger("custom_components.xiaozhi_mcp.switch").setLevel(level)
        
        _LOGGER.info("Debug logging %s for Xiaozhi MCP integration", 
                    "enabled" if debug_enabled else "disabled")

    async def _persist_logging_state(self, debug_enabled: bool) -> None:
        """Persist the logging state to the config entry."""
        try:
            # Update config entry data
            data = dict(self.coordinator.config_entry.data)
            data[CONF_ENABLE_LOGGING] = debug_enabled
            
            # Update the config entry
            self.hass.config_entries.async_update_entry(
                self.coordinator.config_entry,
                data=data
            )
            
            _LOGGER.debug("Persisted debug logging state: %s", debug_enabled)
        except Exception as err:
            _LOGGER.warning("Failed to persist debug logging state: %s", err)

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success
