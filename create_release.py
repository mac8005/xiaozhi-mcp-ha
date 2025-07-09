#!/usr/bin/env python3
"""
Simple script to create a new version tag and trigger a release.
Usage: python3 create_release.py [version]
Example: python3 create_release.py 0.1.0
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path


def run_command(cmd, check=True):
    """Run a shell command and return the result."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=check)
        return result.stdout.strip(), result.stderr.strip()
    except subprocess.CalledProcessError as e:
        print(f"❌ Command failed: {cmd}")
        print(f"Error: {e.stderr}")
        sys.exit(1)


def validate_version(version):
    """Validate version format (semantic versioning)."""
    if not re.match(r'^\d+\.\d+\.\d+$', version):
        print("❌ Invalid version format. Please use semantic versioning (e.g., 1.0.0)")
        sys.exit(1)


def check_tag_exists(version):
    """Check if tag already exists."""
    stdout, _ = run_command(f"git tag -l", check=False)
    if f"v{version}" in stdout.split('\n'):
        print(f"❌ Tag v{version} already exists!")
        sys.exit(1)


def get_current_version():
    """Get current version from manifest.json."""
    manifest_path = Path("custom_components/xiaozhi_mcp/manifest.json")
    if not manifest_path.exists():
        return "0.0.0"
    
    try:
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
            return manifest.get('version', '0.0.0')
    except (json.JSONDecodeError, FileNotFoundError):
        return "0.0.0"


def suggest_next_version():
    """Suggest next version based on current version."""
    current = get_current_version()
    major, minor, patch = map(int, current.split('.'))
    
    print(f"Current version: {current}")
    print("Suggested versions:")
    print(f"  Patch: {major}.{minor}.{patch + 1}")
    print(f"  Minor: {major}.{minor + 1}.0")
    print(f"  Major: {major + 1}.0.0")


def update_manifest(version):
    """Update version in manifest.json."""
    manifest_path = Path("custom_components/xiaozhi_mcp/manifest.json")
    
    if not manifest_path.exists():
        print(f"❌ Manifest file not found: {manifest_path}")
        sys.exit(1)
    
    try:
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        
        manifest['version'] = version
        
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=4)
        
        print(f"✅ Updated manifest.json version to {version}")
        
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"❌ Failed to update manifest.json: {e}")
        sys.exit(1)


def check_git_status():
    """Check if we're in a git repository and working directory status."""
    if not Path(".git").exists():
        print("❌ Not in a git repository!")
        sys.exit(1)
    
    stdout, _ = run_command("git status --porcelain", check=False)
    if stdout.strip():
        print("⚠️  Working directory is not clean. Uncommitted changes:")
        print(stdout)
        response = input("Do you want to continue anyway? (y/N): ").strip().lower()
        if response != 'y':
            print("ℹ️  Aborting release creation")
            sys.exit(1)


def main():
    """Main function."""
    print("🚀 Xiaozhi MCP Release Creator")
    print("=" * 32)
    
    # Check git status
    check_git_status()
    
    # Get version from argument or prompt
    if len(sys.argv) > 1:
        version = sys.argv[1]
    else:
        print()
        suggest_next_version()
        print()
        version = input("Enter new version (format: x.y.z): ").strip()
    
    # Validate version
    validate_version(version)
    
    # Check if tag exists
    check_tag_exists(version)
    
    print(f"ℹ️  Creating release for version v{version}")
    
    # Update manifest
    update_manifest(version)
    
    # Stage and commit
    run_command("git add custom_components/xiaozhi_mcp/manifest.json")
    run_command(f'git commit -m "chore: bump version to {version}"')
    print("✅ Committed version bump")
    
    # Create tag
    run_command(f"git tag v{version}")
    print(f"✅ Created tag v{version}")
    
    # Push changes and tag
    print("ℹ️  Pushing changes and tag to origin...")
    run_command("git push origin main")
    run_command(f"git push origin v{version}")
    print("✅ Pushed changes and tag to origin")
    
    print()
    print(f"🎉 Release v{version} created successfully!")
    print("ℹ️  GitHub Actions will now build and publish the release")
    print("ℹ️  Check the Actions tab at: https://github.com/mac8005/xiaozhi-mcp-hacs/actions")
    print()
    print(f"📦 HACS users will be able to update to v{version} once the release is published")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help']:
        print(__doc__)
        sys.exit(0)
    
    main()
