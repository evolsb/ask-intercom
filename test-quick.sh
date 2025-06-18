#!/bin/bash
# Quick test script for development

set -e

echo "🧪 Running Quick Tests for Ask-Intercom"
echo "========================================"

# Backend tests (fast unit tests only)
echo "🔍 Running backend API tests..."
~/.local/bin/poetry run pytest tests/web/ -v --tb=short

# Code quality checks
echo "🔍 Checking code formatting..."
~/.local/bin/poetry run black --check src/ tests/ || (echo "❌ Code formatting issues found. Run: ~/.local/bin/poetry run black src/ tests/" && exit 1)

echo "🔍 Running linter..."
~/.local/bin/poetry run ruff check src/ tests/ || (echo "❌ Linting issues found. Fix them and try again." && exit 1)

# Frontend build test
echo "🔍 Testing frontend build..."
cd frontend
pnpm run build
cd ..

echo "✅ All quick tests passed!"
echo "💡 Run 'python run_tests.py' for comprehensive testing"
