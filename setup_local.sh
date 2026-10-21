#!/bin/sh
# Create an isolated development environment without modifying system packages.
set -eu
cd "$(dirname "$0")"
python3.13 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
if [ ! -f .env ]; then
  (umask 077; printf '%s\n' 'XIAOZHI_ENDPOINT=' 'HA_ACCESS_TOKEN=' 'HA_MCP_ENDPOINT=http://localhost:8123/mcp_server/sse' > .env)
  echo 'Fill in .env before running the bridge.'
fi
echo 'Run: .venv/bin/python run_local.py'
