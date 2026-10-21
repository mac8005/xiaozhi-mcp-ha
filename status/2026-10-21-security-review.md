# Security and code review — 0.0.26

Reviewed all integration modules, metadata/services/translations, existing tests, local runner/setup, release scripts/workflow and user documentation against baseline e0fbfe0 (0.0.25).

## Findings and remediation

- Confirmed: setup and runtime explicitly disabled WebSocket certificate and hostname verification. A network intermediary could impersonate the cloud endpoint and issue MCP requests or observe responses. Restored verification; regression test uses a real server with an untrusted certificate and verifies rejection in both paths.
- Confirmed: logs included endpoint URLs (which may contain cloud tokens), payloads and server response bodies. Removed these logs and suppressed underlying WebSocket protocol debug output; retained metadata and exception class names.
- Hardening: previously arbitrary SSE path advertisements could select authenticated POST destinations on the configured server. Restricted same-origin MCP paths, rejected redirects, and validated bounded JSON-RPC objects. No independent cross-origin credential theft exploit was demonstrated against the old URL concatenation.
- Reliability: gather waited forever when one pipe ended; cancellation and session state were not consistently cleaned up. One transport owner now cancels both pipes, clears old endpoints/queues and awaits shutdown.
- Protocol: parse SSE event boundaries and multiline data, honor advertised endpoint readiness, accept 202/204 acknowledgement, reject malformed payloads, bound queues/events and request timeouts.
- Compatibility: removed deprecated OptionsFlow config_entry assignment (#31), applied options with reloads, fixed per-entry service routing, removed false 1.0.0 device firmware and unsubstantiated silver quality label.
- Tooling: replaced duplicated shell release logic and shell=True calls with one checked argv-based script; isolated development dependencies; removed local payload monitor and automatic simulation modes; added CI and release gates/checksum output.

## Report boundary

Issue #33 requests a private contact and contains no technical vulnerability details or comments. GitHub private vulnerability reporting was enabled and read back as enabled. The fixes above are independently identified; whether they match the reporter's finding remains unknown. No evidence of exploitation was established.

## Validation

- Python 3.13.12 / Home Assistant 2026.2.3: 39 tests pass, including real local HTTP/SSE/WebSocket roundtrip, TLS rejection, endpoint escapes, redirects, JSON-RPC boundaries, cancellation and multi-entry services.
- Ruff lint and formatting pass.
- Bandit: no medium/high findings; one low-severity use of random for reconnect jitter (not cryptographic).
- pip-audit on requirements.txt: no known vulnerabilities. HA-owned dependencies remain governed by the installed HA version; this is not a claim that all HA releases are vulnerability-free.
- GitHub run 39576323395: Linux tests, Ruff, Bandit, Hassfest and HACS all passed. Release run 39576609210 passed the same gates and published v0.0.26.
- CI diagnostics initially generated a 1 MiB test name from the oversized-message fixture. Explicit short parameter IDs reduced verbose test output to 4 KB; Linux CI then completed successfully.
- No live Home Assistant or physical Xiaozhi device validation performed.

## Upgrade impact

Non-loopback HTTP/WS configurations must migrate to valid TLS. Existing logs may contain credentials or household data; review access and rotate exposed credentials. Service callers with multiple entries must supply entry_id. Legacy HTTP/SSE remains the supported protocol. Local simulation CLI options were removed to avoid accidental household actions and sensitive output.

## Published release

- Release: https://github.com/mac8005/xiaozhi-mcp-ha/releases/tag/v0.0.26
- Tag commit: f3b64882a3ed0b64b6d52898fdefde0413747a16
- Downloaded archive: 12 files, each byte-for-byte equal to the tagged source; manifest version 0.0.26 and ZIP integrity verified.
- SHA-256: 9a6363e1c5cd9a028122aca10a1940c1a97fe8efcd8e9fd6decb608623e6a911; matches published SHA256SUMS.
- Issue reply posted and read back: https://github.com/mac8005/xiaozhi-mcp-ha/issues/33#issuecomment-6312615364
- Private vulnerability reporting read back as enabled; no private technical report was available during this review.
