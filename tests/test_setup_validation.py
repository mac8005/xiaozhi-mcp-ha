"""Setup diagnostics and transport-only validation."""

import ssl
import threading
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import websockets
from aiohttp import web

from custom_components.xiaozhi_mcp.config_flow import (
    AuthenticationFailed,
    ConnectionFailed,
    validate_input,
)
from custom_components.xiaozhi_mcp.mcp_client import (
    MCPAuthenticationError,
    XiaozhiMCPClient,
)
from custom_components.xiaozhi_mcp.security import websocket_ssl_options


async def test_missing_cloud_token_does_not_connect():
    with patch("websockets.connect") as connect:
        with pytest.raises(ConnectionFailed) as error:
            await validate_input(
                MagicMock(),
                {
                    "name": "test",
                    "xiaozhi_endpoint": "wss://api.xiaozhi.me/mcp/",
                    "access_token": "ha-token-placeholder",
                },
            )
        assert error.value.code == "xiaozhi_token_missing"
        connect.assert_not_called()


async def test_cloud_token_in_ha_field_rejected():
    with pytest.raises(AuthenticationFailed):
        await validate_input(
            MagicMock(),
            {
                "name": "test",
                "xiaozhi_endpoint": "wss://api.xiaozhi.me/mcp/?token=placeholder-token",
                "access_token": "placeholder-token",
            },
        )


async def test_ping_only_server_and_distinct_ha_failure():
    messages = []

    async def server(ws):
        async for message in ws:
            messages.append(message)

    async with websockets.serve(server, "127.0.0.1", 0) as listener:
        port = listener.sockets[0].getsockname()[1]
        data = {
            "name": "test",
            "xiaozhi_endpoint": f"ws://127.0.0.1:{port}/",
            "access_token": "ha-token-placeholder",
        }
        with patch.object(
            XiaozhiMCPClient, "check_connection", new_callable=AsyncMock
        ) as check:
            assert await validate_input(MagicMock(), data) == {"title": "test"}
            check.side_effect = MCPAuthenticationError()
            with pytest.raises(AuthenticationFailed):
                await validate_input(MagicMock(), data)
            check.side_effect = OSError("do not expose server details")
            with pytest.raises(ConnectionFailed) as error:
                await validate_input(MagicMock(), data)
            assert error.value.code == "mcp_connection_failed"
            assert error.value.field == "mcp_server_url"
    assert messages == []


async def test_cert_loading_runs_outside_event_loop():
    loop_thread = threading.get_ident()

    def load_context():
        assert threading.get_ident() != loop_thread
        return ssl.create_default_context()

    with patch(
        "custom_components.xiaozhi_mcp.security.get_default_context",
        side_effect=load_context,
    ):
        options = await websocket_ssl_options("wss://example.com/")
    assert options["ssl"].check_hostname
    assert options["ssl"].verify_mode == ssl.CERT_REQUIRED
    assert await websocket_ssl_options("ws://localhost/") == {}


@pytest.mark.parametrize("status", [401, 403])
async def test_real_mcp_auth_failure(status):
    import aiohttp

    async def denied(request):
        return web.Response(status=status)

    app = web.Application()
    app.router.add_get("/mcp_server/sse", denied)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = site._server.sockets[0].getsockname()[1]
    try:
        async with aiohttp.ClientSession() as session:
            client = XiaozhiMCPClient(
                MagicMock(), "placeholder", f"http://127.0.0.1:{port}/mcp_server/sse"
            )
            client.session = session
            with pytest.raises(MCPAuthenticationError):
                await client.check_connection()
    finally:
        await runner.cleanup()
