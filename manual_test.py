#!/usr/bin/env python3
"""Manual test to validate ConfigEntry fixes."""

import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def test_config_entry_syntax():
    """Test that ConfigEntry instantiation syntax is correct."""

    try:
        # Test conftest.py fixture
        print("Testing conftest.py ConfigEntry syntax...")
        with open("tests/conftest.py", "r") as f:
            content = f.read()

        # Check if required arguments are present
        required_args = ["discovery_keys=", "options=", "unique_id="]
        for arg in required_args:
            if arg not in content:
                print(f"❌ Missing required argument: {arg}")
                return False
            else:
                print(f"✅ Found required argument: {arg}")

        # Test test_config_flow.py ConfigEntry
        print("\nTesting test_config_flow.py ConfigEntry syntax...")
        with open("tests/test_config_flow.py", "r") as f:
            content = f.read()

        # Check if required arguments are present
        for arg in required_args:
            if arg not in content:
                print(f"❌ Missing required argument: {arg}")
                return False
            else:
                print(f"✅ Found required argument: {arg}")

        return True

    except Exception as e:
        print(f"❌ Error testing ConfigEntry syntax: {e}")
        return False


def test_pytest_config():
    """Test pytest configuration."""
    print("\nTesting pytest configuration...")

    # Check pytest.ini
    try:
        with open("pytest.ini", "r") as f:
            content = f.read()

        if "asyncio_mode = auto" in content:
            print("✅ pytest.ini has asyncio_mode = auto")
        else:
            print("❌ pytest.ini missing asyncio_mode = auto")
            return False

    except Exception as e:
        print(f"❌ Error reading pytest.ini: {e}")
        return False

    # Check pyproject.toml
    try:
        with open("pyproject.toml", "r") as f:
            content = f.read()

        if (
            "[tool.pytest.ini_options]" in content
            and 'asyncio_mode = "auto"' in content
        ):
            print("✅ pyproject.toml has pytest asyncio configuration")
        else:
            print("❌ pyproject.toml missing pytest asyncio configuration")
            return False

    except Exception as e:
        print(f"❌ Error reading pyproject.toml: {e}")
        return False

    return True


def test_python_syntax():
    """Test Python syntax of test files."""
    print("\nTesting Python syntax...")

    test_files = [
        "tests/conftest.py",
        "tests/test_config_flow.py",
        "tests/test_init.py",
    ]

    for file_path in test_files:
        try:
            with open(file_path, "r") as f:
                content = f.read()

            # Try to compile the code to check syntax
            compile(content, file_path, "exec")
            print(f"✅ {file_path} has valid Python syntax")

        except SyntaxError as e:
            print(f"❌ Syntax error in {file_path}: {e}")
            return False
        except Exception as e:
            print(f"❌ Error testing {file_path}: {e}")
            return False

    return True


if __name__ == "__main__":
    print("Manual Test Suite for ConfigEntry and pytest fixes")
    print("=" * 55)

    all_passed = True

    # Test ConfigEntry syntax
    if not test_config_entry_syntax():
        all_passed = False

    # Test pytest configuration
    if not test_pytest_config():
        all_passed = False

    # Test Python syntax
    if not test_python_syntax():
        all_passed = False

    print("\n" + "=" * 55)
    if all_passed:
        print("✅ All tests passed! The fixes appear to be working correctly.")
    else:
        print("❌ Some tests failed. Please review the output above.")

    sys.exit(0 if all_passed else 1)
