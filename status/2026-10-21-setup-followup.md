# Setup follow-up — 0.0.27

The endpoint field takes the complete Xiaozhi URL including its token. The access_token field is exclusively for a separate Home Assistant long-lived access token. No supplied credentials were used in network tests or saved in the repository.

Changes: missing-token validation for the official endpoint, WebSocket ping/pong setup test, field-specific connection/authentication/TLS errors, English runtime translations, off-event-loop verified certificate context loading in setup/runtime. README includes DNS and direct-HTTPS/reverse-proxy guidance.

Reviewed all open issues (#29, #30, #31, #33). Published evidence-based replies to #29/#30/#31; left issues open for reporter confirmation. #33 already has the private-reporting response; no duplicate reply added.

Validation: 45 tests passed locally and on Linux; Ruff, Bandit medium/high scan, Hassfest and HACS passed. Release workflow 39586063954 succeeded. Downloaded 13 archive files match tag f4e9d81f9de8282208e65ce00d5e77762071f4f8. SHA-256 ecc9271ab6275297a6cef106810a14798e2cd00aac9cc655091357f52c27fd25 matches published SHA256SUMS. No live household or physical-device test performed.
