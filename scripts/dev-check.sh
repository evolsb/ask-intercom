#!/bin/bash
# Development check script to prevent stale server issues

set -e

echo "🔍 Checking for development issues..."

# Check for running Ask-Intercom processes
echo ""
echo "📋 Checking for running Ask-Intercom processes..."
RUNNING_PROCS=$(ps aux | grep -E "python.*ask-intercom|uvicorn.*ask-intercom" | grep -v grep || true)

if [ -n "$RUNNING_PROCS" ]; then
    echo "⚠️  Found running Ask-Intercom processes:"
    echo "$RUNNING_PROCS"
    echo ""
    echo "💡 Consider stopping them before making changes:"
    echo "   pkill -f 'python.*ask-intercom'"
    echo "   pkill -f 'uvicorn.*ask-intercom'"
else
    echo "✅ No running Ask-Intercom processes found"
fi

# Check for uncommitted changes
echo ""
echo "📋 Checking git status..."
if ! git diff-index --quiet HEAD -- 2>/dev/null; then
    echo "⚠️  You have uncommitted changes:"
    git status --porcelain
    echo ""
    echo "💡 Consider committing changes before starting servers"
else
    echo "✅ Working directory is clean"
fi

# Check for model parameter validation
echo ""
echo "📋 Checking for potential parameter issues..."
if grep -r "CostInfo(" src/ | grep -v "from_usage\|zero_cost" >/dev/null 2>&1; then
    echo "⚠️  Found direct CostInfo() calls - consider using helper methods:"
    grep -r "CostInfo(" src/ | grep -v "from_usage\|zero_cost" || true
    echo ""
    echo "💡 Use CostInfo.from_usage() or CostInfo.zero_cost() instead"
else
    echo "✅ All CostInfo usage follows safe patterns"
fi

# Check for active ports
echo ""
echo "📋 Checking for services on common ports..."
for port in 3000 8000; do
    if lsof -i :$port >/dev/null 2>&1; then
        PROC_INFO=$(lsof -i :$port | tail -n +2)
        echo "⚠️  Port $port is in use:"
        echo "$PROC_INFO"
    else
        echo "✅ Port $port is available"
    fi
done

echo ""
echo "🎯 Development check complete!"
echo ""
echo "💡 To start fresh development server:"
echo "   ./scripts/dev-check.sh"
echo "   env -i HOME=\"\$HOME\" PATH=\"\$PATH\" ~/.local/bin/poetry run uvicorn src.web.main:app --host 0.0.0.0 --port 8000 --reload"
