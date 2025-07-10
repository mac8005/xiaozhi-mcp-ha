#!/bin/bash
# Setup script for running Xiaozhi MCP integration locally

echo "🚀 Setting up Xiaozhi MCP integration for local development..."

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not found. Please install Python 3."
    exit 1
fi

# Check if pip is available
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 is required but not found. Please install pip3."
    exit 1
fi

# Install required packages
echo "📦 Installing required Python packages..."
pip3 install -r requirements.txt

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ .env file not found. Please create one with the required environment variables."
    echo "Template .env file has been created for you."
    exit 1
fi

echo "✅ Setup complete!"
echo ""
echo "To run the integration locally:"
echo "  python3 run_local.py"
echo ""
echo "To run with GetLiveContext simulation:"
echo "  python3 run_local.py --simulate"
echo "  python3 run_local.py --simulate --entity-id sensor.my_sensor"
echo ""
echo "To send a custom message:"
echo '  python3 run_local.py --custom-message '"'"'{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"GetLiveContext","arguments":{"entity_id":"sensor.test"}}}'"'"''
echo ""
echo "To stop the integration, press Ctrl+C"
echo ""
echo "Logs will be written to: xiaozhi_mcp_local.log"
