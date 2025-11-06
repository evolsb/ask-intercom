#!/bin/bash
# Check FastIntercom MCP health

echo "🏥 FastIntercom MCP Health Check"
echo "================================"

# Check if package is installed
echo -n "📦 Package installed: "
if ~/.local/bin/poetry run python -c "import fast_intercom_mcp" 2>/dev/null; then
    VERSION=$(~/.local/bin/poetry run python -c "import fast_intercom_mcp; print(fast_intercom_mcp.__version__)")
    echo "✅ (v$VERSION)"
else
    echo "❌"
    exit 1
fi

# Check database
echo -n "💾 Database exists: "
if [ -f "$HOME/.fastintercom/data.db" ]; then
    SIZE=$(du -h "$HOME/.fastintercom/data.db" | cut -f1)
    echo "✅ ($SIZE)"
else
    echo "❌"
fi

# Check if MCP server can start
echo -n "🚀 MCP server can start: "
if timeout 5 ~/.local/bin/poetry run python -c "from fast_intercom_mcp import FastIntercomMCPServer; print('OK')" 2>/dev/null | grep -q "OK"; then
    echo "✅"
else
    echo "❌"
fi

# Check environment
echo -n "🔑 INTERCOM_ACCESS_TOKEN: "
if [ -n "$INTERCOM_ACCESS_TOKEN" ] || ([ -f .env ] && grep -q "INTERCOM_ACCESS_TOKEN" .env); then
    echo "✅"
else
    echo "❌"
fi

echo ""
echo "Run './scripts/start-fastintercom-mcp.sh' to start the MCP server"
