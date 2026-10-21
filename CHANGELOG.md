# Changelog

## [0.0.27] - 2026-10-21

- Clarify the two credentials: the full Xiaozhi URL includes its token; the dedicated field accepts a Home Assistant long-lived access token. Detect missing tokens on the official Xiaozhi endpoint before connecting.
- Use WebSocket ping/pong during setup instead of requiring an application-level MCP response, avoiding false connection failures.
- Report separate Xiaozhi authentication/TLS/network and Home Assistant authentication/TLS/MCP errors without exposing credentials.
- Load verified TLS contexts off the event loop in setup and runtime, addressing the blocking certificate-loading report in #31.
- Include English runtime translations so custom integration forms and errors display explanatory text.
- Document DNS and HTTP/HTTPS troubleshooting from #29. The reconnect and options-flow fixes from 0.0.26 remain included.

Restart Home Assistant after upgrading. Keep the complete Xiaozhi URL in the endpoint field. Live household/device validation is still required; automated tests use local servers.

## [0.0.26] - 2026-10-21

### Security
- Verify WebSocket TLS certificates and hostnames during setup and runtime.
- Require TLS for non-loopback connections. Existing LAN `http://` or `ws://` URLs must migrate to valid TLS, or use loopback when the server runs on the same host.
- Remove credential-bearing URL, response-body and household payload logging, including the local development runner.
- Restrict advertised MCP POST endpoints to the configured origin and `/mcp_server/` path; reject redirects and arbitrary/non-JSON-RPC payloads.
- Bound SSE events, WebSocket messages and response queues.
- Enable private vulnerability reporting and document the cloud-to-home trust boundary.

### Reliability and compatibility
- Cancel both forwarding tasks when either transport stops; clean up old connections before reconnecting or unloading.
- Reset session endpoints and queued responses across SSE sessions; parse multiline SSE events and accept HTTP 202/204 POST acknowledgements.
- Fix options flow for Home Assistant 2025.12+, apply saved options, and reload on options changes.
- Route services by integration entry; specify `entry_id` when multiple bridges exist. `send_message` accepts a JSON-RPC object or JSON string.
- Remove incorrect device firmware and unsupported quality-scale claims; require Home Assistant 2025.3 or later.
- Add automated regression tests and gate HACS release ZIP publication on tests, lint, Hassfest and HACS validation. Publish archive checksums.

### Upgrade and validation
- Restart Home Assistant after upgrading. Confirm the connection switch, exposed tools, reconnect behavior and options on your installation.
- The automated suite uses Home Assistant 2026.2.3 and local HTTP/TLS servers. Physical Xiaozhi hardware and the user's live Home Assistant installation were not exercised.
- Transport support remains legacy HTTP/SSE (`/mcp_server/sse`); this release does not add Streamable HTTP.
- Issue #33 has no private technical report yet; these are independently identified fixes, not confirmation of the reporter's undisclosed finding.

Manual installation: extract `xiaozhi_mcp.zip` into `config/custom_components/xiaozhi_mcp/`. HACS users can update normally.
