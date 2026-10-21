# Security policy

Report vulnerabilities privately using [GitHub private vulnerability reporting](https://github.com/mac8005/xiaozhi-mcp-ha/security/advisories/new). Include the affected version, prerequisites, reproduction steps and impact. Do not post tokens, endpoint URLs containing tokens, household data or exploit details in public issues.

Security fixes are provided in the latest release. Upgrade older installations before investigating a suspected issue.

## Trust boundary

The configured Xiaozhi service can invoke the tools exposed by your authenticated Home Assistant MCP server and receive their results. This is the purpose of the bridge; it is not an authorization boundary between the cloud and exposed tools. Only connect services you trust, limit exposed entities, and use a dedicated non-administrator Home Assistant user where practical. A long-lived access token is a sensitive credential; protect Home Assistant configuration and backups.

Connections outside loopback require TLS with a valid certificate. Plain HTTP/WS is accepted only for localhost or a loopback IP. A private LAN address does not imply encrypted or authenticated transport. There is no certificate-verification bypass.

Version 0.0.26 removes endpoint and message payload logging. Earlier versions could write sensitive endpoint URLs and household messages into logs. Review access to retained logs; rotate affected endpoint credentials if those logs were shared or exposed. The review did not establish that any installation was exploited.
