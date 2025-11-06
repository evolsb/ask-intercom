#!/usr/bin/env python3
"""
Dependency check script for Ask-Intercom.

This script verifies that all required dependencies are properly installed
and accessible, helping prevent runtime issues.
"""

import subprocess
import sys
from pathlib import Path


def check_dependency(package_name: str, import_name: str = None) -> bool:
    """Check if a dependency is properly installed."""
    import_name = import_name or package_name.replace("-", "_")

    try:
        # Check if package is installed via Poetry
        result = subprocess.run(
            [str(Path.home() / ".local/bin/poetry"), "show", package_name],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )

        if result.returncode != 0:
            print(f"❌ Package '{package_name}' not found in Poetry dependencies")
            return False

        # Check if module can be imported
        try:
            subprocess.run(
                [
                    str(Path.home() / ".local/bin/poetry"),
                    "run",
                    "python",
                    "-c",
                    f"import {import_name}",
                ],
                capture_output=True,
                text=True,
                check=True,
                cwd=Path(__file__).parent.parent,
            )
            print(f"✅ {package_name} ({import_name}) is properly installed")
            return True
        except subprocess.CalledProcessError:
            print(
                f"❌ Package '{package_name}' is installed but module '{import_name}' cannot be imported"
            )
            return False

    except Exception as e:
        print(f"❌ Error checking {package_name}: {e}")
        return False


def main():
    """Check all critical dependencies."""
    print("🔍 Checking Ask-Intercom dependencies...")

    dependencies = [
        ("openai", "openai"),
        ("httpx", "httpx"),
        ("pydantic", "pydantic"),
        ("rich", "rich"),
        ("fastapi", "fastapi"),
        ("mcp", "mcp"),
        ("fast-intercom-mcp", "fast_intercom_mcp"),
    ]

    all_good = True

    for package, import_name in dependencies:
        if not check_dependency(package, import_name):
            all_good = False

    if all_good:
        print("\n✅ All dependencies are properly installed!")
        return 0
    else:
        print("\n❌ Some dependencies have issues. Run 'poetry install' to fix.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
