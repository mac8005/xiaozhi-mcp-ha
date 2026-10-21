# Status
Updated: 2026-10-21

## In flight
- 0.0.26 security/refactor candidate implemented; awaiting GitHub validation before tagging.
- Issue #33 is a private-contact request, without technical details. Private reporting enabled and verified.

## Decisions
- Fix independently verified TLS bypass/log leakage; do not claim these match the undisclosed report.
- Require TLS outside loopback; retain legacy HTTP/SSE protocol.
- See [review and validation](2026-10-21-security-review.md).

## Next
1. Check CI, Hassfest and HACS results; repair any failures.
2. Tag/publish 0.0.26 and verify downloadable archive/checksum.
3. Comment on #33 with private-report link and verified release findings.

## Gotchas
- Live Home Assistant/device validation has not been performed.
- Python 3.13 development environment pins HA 2026.2.3.
- Multiple bridges require explicit entry_id for service calls.

## Log
- 2026-10-21: Linux job outlived process timeout with unavailable logs; retrying on explicit Ubuntu 24.04 to isolate runner-image behavior.
- 2026-10-21: Added process-level Linux test deadline and uncaptured verbose diagnostics because per-test signals did not finish the stalled run.
- 2026-10-21: Hassfest/HACS passed; Linux test job stalled, adding bounded test timeouts to expose the failing lifecycle path.
- 2026-10-21: Verified minimum HA coordinator API; ensured parent coordinator timers are cancelled during shutdown.
- 2026-10-21: Completed source review and implementation; 39 tests, Ruff, dependency audit and medium/high security checks pass.
- 2026-10-21: Started security review and initialized shared status.
