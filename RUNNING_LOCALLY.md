# Running locally

Use Python 3.13 and `./setup_local.sh` to create an isolated environment. Fill in the generated `.env` file:

```dotenv
XIAOZHI_ENDPOINT=wss://your-trusted-service.example/mcp/?token=YOUR_TOKEN
HA_ACCESS_TOKEN=YOUR_HOME_ASSISTANT_TOKEN
HA_MCP_ENDPOINT=http://localhost:8123/mcp_server/sse
```

Run `.venv/bin/python run_local.py`, optionally with `--debug` for transport metadata. Payloads and token-bearing URLs are never intentionally logged. Stop with Ctrl+C. Setup and shutdown failures close both connections.

This runner uses the production coordinator with a real Home Assistant core object and a minimal configuration-entry stand-in. It does not start a Home Assistant server or validate the integration's full setup/UI lifecycle. Use a running MCP server. Non-loopback endpoints require valid TLS. It does not send simulated household commands automatically.

For automated checks:

```sh
.venv/bin/python -m pytest
.venv/bin/ruff check custom_components tests run_local.py create_release.py
.venv/bin/bandit -r custom_components -ll
```

For releases, commit the manifest version, changelog and status first, then run `.venv/bin/python create_release.py VERSION`. The script verifies a clean main branch and passing tests, then pushes the tag. The release is only published after GitHub validation succeeds; verify the downloadable HACS archive and checksum afterwards.
