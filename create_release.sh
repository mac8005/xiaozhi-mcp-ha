#!/bin/sh
# Use the same validated release path on macOS and Linux.
set -eu
cd "$(dirname "$0")"
exec .venv/bin/python create_release.py "$@"
