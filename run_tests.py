#!/usr/bin/env python3
"""
Comprehensive test runner for Ask-Intercom project.

This script runs all tests and provides a summary of results.
"""

import subprocess
import sys
import time
from pathlib import Path


def run_command(cmd, description):
    """Run a command and return the result."""
    print(f"\n🔍 {description}")
    print(f"Running: {' '.join(cmd)}")
    print("-" * 60)

    start_time = time.time()
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, cwd=Path(__file__).parent
        )
        end_time = time.time()
        duration = end_time - start_time

        if result.returncode == 0:
            print(f"✅ PASSED ({duration:.1f}s)")
            if result.stdout.strip():
                print(result.stdout)
            return True
        else:
            print(f"❌ FAILED ({duration:.1f}s)")
            if result.stdout.strip():
                print("STDOUT:", result.stdout)
            if result.stderr.strip():
                print("STDERR:", result.stderr)
            return False

    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False


def main():
    """Run all tests and provide summary."""
    print("🚀 Ask-Intercom Test Suite")
    print("=" * 60)

    tests = [
        {
            "cmd": ["poetry", "run", "pytest", "tests/web/", "-v"],
            "description": "Backend API Tests",
            "critical": True,
        },
        {
            "cmd": ["poetry", "run", "pytest", "tests/unit/", "-v"],
            "description": "Unit Tests",
            "critical": True,
        },
        {
            "cmd": ["poetry", "run", "pytest", "tests/integration/", "-v"],
            "description": "Integration Tests",
            "critical": False,  # These require real API keys
        },
        {
            "cmd": ["poetry", "run", "black", "--check", "src/", "tests/"],
            "description": "Code Formatting Check",
            "critical": True,
        },
        {
            "cmd": ["poetry", "run", "ruff", "check", "src/", "tests/"],
            "description": "Code Linting",
            "critical": True,
        },
    ]

    results = []
    critical_failures = 0

    for test in tests:
        success = run_command(test["cmd"], test["description"])
        results.append(
            {
                "description": test["description"],
                "success": success,
                "critical": test["critical"],
            }
        )

        if not success and test["critical"]:
            critical_failures += 1

    # Frontend tests (separate because they're in a different directory)
    print("\n🔍 Frontend Build Test")
    print("-" * 60)
    frontend_build = run_command(["pnpm", "build"], "Frontend Build Test")
    results.append(
        {
            "description": "Frontend Build Test",
            "success": frontend_build,
            "critical": True,
        }
    )
    if not frontend_build:
        critical_failures += 1

    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)

    for result in results:
        status = "✅ PASS" if result["success"] else "❌ FAIL"
        critical = " (CRITICAL)" if result["critical"] else ""
        print(f"{status} {result['description']}{critical}")

    print(f"\nTotal tests: {len(results)}")
    print(f"Passed: {sum(1 for r in results if r['success'])}")
    print(f"Failed: {sum(1 for r in results if not r['success'])}")
    print(f"Critical failures: {critical_failures}")

    if critical_failures > 0:
        print("\n❌ CRITICAL TESTS FAILED - Build should not proceed")
        sys.exit(1)
    else:
        print("\n✅ ALL CRITICAL TESTS PASSED - Build is ready")
        sys.exit(0)


if __name__ == "__main__":
    main()
