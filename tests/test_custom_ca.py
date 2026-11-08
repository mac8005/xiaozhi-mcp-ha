"""Verify scoped MCP certificate trust with real TLS and configuration flows."""

import asyncio
import ipaddress
import ssl
import threading
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest
import trustme
from aiohttp import web
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID

from custom_components.xiaozhi_mcp.config_flow import (
    ConfigFlow,
    ConnectionFailed,
    OptionsFlowHandler,
    validate_mcp,
)
from custom_components.xiaozhi_mcp.coordinator import XiaozhiMCPCoordinator
from custom_components.xiaozhi_mcp.mcp_client import (
    MCPCertificateError,
    XiaozhiMCPClient,
    _load_ca_context,
)


@asynccontextmanager
async def tls_server(tmp_path, kind="private_ca"):
    """Serve authenticated SSE and POST with a private test certificate."""
    ca = trustme.CA()
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ca_path = tmp_path / "ca.pem"
    if kind == "self_signed":
        key = ec.generate_private_key(ec.SECP256R1())
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "test")])
        cert = (
            x509.CertificateBuilder()
            .subject_name(name)
            .issuer_name(name)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.now(UTC) - timedelta(days=1))
            .not_valid_after(datetime.now(UTC) + timedelta(days=1))
            .add_extension(
                x509.SubjectAlternativeName(
                    [x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]
                ),
                critical=False,
            )
            .add_extension(
                x509.BasicConstraints(ca=False, path_length=None), critical=True
            )
            .sign(key, hashes.SHA256())
        )
        ca_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
        key_path = tmp_path / "key.pem"
        key_path.write_bytes(
            key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption(),
            )
        )
        context.load_cert_chain(ca_path, key_path)
    else:
        dates = {}
        if kind == "expired":
            dates = {
                "not_before": datetime.now(UTC) - timedelta(days=2),
                "not_after": datetime.now(UTC) - timedelta(days=1),
            }
        cert = ca.issue_cert(
            "wrong.example" if kind == "wrong_host" else "127.0.0.1", **dates
        )
        cert.configure_cert(context)
        ca.cert_pem.write_to_path(ca_path)
    received = []
    stop = asyncio.Event()

    async def sse(request):
        assert request.headers["Authorization"] == "Bearer test-token"
        response = web.StreamResponse(headers={"Content-Type": "text/event-stream"})
        await response.prepare(request)
        await response.write(b"event: endpoint\ndata: /mcp_server/messages/test\n\n")
        await stop.wait()
        return response

    async def post(request):
        assert request.headers["Authorization"] == "Bearer test-token"
        received.append(await request.json())
        return web.Response(status=202)

    app = web.Application()
    app.router.add_get("/mcp_server/sse", sse)
    app.router.add_post("/mcp_server/messages/test", post)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0, ssl_context=context)
    await site.start()
    port = site._server.sockets[0].getsockname()[1]
    try:
        yield f"https://127.0.0.1:{port}/mcp_server/sse", str(ca_path), received
    finally:
        stop.set()
        await runner.cleanup()


@pytest.mark.parametrize("kind", ["private_ca", "self_signed"])
async def test_custom_trust_setup_sse_post_and_isolation(tmp_path, kind):
    async with tls_server(tmp_path, kind) as (url, cafile, received):
        async with aiohttp.ClientSession() as session:
            with patch(
                "custom_components.xiaozhi_mcp.mcp_client.async_get_clientsession",
                return_value=session,
            ):
                await validate_mcp(
                    MagicMock(),
                    {
                        "access_token": "test-token",
                        "mcp_server_url": url,
                        "mcp_ca_cert": cafile,
                    },
                )
                client = XiaozhiMCPClient(MagicMock(), "test-token", url, cafile)
                try:
                    await client.connect_to_mcp()
                    await client.send_to_mcp('{"jsonrpc":"2.0","method":"ping","id":1}')
                    assert received == [{"jsonrpc": "2.0", "method": "ping", "id": 1}]
                    assert client._ssl_context.check_hostname
                    assert client._ssl_context.verify_mode == ssl.CERT_REQUIRED
                    # The same HA-owned session must still reject this server by default.
                    with pytest.raises(aiohttp.ClientConnectorCertificateError):
                        await session.get(url)
                finally:
                    await client.disconnect_from_mcp()
                assert not session.closed


@pytest.mark.parametrize("failure", ["no_ca", "wrong_ca", "wrong_host", "expired"])
async def test_tls_failures_rejected_for_setup_and_both_requests(tmp_path, failure):
    async with tls_server(tmp_path, failure) as (url, cafile, received):
        if failure == "no_ca":
            cafile = ""
        elif failure == "wrong_ca":
            wrong_ca = tmp_path / "wrong.pem"
            trustme.CA().cert_pem.write_to_path(wrong_ca)
            cafile = str(wrong_ca)
        async with aiohttp.ClientSession() as session:
            with patch(
                "custom_components.xiaozhi_mcp.mcp_client.async_get_clientsession",
                return_value=session,
            ):
                with pytest.raises(ConnectionFailed) as error:
                    await validate_mcp(
                        MagicMock(),
                        {
                            "access_token": "test-token",
                            "mcp_server_url": url,
                            "mcp_ca_cert": cafile,
                        },
                    )
                assert error.value.code == "mcp_tls_failed"
                client = XiaozhiMCPClient(MagicMock(), "test-token", url, cafile)
                with pytest.raises(aiohttp.ClientConnectorCertificateError):
                    await client.check_connection()
                client._ready.set()
                client._latest_endpoint = "/mcp_server/messages/test"
                with pytest.raises(aiohttp.ClientConnectorCertificateError):
                    await client.send_to_mcp('{"jsonrpc":"2.0","method":"ping"}')
                assert received == []


@pytest.mark.parametrize("kind", ["missing", "invalid_pem", "directory", "relative"])
async def test_invalid_certificate_files_fail_closed(tmp_path, kind):
    path = tmp_path / "certificate.pem"
    if kind == "invalid_pem":
        path.write_text("not a certificate")
    elif kind == "directory":
        path.mkdir()
    elif kind == "relative":
        path = "certificate.pem"
    with pytest.raises(MCPCertificateError):
        await XiaozhiMCPClient(
            MagicMock(), "test-token", mcp_ca_cert=str(path)
        ).check_connection()
    with pytest.raises(ConnectionFailed) as error:
        await validate_mcp(
            MagicMock(), {"access_token": "test-token", "mcp_ca_cert": str(path)}
        )
    assert error.value.code == "mcp_ca_invalid"
    assert error.value.field == "mcp_ca_cert"


async def test_ca_loading_off_loop_and_cached(tmp_path):
    ca_path = tmp_path / "ca.pem"
    trustme.CA().cert_pem.write_to_path(ca_path)
    loop_thread = threading.get_ident()

    def load(path):
        assert threading.get_ident() != loop_thread
        return _load_ca_context(path)

    client = XiaozhiMCPClient(MagicMock(), "test-token", mcp_ca_cert=str(ca_path))
    with (
        patch(
            "custom_components.xiaozhi_mcp.mcp_client._load_ca_context",
            side_effect=load,
        ) as loader,
        patch("custom_components.xiaozhi_mcp.mcp_client.async_get_clientsession"),
    ):
        await client._ensure_session()
        await client._ensure_session()
    loader.assert_called_once()


async def test_setup_maps_certificate_file_error(tmp_path):
    flow = ConfigFlow()
    flow.hass = MagicMock()
    websocket = AsyncMock()
    pong = asyncio.get_running_loop().create_future()
    pong.set_result(None)
    websocket.ping.return_value = pong
    connect = MagicMock()
    connect.return_value.__aenter__.return_value = websocket
    with patch("websockets.connect", connect):
        result = await flow.async_step_user(
            {
                "name": "test",
                "xiaozhi_endpoint": "ws://localhost/",
                "access_token": "test-token",
                "mcp_ca_cert": str(tmp_path / "missing.pem"),
            }
        )
    assert result["errors"] == {"mcp_ca_cert": "mcp_ca_invalid"}


async def test_options_validate_save_reuse_and_clear(tmp_path):
    entry = MagicMock(data={"access_token": "test-token"}, options={})
    flow = OptionsFlowHandler()
    flow.handler = "test-entry"
    flow.hass = MagicMock()
    flow.hass.config_entries.async_get_known_entry.return_value = entry
    async with tls_server(tmp_path) as (url, cafile, _):
        entry.data["mcp_server_url"] = url
        async with aiohttp.ClientSession() as session:
            with patch(
                "custom_components.xiaozhi_mcp.mcp_client.async_get_clientsession",
                return_value=session,
            ):
                result = await flow.async_step_init(
                    {"mcp_ca_cert": str(tmp_path / "missing.pem")}
                )
                assert result["errors"] == {"mcp_ca_cert": "mcp_ca_invalid"}
                result = await flow.async_step_init({"mcp_ca_cert": " " + cafile + " "})
                assert result["type"] == "create_entry"
                assert result["data"]["mcp_ca_cert"] == cafile
                entry.options = result["data"]
                coordinator = XiaozhiMCPCoordinator(
                    MagicMock(),
                    entry,
                    "test",
                    "wss://example.com",
                    "test-token",
                    30,
                    url,
                )
                await coordinator._mcp_client.check_connection()
                # Clearing cannot silently accept a still-untrusted HTTPS server.
                result = await flow.async_step_init({"mcp_ca_cert": ""})
                assert result["errors"] == {"base": "mcp_tls_failed"}
                entry.data["mcp_server_url"] = "http://localhost:8123/mcp_server/sse"
                with patch.object(
                    XiaozhiMCPClient, "check_connection", new_callable=AsyncMock
                ):
                    result = await flow.async_step_init({"mcp_ca_cert": ""})
                assert result["type"] == "create_entry"
                entry.data["mcp_ca_cert"] = cafile
                entry.options = result["data"]
                coordinator = XiaozhiMCPCoordinator(
                    MagicMock(),
                    entry,
                    "test",
                    "wss://example.com",
                    "test-token",
                    30,
                    url,
                )
                assert coordinator._mcp_client.mcp_ca_cert == ""
