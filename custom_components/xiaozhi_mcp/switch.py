"""Switch platform for Xiaozhi MCP integration."""
from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import XiaozhiMCPCoordinator

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
            return self.coordinator.connected
        elif self.entity_description.key == "debug_logging":
            return self.coordinator.enable_logging
        return False

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        if self.entity_description.key == "connection":
            await self.coordinator.async_reconnect()
        elif self.entity_description.key == "debug_logging":
            self.coordinator.enable_logging = True
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        if self.entity_description.key == "connection":
            await self.coordinator.async_shutdown()
        elif self.entity_description.key == "debug_logging":
            self.coordinator.enable_logging = False
        await self.coordinator.async_request_refresh()

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success
