"""Validation shared by configuration and both bridge transports."""

import asyncio
import ipaddress
import json
import logging
from urllib.parse import unquote, urljoin, urlsplit

from homeassistant.util.ssl import get_default_context

# Protocol debug logs include handshake URLs and household payloads.
WEBSOCKET_LOGGER = logging.Logger("xiaozhi_mcp.transport", level=logging.CRITICAL + 1)

MAX_MESSAGE_BYTES = 1024 * 1024


def validate_url(value: str, *, websocket: bool = False) -> str:
    """Require TLS outside loopback; never accept credentials in URL authority."""
    try:
        parsed = urlsplit(value)
        schemes = ("ws", "wss") if websocket else ("http", "https")
        if (
            parsed.scheme not in schemes
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.fragment
            or "\\" in value
            or any(ord(c) <= 32 or ord(c) == 127 for c in value)
        ):
            raise ValueError
        _ = parsed.port
        host = parsed.hostname
        try:
            loopback = ipaddress.ip_address(host).is_loopback
        except ValueError:
            loopback = host.lower() == "localhost"
        if parsed.scheme in ("http", "ws") and not loopback:
            raise ValueError
    except (ValueError, TypeError):
        raise ValueError(
            "Use a valid TLS URL (plaintext is allowed only on loopback)"
        ) from None
    return value


def resolve_endpoint(base: str, endpoint: str) -> str:
    """Confine server-supplied POST destinations to the configured MCP origin/path."""
    validate_url(base)
    if not endpoint or "\\" in endpoint or any(ord(c) <= 32 for c in endpoint):
        raise ValueError("Invalid MCP endpoint")
    url = urljoin(base, endpoint)
    validate_url(url)
    source, target = urlsplit(base), urlsplit(url)

    def origin(parts):
        return (
            parts.scheme,
            parts.hostname,
            parts.port or (443 if parts.scheme == "https" else 80),
        )

    path = unquote(target.path)
    if (
        origin(source) != origin(target)
        or not path.startswith("/mcp_server/")
        or any(part in (".", "..") for part in path.split("/"))
        or "\\" in path
        or "%" in path
    ):
        raise ValueError("MCP endpoint must remain within the configured MCP server")
    return url


def validate_message(message: str | bytes) -> dict:
    """Accept bounded JSON-RPC objects, never arbitrary REST payloads."""
    if (
        len(message.encode() if isinstance(message, str) else message)
        > MAX_MESSAGE_BYTES
    ):
        raise ValueError("MCP message too large")
    try:
        data = json.loads(message)
    except (ValueError, UnicodeError):
        raise ValueError("Invalid JSON-RPC message") from None
    if not isinstance(data, dict) or data.get("jsonrpc") != "2.0":
        raise ValueError("Expected a JSON-RPC 2.0 object")
    if not any(key in data for key in ("method", "result", "error")):
        raise ValueError("Invalid JSON-RPC message")
    return data


async def websocket_ssl_options(endpoint: str) -> dict:
    """Load CA certificates off the event loop, retaining hostname verification."""
    if urlsplit(endpoint).scheme == "wss":
        return {"ssl": await asyncio.to_thread(get_default_context)}
    return {}
