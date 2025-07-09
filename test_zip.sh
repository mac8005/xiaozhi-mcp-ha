#!/bin/bash

# Test script to verify ZIP creation for HACS compatibility
# This script mimics the GitHub Actions workflow

set -e

echo "🧪 Testing ZIP creation for HACS compatibility"
echo "=============================================="

# Clean up any existing test files
rm -f xiaozhi_mcp.zip

# Create ZIP file the same way as the GitHub Actions workflow
echo "📦 Creating ZIP file..."
cd custom_components/xiaozhi_mcp
zip -r ../../xiaozhi_mcp.zip . -x "__pycache__/*" "*.pyc"
cd ../..

echo "✅ ZIP file created:"
ls -la xiaozhi_mcp.zip

echo ""
echo "📋 ZIP file contents:"
unzip -l xiaozhi_mcp.zip

echo ""
echo "🔍 Validating ZIP structure for HACS compatibility..."

# Check for required files in ZIP root
if unzip -l xiaozhi_mcp.zip | grep -q "manifest.json"; then
    echo "✅ manifest.json found in ZIP root"
else
    echo "❌ manifest.json not found in ZIP root"
    exit 1
fi

if unzip -l xiaozhi_mcp.zip | grep -q "__init__.py"; then
    echo "✅ __init__.py found in ZIP root"
else
    echo "❌ __init__.py not found in ZIP root"
    exit 1
fi

if unzip -l xiaozhi_mcp.zip | grep -q "config_flow.py"; then
    echo "✅ config_flow.py found in ZIP root"
else
    echo "❌ config_flow.py not found in ZIP root"
    exit 1
fi

if unzip -l xiaozhi_mcp.zip | grep -q "services.yaml"; then
    echo "✅ services.yaml found in ZIP root"
else
    echo "❌ services.yaml not found in ZIP root"
    exit 1
fi

echo ""
echo "🎉 ZIP structure is valid for HACS!"
echo "The integration files are now in the root of the ZIP file."
echo ""
echo "To clean up, run: rm xiaozhi_mcp.zip"
