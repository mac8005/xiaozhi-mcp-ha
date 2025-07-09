"""Sensor platform for Xiaozhi MCP integration."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    ATTR_CONNECTED,
    ATTR_LAST_SEEN,
    ATTR_RECONNECT_COUNT,
    ATTR_MESSAGE_COUNT,
    ATTR_ERROR_COUNT,
)
from .coordinator import XiaozhiMCPCoordinator

SENSOR_DESCRIPTIONS: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key="status",
        name="Status",
        icon="mdi:robot",
    ),
    SensorEntityDescription(
        key="last_seen",
        name="Last Seen",
        icon="mdi:clock",
    ),
    SensorEntityDescription(
        key="reconnect_count",
        name="Reconnect Count",
        icon="mdi:restart",
    ),
    SensorEntityDescription(
        key="message_count",
        name="Message Count",
        icon="mdi:message",
    ),
    SensorEntityDescription(
        key="error_count",
        name="Error Count",
        icon="mdi:alert",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Xiaozhi MCP sensor platform."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities = []
    for description in SENSOR_DESCRIPTIONS:
        entities.append(XiaozhiMCPSensor(coordinator, description))

    async_add_entities(entities)


class XiaozhiMCPSensor(CoordinatorEntity, SensorEntity):
    """Xiaozhi MCP sensor."""

    def __init__(
        self,
        coordinator: XiaozhiMCPCoordinator,
        description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
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
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        if self.entity_description.key == "status":
            return "Connected" if self.coordinator.connected else "Disconnected"
        elif self.entity_description.key == "last_seen":
            if self.coordinator.last_seen:
                return self.coordinator.last_seen.isoformat()
            return None
        elif self.entity_description.key == "reconnect_count":
            return self.coordinator.reconnect_count
        elif self.entity_description.key == "message_count":
            return self.coordinator.message_count
        elif self.entity_description.key == "error_count":
            return self.coordinator.error_count
        return None

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        if self.entity_description.key == "status":
            return {
                ATTR_CONNECTED: self.coordinator.connected,
                ATTR_LAST_SEEN: (
                    self.coordinator.last_seen.isoformat()
                    if self.coordinator.last_seen
                    else None
                ),
                ATTR_RECONNECT_COUNT: self.coordinator.reconnect_count,
                ATTR_MESSAGE_COUNT: self.coordinator.message_count,
                ATTR_ERROR_COUNT: self.coordinator.error_count,
            }
        return {}
