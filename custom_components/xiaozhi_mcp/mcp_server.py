"""MCP Server implementation for Xiaozhi integration."""
from __future__ import annotations

import json
import logging
from typing import Any

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import area_registry, device_registry, entity_registry

from .const import (
    MCP_PROTOCOL_VERSION,
    MCP_IMPLEMENTATION,
    MCP_TOOLS,
    ENTITY_TYPES,
)

_LOGGER = logging.getLogger(__name__)


class XiaozhiMCPServer:
    """MCP Server for handling Xiaozhi requests."""

    def __init__(self, hass: HomeAssistant, access_token: str) -> None:
        """Initialize the MCP server."""
        self.hass = hass
        self.access_token = access_token
        self.session = async_get_clientsession(hass)
        
        # Setup request handlers
        self._handlers = {
            "initialize": self._handle_initialize,
            "tools/list": self._handle_tools_list,
            "tools/call": self._handle_tools_call,
            "ping": self._handle_ping,
        }

    async def handle_message(self, message: dict[str, Any]) -> dict[str, Any] | None:
        """Handle an incoming MCP message."""
        try:
            method = message.get("method")
            message_id = message.get("id")
            params = message.get("params", {})
            
            if method in self._handlers:
                result = await self._handlers[method](params)
                
                if message_id:
                    return {
                        "jsonrpc": "2.0",
                        "id": message_id,
                        "result": result,
                    }
            else:
                _LOGGER.warning("Unknown method: %s", method)
                if message_id:
                    return {
                        "jsonrpc": "2.0",
                        "id": message_id,
                        "error": {
                            "code": -32601,
                            "message": "Method not found",
                        },
                    }
                    
        except Exception as err:
            _LOGGER.error("Error handling message: %s", err)
            if message.get("id"):
                return {
                    "jsonrpc": "2.0",
                    "id": message.get("id"),
                    "error": {
                        "code": -32603,
                        "message": f"Internal error: {err}",
                    },
                }
        
        return None

    async def _handle_initialize(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle initialize request."""
        return {
            "protocolVersion": MCP_PROTOCOL_VERSION,
            "serverInfo": {
                "name": "Xiaozhi Home Assistant MCP Server",
                "version": "1.0.0",
                "implementation": MCP_IMPLEMENTATION,
            },
            "capabilities": {
                "tools": True,
                "resources": False,
                "prompts": False,
                "sampling": False,
            },
        }

    async def _handle_tools_list(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle tools list request."""
        return {
            "tools": list(MCP_TOOLS.values())
        }

    async def _handle_tools_call(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle tools call request."""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        if tool_name == "get_state":
            return await self._get_state(arguments)
        elif tool_name == "call_service":
            return await self._call_service(arguments)
        elif tool_name == "list_entities":
            return await self._list_entities(arguments)
        elif tool_name == "get_areas":
            return await self._get_areas(arguments)
        elif tool_name == "get_devices":
            return await self._get_devices(arguments)
        else:
            raise ValueError(f"Unknown tool: {tool_name}")

    async def _handle_ping(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle ping request."""
        return {"pong": True}

    async def _get_state(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Get state of an entity."""
        entity_id = arguments.get("entity_id")
        if not entity_id:
            raise ValueError("entity_id is required")
        
        state = self.hass.states.get(entity_id)
        if not state:
            return {
                "success": False,
                "error": f"Entity {entity_id} not found",
            }
        
        return {
            "success": True,
            "entity_id": entity_id,
            "state": state.state,
            "attributes": dict(state.attributes),
            "last_changed": state.last_changed.isoformat(),
            "last_updated": state.last_updated.isoformat(),
        }

    async def _call_service(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Call a Home Assistant service."""
        domain = arguments.get("domain")
        service = arguments.get("service")
        service_data = arguments.get("service_data", {})
        
        if not domain or not service:
            raise ValueError("domain and service are required")
        
        try:
            await self.hass.services.async_call(
                domain, service, service_data, blocking=True
            )
            return {
                "success": True,
                "message": f"Service {domain}.{service} called successfully",
            }
        except Exception as err:
            return {
                "success": False,
                "error": str(err),
            }

    async def _list_entities(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """List entities in Home Assistant."""
        domain_filter = arguments.get("domain")
        
        entities = []
        for state in self.hass.states.async_all():
            if domain_filter and not state.entity_id.startswith(f"{domain_filter}."):
                continue
            
            entities.append({
                "entity_id": state.entity_id,
                "name": state.attributes.get("friendly_name", state.entity_id),
                "state": state.state,
                "domain": state.domain,
                "device_class": state.attributes.get("device_class"),
                "unit_of_measurement": state.attributes.get("unit_of_measurement"),
            })
        
        return {
            "success": True,
            "entities": entities,
            "count": len(entities),
        }

    async def _get_areas(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Get areas in Home Assistant."""
        area_reg = area_registry.async_get(self.hass)
        
        areas = []
        for area in area_reg.areas.values():
            areas.append({
                "area_id": area.id,
                "name": area.name,
                "aliases": area.aliases,
                "picture": area.picture,
            })
        
        return {
            "success": True,
            "areas": areas,
            "count": len(areas),
        }

    async def _get_devices(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Get devices in Home Assistant."""
        area_id = arguments.get("area_id")
        device_reg = device_registry.async_get(self.hass)
        
        devices = []
        for device in device_reg.devices.values():
            if area_id and device.area_id != area_id:
                continue
            
            devices.append({
                "device_id": device.id,
                "name": device.name or device.name_by_user,
                "manufacturer": device.manufacturer,
                "model": device.model,
                "area_id": device.area_id,
                "sw_version": device.sw_version,
                "identifiers": list(device.identifiers),
            })
        
        return {
            "success": True,
            "devices": devices,
            "count": len(devices),
        }
