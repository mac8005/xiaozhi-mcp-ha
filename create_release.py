#!/usr/bin/env python3
"""Push a release tag after version, changelog, clean-tree and test checks."""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def run(*args):
    return subprocess.run(
        args, cwd=ROOT, check=True, text=True, capture_output=True
    ).stdout.strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version", help="Already committed version (e.g. 0.0.26)")
    args = parser.parse_args()
    version = args.version
    if not re.fullmatch(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)", version):
        parser.error("Use a stable semantic version")
    if run("git", "status", "--porcelain"):
        parser.error("Commit all changes, including status, before releasing")
    if run("git", "branch", "--show-current") != "main":
        parser.error("Release from main")
    manifest = json.loads(
        (ROOT / "custom_components/xiaozhi_mcp/manifest.json").read_text()
    )
    if manifest["version"] != version:
        parser.error("Manifest version must match the requested version")
    if f"## [{version}]" not in (ROOT / "CHANGELOG.md").read_text():
        parser.error("Add version-specific release notes first")
    run("git", "fetch", "origin", "--tags")
    if run("git", "tag", "-l", f"v{version}"):
        parser.error("Tag already exists")
    run(sys.executable, "-m", "pytest")
    run("git", "push", "origin", "main")
    run("git", "tag", f"v{version}")
    run("git", "push", "origin", f"v{version}")
    print(
        f"Tag v{version} pushed. Publication is complete only after the release workflow and ZIP verification succeed."
    )


if __name__ == "__main__":
    main()
