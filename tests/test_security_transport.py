"""Exercise credential boundaries, real TLS rejection and stream lifecycle."""

import asyncio
import json
import ssl
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest
import trustme
import websockets
from aiohttp import web

from custom_components.xiaozhi_mcp.config_flow import (
    ConnectionFailed,
    OptionsFlowHandler,
    validate_input,
)
from custom_components.xiaozhi_mcp.coordinator import XiaozhiMCPCoordinator
from custom_components.xiaozhi_mcp.mcp_client import XiaozhiMCPClient
from custom_components.xiaozhi_mcp.security import (
    resolve_endpoint,
    validate_message,
    validate_url,
)


@pytest.mark.parametrize(
    "url",
    [
        "http://example.com/mcp_server/sse",
        "ws://192.168.1.2/ws",
        "https://user:pass@example.com/",
        "https://example.com/#secret",
        "https://example.com:bad/",
        "https://example.com/\nsecret",
    ],
)
def test_unsafe_config_urls(url):
    with pytest.raises(ValueError):
        validate_url(url, websocket=url.startswith("ws"))


@pytest.mark.parametrize(
    "endpoint",
    [
        "https://evil.example/mcp_server/messages",
        "//evil.example/mcp_server/messages",
        "/api/services/lock/unlock",
        "/mcp_server/../api",
        "/mcp_server/%2e%2e/api",
        "/mcp_server/%252e%252e/api",
        "http://ha.example/mcp_server/messages",
    ],
)
def test_endpoint_escape(endpoint):
    with pytest.raises(ValueError):
        resolve_endpoint("https://ha.example/mcp_server/sse", endpoint)


def test_valid_endpoint_and_zero_id():
    assert (
        resolve_endpoint(
            "http://localhost:8123/mcp_server/sse",
            "/mcp_server/messages/?session_id=abc",
        )
        == "http://localhost:8123/mcp_server/messages/?session_id=abc"
    )
    assert validate_message('{"jsonrpc":"2.0","id":0,"method":"ping"}')["id"] == 0


@pytest.mark.parametrize(
    "message",
    ["[]", "null", '{"entity_id":"lock.front"}', "invalid", "x" * (1024 * 1024 + 1)],
    ids=["array", "null", "non_rpc", "invalid_json", "oversized"],
)
def test_invalid_messages(message):
    with pytest.raises(ValueError):
        validate_message(message)


async def test_sse_multiline_and_endpoint():
    client = XiaozhiMCPClient(MagicMock(), "secret")

    async def lines():
        for line in [
            b": heartbeat\n",
            b"\n",
            b"event:endpoint\n",
            b"data:/mcp_server/messages/?session_id=a\n",
            b"\n",
            b"event: message\n",
            b'data: {"jsonrpc":"2.0",\n',
            b'data: "id":0,"result":{}}\n',
            b"\n",
        ]:
            yield line

    client._sse_response = MagicMock(content=lines())
    await client._read_sse_stream()
    assert client._ready.is_set()
    assert json.loads(client._sse_queue.get_nowait())["id"] == 0
    client._clear_session_state()
    assert not client._ready.is_set()
    assert client._latest_endpoint is None


async def test_http_202_redirect_and_cleanup():
    received = []

    async def post(request):
        received.append((request.headers.get("Authorization"), await request.json()))
        return web.Response(status=202)

    async def redirect(request):
        raise web.HTTPTemporaryRedirect("/mcp_server/messages/")

    app = web.Application()
    app.router.add_post("/mcp_server/messages/", post)
    app.router.add_post("/mcp_server/redirect", redirect)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = site._server.sockets[0].getsockname()[1]
    try:
        async with aiohttp.ClientSession() as session:
            client = XiaozhiMCPClient(
                MagicMock(), "test-secret", f"http://127.0.0.1:{port}/mcp_server/sse"
            )
            client.session = session
            client._ready.set()
            client._latest_endpoint = "/mcp_server/messages/"
            await client.send_to_mcp('{"jsonrpc":"2.0","method":"ping","id":0}')
            assert received[0][0] == "Bearer test-secret"
            client._latest_endpoint = "/mcp_server/redirect"
            with pytest.raises(ConnectionError):
                await client.send_to_mcp('{"jsonrpc":"2.0","method":"ping"}')
            assert len(received) == 1
            await client.disconnect_from_mcp()
            assert not session.closed  # HA owns the session.
    finally:
        await runner.cleanup()


async def test_untrusted_certificate_rejected_in_setup_and_runtime(caplog):
    ca = trustme.CA()
    certificate = ca.issue_cert("localhost")
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    certificate.configure_cert(context)

    async def echo(ws):
        async for message in ws:
            await ws.send(message)

    async with websockets.serve(echo, "127.0.0.1", 0, ssl=context) as server:
        port = server.sockets[0].getsockname()[1]
        endpoint = f"wss://localhost:{port}/?token=DO_NOT_LOG"
        data = {
            "name": "test",
            "xiaozhi_endpoint": endpoint,
            "access_token": "DO_NOT_LOG_TOKEN",
        }
        with pytest.raises(ConnectionFailed):
            await validate_input(MagicMock(), data)
        entry = MagicMock(data={}, options={})
        with patch(
            "custom_components.xiaozhi_mcp.coordinator.XiaozhiMCPClient"
        ) as factory:
            factory.return_value.connect_to_mcp = AsyncMock()
            factory.return_value.disconnect_from_mcp = AsyncMock()
            coordinator = XiaozhiMCPCoordinator(
                MagicMock(),
                entry,
                "test",
                endpoint,
                "secret",
                30,
                "http://localhost:8123/mcp_server/sse",
            )
            with pytest.raises(ssl.SSLCertVerificationError):
                await coordinator._connect()
            assert not coordinator.connected
    assert "DO_NOT_LOG" not in caplog.text


async def test_one_pipe_ending_cancels_sibling():
    with patch("custom_components.xiaozhi_mcp.coordinator.XiaozhiMCPClient"):
        coordinator = XiaozhiMCPCoordinator(
            MagicMock(),
            MagicMock(data={}, options={}),
            "test",
            "wss://example.com/ws",
            "secret",
            30,
            "http://localhost:8123/mcp_server/sse",
        )
    cancelled = asyncio.Event()

    async def wait_forever():
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.set()

    coordinator._pipe_websocket_to_mcp = AsyncMock()
    coordinator._pipe_mcp_to_websocket = wait_forever
    coordinator._connected = True
    await asyncio.wait_for(coordinator._handle_messages(), 1)
    assert cancelled.is_set()
    assert not coordinator.connected


def test_options_flow_no_deprecated_assignment():
    assert isinstance(OptionsFlowHandler(), OptionsFlowHandler)


async def test_bridge_roundtrip_and_shutdown():
    """Run real local WebSocket and SSE servers through the production bridge."""
    requests = asyncio.Queue()
    stop = asyncio.Event()
    returned = asyncio.Future()

    async def sse(request):
        assert request.headers["Authorization"] == "Bearer local-test-token"
        response = web.StreamResponse(headers={"Content-Type": "text/event-stream"})
        await response.prepare(request)
        await response.write(
            b"event: endpoint\ndata: /mcp_server/messages/?session_id=test\n\n"
        )
        try:
            message = await requests.get()
            payload = json.dumps(
                {"jsonrpc": "2.0", "id": message["id"], "result": {"ok": True}}
            )
            await response.write(f"event: message\ndata: {payload}\n\n".encode())
            await stop.wait()
        finally:
            return response

    async def post(request):
        assert request.query["session_id"] == "test"
        assert request.headers["Authorization"] == "Bearer local-test-token"
        await requests.put(await request.json())
        return web.Response(status=202)

    async def cloud(ws):
        await ws.send('{"jsonrpc":"2.0","id":0,"method":"ping"}')
        returned.set_result(json.loads(await ws.recv()))
        await stop.wait()

    app = web.Application()
    app.router.add_get("/mcp_server/sse", sse)
    app.router.add_post("/mcp_server/messages/", post)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = site._server.sockets[0].getsockname()[1]
    try:
        async with (
            websockets.serve(cloud, "127.0.0.1", 0) as server,
            aiohttp.ClientSession() as session,
        ):
            ws_port = server.sockets[0].getsockname()[1]
            coordinator = XiaozhiMCPCoordinator(
                MagicMock(),
                MagicMock(data={}, options={}),
                "test",
                f"ws://127.0.0.1:{ws_port}",
                "local-test-token",
                30,
                f"http://127.0.0.1:{port}/mcp_server/sse",
            )
            coordinator._mcp_client.session = session
            try:
                await coordinator._connect()
                assert await asyncio.wait_for(returned, 3) == {
                    "jsonrpc": "2.0",
                    "id": 0,
                    "result": {"ok": True},
                }
                assert coordinator.connected
            finally:
                await coordinator.async_shutdown()
                stop.set()
            assert coordinator._message_task is None
            assert coordinator._mcp_client._mcp_task is None
            assert not coordinator.connected
    finally:
        stop.set()
        await runner.cleanup()


async def test_services_route_current_entry_not_last_registered():
    from types import SimpleNamespace

    from homeassistant.exceptions import ServiceValidationError

    from custom_components.xiaozhi_mcp import _async_setup_services

    first, second = AsyncMock(), AsyncMock()
    hass = MagicMock()
    hass.data = {"xiaozhi_mcp": {"first": first, "second": second}}
    hass.services.has_service.return_value = False
    await _async_setup_services(hass, second)
    callbacks = {
        call.args[1]: call.args[2]
        for call in hass.services.async_register.call_args_list
    }
    with pytest.raises(ServiceValidationError):
        await callbacks["reconnect"](SimpleNamespace(data={}))
    await callbacks["reconnect"](SimpleNamespace(data={"entry_id": "first"}))
    first.async_reconnect.assert_awaited_once()
    second.async_reconnect.assert_not_awaited()
    del hass.data["xiaozhi_mcp"]["second"]
    await callbacks["send_message"](
        SimpleNamespace(data={"message": '{"jsonrpc":"2.0","method":"ping"}'})
    )
    first.async_send_message.assert_awaited_once_with(
        {"jsonrpc": "2.0", "method": "ping"}
    )
