"""Exercise endpoint diagnostics, native route coexistence and repair recovery."""

import asyncio
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest
from aiohttp import web
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from custom_components.xiaozhi_mcp import async_remove_entry, async_setup_entry
from custom_components.xiaozhi_mcp.config_flow import (
    ConnectionFailed,
    OptionsFlowHandler,
    validate_mcp,
)
from custom_components.xiaozhi_mcp.coordinator import XiaozhiMCPCoordinator
from custom_components.xiaozhi_mcp.mcp_client import MCPServerError, XiaozhiMCPClient


@asynccontextmanager
async def endpoint(handler):
    app = web.Application()
    app.router.add_get("/mcp_server/sse", handler)
    # A Streamable HTTP service can coexist without blocking the legacy SSE route.
    app.router.add_post("/api/mcp", lambda request: web.json_response({"ok": True}))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = site._server.sockets[0].getsockname()[1]
    try:
        async with aiohttp.ClientSession() as session:
            with patch(
                "custom_components.xiaozhi_mcp.mcp_client.async_get_clientsession",
                return_value=session,
            ):
                yield f"http://127.0.0.1:{port}/mcp_server/sse", session
    finally:
        await runner.cleanup()


async def valid_sse(request):
    return web.Response(
        text="event: endpoint\ndata: /mcp_server/messages/session\n\n",
        content_type="text/event-stream",
    )


@pytest.mark.parametrize(
    "path", ["/api/mcp", "/api/mcp/", "/api/mcp/assist", "/api/mcp_http"]
)
async def test_streamable_urls_rejected_without_sending_credentials(path):
    with patch(
        "custom_components.xiaozhi_mcp.mcp_client.async_get_clientsession"
    ) as session:
        with pytest.raises(ConnectionFailed) as error:
            await validate_mcp(
                MagicMock(),
                {
                    "access_token": "SECRET",
                    "mcp_server_url": "https://example.com" + path,
                },
            )
    assert error.value.code == "mcp_wrong_transport"
    session.assert_not_called()


@pytest.mark.parametrize(
    "status,content_type,body,code",
    [
        (
            404,
            "text/plain",
            "Found multiple Model Context Protocol configurations",
            "mcp_multiple_servers",
        ),
        (404, "text/plain", "not found SECRET", "mcp_endpoint_unavailable"),
        (405, "text/plain", "method not allowed", "mcp_endpoint_unavailable"),
        (200, "text/html", "<html>SECRET</html>", "mcp_invalid_response"),
        (200, "application/json", '{"secret":"SECRET"}', "mcp_invalid_response"),
        (200, "text/event-stream", ": heartbeat\n\n", "mcp_invalid_response"),
        (
            200,
            "text/event-stream",
            "event: endpoint\ndata: https://evil.example/SECRET\n\n",
            "mcp_invalid_response",
        ),
    ],
    ids=[
        "duplicate_native",
        "missing_route",
        "wrong_method",
        "html",
        "json",
        "no_endpoint",
        "unsafe_endpoint",
    ],
)
async def test_endpoint_diagnostics(status, content_type, body, code, caplog):
    async def response(request):
        return web.Response(status=status, content_type=content_type, text=body)

    async with endpoint(response) as (url, session):
        client = XiaozhiMCPClient(MagicMock(), "SECRET", url)
        with pytest.raises(MCPServerError) as error:
            await client.check_connection()
        assert error.value.code == code
        assert "SECRET" not in str(error.value)
        assert not client._ready.is_set()
        assert client._sse_response is None
        assert not session.closed
        with pytest.raises(ConnectionFailed) as flow_error:
            await validate_mcp(
                MagicMock(), {"access_token": "SECRET", "mcp_server_url": url}
            )
        assert flow_error.value.code == code
    assert "SECRET" not in caplog.text


async def test_fragmented_duplicate_diagnostic():
    async def response(request):
        stream = web.StreamResponse(status=404)
        await stream.prepare(request)
        await stream.write(b"Found multiple Model ")
        await asyncio.sleep(0.01)
        await stream.write(b"Context Protocol configurations")
        return stream

    async with endpoint(response) as (url, _):
        with pytest.raises(MCPServerError) as error:
            await XiaozhiMCPClient(MagicMock(), "test", url).check_connection()
        assert error.value.code == "mcp_multiple_servers"


async def test_missing_handshake_is_bounded():
    stop = asyncio.Event()

    async def response(request):
        stream = web.StreamResponse(headers={"Content-Type": "text/event-stream"})
        await stream.prepare(request)
        await stop.wait()
        return stream

    async with endpoint(response) as (url, _):
        try:
            with pytest.raises(MCPServerError) as error:
                await asyncio.wait_for(
                    XiaozhiMCPClient(MagicMock(), "test", url).check_connection(), 7
                )
            assert error.value.code == "mcp_invalid_response"
        finally:
            stop.set()


async def test_native_routes_coexist_and_probe_does_not_call_tools():
    async with endpoint(valid_sse) as (url, session):
        await XiaozhiMCPClient(MagicMock(), "test", url).check_connection()
        async with session.post(url.replace("/mcp_server/sse", "/api/mcp")) as response:
            assert response.status == 200


async def test_real_repairs_are_entry_scoped_and_clear_on_recovery_or_removal(tmp_path):
    hass = HomeAssistant(str(tmp_path))
    registry = ir.async_get(hass)
    coordinators = []
    try:
        for entry_id in ("first", "second"):
            entry = MagicMock(entry_id=entry_id, data={}, options={})
            coordinator = XiaozhiMCPCoordinator(
                hass,
                entry,
                entry_id,
                "wss://example.com",
                "test",
                30,
                "https://example.com/api/mcp",
            )
            coordinators.append(coordinator)
            coordinator.async_reconnect = AsyncMock()
            coordinator.async_refresh = AsyncMock()
            coordinator._connection_monitor_loop = AsyncMock()
            with pytest.raises(MCPServerError):
                await coordinator.async_setup()
            issue = registry.async_get_issue("xiaozhi_mcp", f"mcp_server_{entry_id}")
            assert issue.translation_key == "mcp_wrong_transport"
            assert issue.severity == ir.IssueSeverity.WARNING
            coordinator.async_reconnect.assert_not_awaited()
        async with endpoint(valid_sse) as (url, _):
            coordinators[0]._mcp_client.mcp_server_url = url
            await coordinators[0].async_setup()
        assert registry.async_get_issue("xiaozhi_mcp", "mcp_server_first") is None
        assert registry.async_get_issue("xiaozhi_mcp", "mcp_server_second") is not None
        await async_remove_entry(hass, coordinators[1].config_entry)
        assert registry.async_get_issue("xiaozhi_mcp", "mcp_server_second") is None
    finally:
        for coordinator in coordinators:
            await coordinator.async_shutdown()
        await hass.async_stop(force=True)


async def test_options_can_correct_endpoint_and_runtime_uses_saved_url():
    entry = MagicMock(
        data={
            "access_token": "test-token",
            "mcp_server_url": "https://example.com/api/mcp",
            "name": "test",
            "xiaozhi_endpoint": "wss://example.com",
        },
        options={},
    )
    hass = MagicMock()
    hass.data = {}
    hass.config_entries.async_get_known_entry.return_value = entry
    hass.config_entries.async_forward_entry_setups = AsyncMock()
    flow = OptionsFlowHandler()
    flow.hass = hass
    flow.handler = "test-entry"
    result = await flow.async_step_init(
        {"mcp_server_url": "http://192.168.1.2/mcp_server/sse"}
    )
    assert result["errors"] == {"mcp_server_url": "invalid_endpoint"}
    async with endpoint(valid_sse) as (url, _):
        result = await flow.async_step_init({"mcp_server_url": url})
    assert result["type"] == "create_entry"
    entry.options = result["data"]
    with (
        patch("custom_components.xiaozhi_mcp.XiaozhiMCPCoordinator") as factory,
        patch("custom_components.xiaozhi_mcp.dr.async_get"),
        patch(
            "custom_components.xiaozhi_mcp._async_setup_services",
            new_callable=AsyncMock,
        ),
    ):
        factory.return_value.async_setup = AsyncMock()
        assert await async_setup_entry(hass, entry)
        assert factory.call_args.args[-1] == url
