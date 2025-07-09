#!/bin/bash
# Test runner script for local testing

set -e

echo "Installing test dependencies..."
pip install websockets>=11.0.3 aiohttp>=3.8.0

echo "Running pytest with proper configuration..."
python -m pytest tests/ -v --tb=short

echo "Tests completed!"
