#!/usr/bin/env python3
"""Comprehensive validation script for HACS compliance."""

import json
import os
import subprocess
import sys
from pathlib import Path


def run_command(cmd, description):
    """Run a command and return success status."""
    print(f"Checking {description}...")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✓ {description} passed")
            return True
        else:
            print(f"✗ {description} failed:")
            print(result.stdout)
            print(result.stderr)
            return False
    except Exception as e:
        print(f"✗ {description} error: {e}")
        return False


def validate_json_file(file_path, description):
    """Validate a JSON file."""
    print(f"Validating {description}...")
    try:
        with open(file_path, "r") as f:
            data = json.load(f)
        print(f"✓ {description} is valid JSON")
        return True, data
    except Exception as e:
        print(f"✗ {description} error: {e}")
        return False, None


def validate_manifest():
    """Validate the manifest.json file."""
    success, manifest = validate_json_file(
        "custom_components/xiaozhi_mcp/manifest.json", "manifest.json"
    )
    if not success:
        return False

    required_fields = ["domain", "name", "version", "documentation", "requirements"]
    for field in required_fields:
        if field not in manifest:
            print(f"✗ manifest.json missing required field: {field}")
            return False

    print(f"✓ manifest.json contains all required fields")
    return True


def validate_hacs():
    """Validate the hacs.json file."""
    success, hacs = validate_json_file("hacs.json", "hacs.json")
    if not success:
        return False

    required_fields = ["name", "render_readme"]
    for field in required_fields:
        if field not in hacs:
            print(f"✗ hacs.json missing required field: {field}")
            return False

    print(f"✓ hacs.json contains all required fields")
    return True


def validate_imports():
    """Validate that all imports work correctly."""
    print("Validating imports...")
    try:
        # Test HomeAssistant imports
        from homeassistant.config_entries import ConfigEntry
        from homeassistant.core import HomeAssistant

        # Test integration imports
        from custom_components.xiaozhi_mcp import DOMAIN, async_setup_entry
        from custom_components.xiaozhi_mcp.coordinator import XiaozhiMCPCoordinator
        from custom_components.xiaozhi_mcp.mcp_client import XiaozhiMCPClient

        print("✓ All imports successful")
        return True
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False


def validate_files():
    """Validate that all required files exist."""
    print("Validating file structure...")
    required_files = [
        "custom_components/xiaozhi_mcp/__init__.py",
        "custom_components/xiaozhi_mcp/manifest.json",
        "custom_components/xiaozhi_mcp/config_flow.py",
        "custom_components/xiaozhi_mcp/coordinator.py",
        "custom_components/xiaozhi_mcp/mcp_client.py",
        "custom_components/xiaozhi_mcp/sensor.py",
        "custom_components/xiaozhi_mcp/switch.py",
        "hacs.json",
        "README.md",
        "LICENSE",
    ]

    missing_files = []
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)

    if missing_files:
        print(f"✗ Missing files: {missing_files}")
        return False

    print("✓ All required files present")
    return True


def main():
    """Main validation function."""
    print("Starting HACS compliance validation...")
    print("=" * 60)

    all_checks_passed = True

    # File structure validation
    all_checks_passed &= validate_files()

    # JSON validation
    all_checks_passed &= validate_manifest()
    all_checks_passed &= validate_hacs()

    # Import validation
    all_checks_passed &= validate_imports()

    # Code formatting validation
    all_checks_passed &= run_command(
        "black --check custom_components/ tests/", "code formatting (black)"
    )
    all_checks_passed &= run_command(
        "isort --check-only --profile black custom_components/ tests/",
        "import sorting (isort)",
    )

    print("=" * 60)
    if all_checks_passed:
        print("🎉 All HACS compliance checks passed!")
        print("The integration is ready for HACS and CI/CD validation.")
        return 0
    else:
        print("❌ Some checks failed!")
        print("Please fix the issues above before proceeding.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
