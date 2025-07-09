#!/usr/bin/env python3
"""Quick test to verify the integration imports work."""


def test_imports():
    """Test basic imports."""
    try:
        from custom_components.xiaozhi_mcp import DOMAIN

        print(f"✓ Successfully imported DOMAIN: {DOMAIN}")
    except ImportError as e:
        print(f"✗ Failed to import DOMAIN: {e}")
        return False

    try:
        from custom_components.xiaozhi_mcp import async_setup_entry

        print("✓ Successfully imported async_setup_entry")
    except ImportError as e:
        print(f"✗ Failed to import async_setup_entry: {e}")
        return False

    # Test other core components
    try:
        from custom_components.xiaozhi_mcp.coordinator import XiaozhiMCPCoordinator

        print("✓ Successfully imported XiaozhiMCPCoordinator")
    except ImportError as e:
        print(f"✗ Failed to import XiaozhiMCPCoordinator: {e}")
        return False

    try:
        from custom_components.xiaozhi_mcp.mcp_client import XiaozhiMCPClient

        print("✓ Successfully imported XiaozhiMCPClient")
    except ImportError as e:
        print(f"✗ Failed to import XiaozhiMCPClient: {e}")
        return False

    return True


def test_homeassistant_imports():
    """Test Home Assistant imports."""
    try:
        from homeassistant.config_entries import ConfigEntry
        from homeassistant.core import HomeAssistant

        print("✓ Successfully imported HomeAssistant core components")
        return True
    except ImportError as e:
        print(f"✗ Failed to import HomeAssistant components: {e}")
        return False


if __name__ == "__main__":
    print("Running quick integration tests...")
    print("=" * 50)

    success = True
    success &= test_homeassistant_imports()
    success &= test_imports()

    print("=" * 50)
    if success:
        print("✓ All imports successful!")
    else:
        print("✗ Some imports failed!")

    print("\nTesting manifest.json validation...")
    import json

    try:
        with open("custom_components/xiaozhi_mcp/manifest.json", "r") as f:
            manifest = json.load(f)
        print(f"✓ manifest.json is valid JSON with domain: {manifest.get('domain')}")
    except Exception as e:
        print(f"✗ manifest.json error: {e}")
        success = False

    print("\nTesting hacs.json validation...")
    try:
        with open("hacs.json", "r") as f:
            hacs = json.load(f)
        print(f"✓ hacs.json is valid JSON with name: {hacs.get('name')}")
    except Exception as e:
        print(f"✗ hacs.json error: {e}")
        success = False

    exit(0 if success else 1)
