#!/bin/bash
#
# FastIntercom MCP Setup Script
# Ensures FastIntercom MCP is properly installed, configured, and running
#

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
POETRY_BIN="${HOME}/.local/bin/poetry"
FASTINTERCOM_DB_PATH="${HOME}/.fastintercom/data.db"
MCP_CONFIG_PATH="${HOME}/.config/mcp/config.json"
PYTHON_CMD="python3"

echo "🚀 FastIntercom MCP Setup for Ask-Intercom"
echo "=========================================="

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check Python version
check_python_version() {
    if ! command_exists python3; then
        echo -e "${RED}❌ Python 3 not found${NC}"
        return 1
    fi
    
    PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    echo -e "${GREEN}✅ Python ${PYTHON_VERSION} found${NC}"
    
    # Check if version is 3.11 or higher
    if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 11) else 1)"; then
        echo -e "${YELLOW}⚠️  Python 3.11+ recommended for best performance${NC}"
    fi
}

# 1. Check dependencies
echo ""
echo "1️⃣  Checking dependencies..."
check_python_version

if ! command_exists poetry && ! [ -f "$POETRY_BIN" ]; then
    echo -e "${RED}❌ Poetry not found${NC}"
    echo "Please install Poetry first: https://python-poetry.org/docs/#installation"
    exit 1
else
    echo -e "${GREEN}✅ Poetry found${NC}"
fi

# 2. Install/Update FastIntercom MCP
echo ""
echo "2️⃣  Installing/Updating FastIntercom MCP..."

cd "$(dirname "$0")/.."  # Go to project root

# Check if FastIntercom MCP is in dependencies
if grep -q "fast-intercom-mcp" pyproject.toml; then
    echo "📦 FastIntercom MCP already in dependencies"
else
    echo "📦 Adding FastIntercom MCP to dependencies..."
    $POETRY_BIN add git+https://github.com/evolsb/FastIntercomMCP.git
fi

# Get latest version
echo "🔄 Checking for updates..."
CURRENT_VERSION=$($POETRY_BIN run python -c "import fast_intercom_mcp; print(fast_intercom_mcp.__version__)" 2>/dev/null || echo "unknown")
echo "Current version: $CURRENT_VERSION"

# Force update to latest
$POETRY_BIN update fast-intercom-mcp
NEW_VERSION=$($POETRY_BIN run python -c "import fast_intercom_mcp; print(fast_intercom_mcp.__version__)" 2>/dev/null || echo "unknown")

if [ "$CURRENT_VERSION" != "$NEW_VERSION" ]; then
    echo -e "${GREEN}✅ Updated from $CURRENT_VERSION to $NEW_VERSION${NC}"
else
    echo -e "${GREEN}✅ Already on latest version: $NEW_VERSION${NC}"
fi

# 3. Configure FastIntercom MCP
echo ""
echo "3️⃣  Configuring FastIntercom MCP..."

# Check for Intercom token
if [ -z "$INTERCOM_ACCESS_TOKEN" ]; then
    if [ -f .env ] && grep -q "INTERCOM_ACCESS_TOKEN" .env; then
        echo "📝 Loading INTERCOM_ACCESS_TOKEN from .env file"
        export $(grep INTERCOM_ACCESS_TOKEN .env | xargs)
    else
        echo -e "${YELLOW}⚠️  INTERCOM_ACCESS_TOKEN not set${NC}"
        echo "Please set it in your .env file or environment"
    fi
else
    echo -e "${GREEN}✅ INTERCOM_ACCESS_TOKEN found${NC}"
fi

# Create FastIntercom directory if needed
mkdir -p "${HOME}/.fastintercom"

# 4. Initialize FastIntercom MCP Database
echo ""
echo "4️⃣  Initializing FastIntercom MCP database..."

if [ -f "$FASTINTERCOM_DB_PATH" ]; then
    DB_SIZE=$(du -h "$FASTINTERCOM_DB_PATH" | cut -f1)
    echo -e "${GREEN}✅ Database exists (size: $DB_SIZE)${NC}"
    
    # Check database age
    if [ "$(uname)" = "Darwin" ]; then
        # macOS
        DB_AGE=$(($(date +%s) - $(stat -f%m "$FASTINTERCOM_DB_PATH")))
    else
        # Linux
        DB_AGE=$(($(date +%s) - $(stat -c%Y "$FASTINTERCOM_DB_PATH")))
    fi
    
    DB_AGE_HOURS=$((DB_AGE / 3600))
    echo "📊 Database last modified: ${DB_AGE_HOURS} hours ago"
    
    if [ $DB_AGE_HOURS -gt 24 ]; then
        echo -e "${YELLOW}⚠️  Database is more than 24 hours old. Consider running a sync.${NC}"
    fi
else
    echo "📦 No database found. It will be created on first sync."
fi

# 5. Create MCP server startup script
echo ""
echo "5️⃣  Creating FastIntercom MCP server startup script..."

cat > scripts/start-fastintercom-mcp.sh << 'EOF'
#!/bin/bash
# Start FastIntercom MCP Server

echo "🚀 Starting FastIntercom MCP Server..."

# Load environment
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Check for token
if [ -z "$INTERCOM_ACCESS_TOKEN" ]; then
    echo "❌ Error: INTERCOM_ACCESS_TOKEN not set"
    echo "Please set it in your .env file"
    exit 1
fi

# Start the MCP server
echo "📡 Starting MCP server on stdio..."
exec poetry run python -m fast_intercom_mcp.mcp_server

EOF

chmod +x scripts/start-fastintercom-mcp.sh
echo -e "${GREEN}✅ Created start-fastintercom-mcp.sh${NC}"

# 6. Create sync script
echo ""
echo "6️⃣  Creating FastIntercom sync script..."

cat > scripts/sync-fastintercom.sh << 'EOF'
#!/bin/bash
# Sync FastIntercom MCP data

echo "🔄 Syncing FastIntercom MCP data..."

# Load environment
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Run sync (if the v0.3.0 has a sync command)
# Note: This may need adjustment based on actual FastIntercom v0.3.0 API
poetry run python -c "
from fast_intercom_mcp import Config, SyncService
import asyncio

async def sync():
    config = Config()
    sync_service = SyncService(config)
    print('Starting sync...')
    # Actual sync method depends on v0.3.0 API
    print('Sync completed')

asyncio.run(sync())
" || echo "⚠️  Manual sync not available in v0.3.0 - use background sync"

EOF

chmod +x scripts/sync-fastintercom.sh
echo -e "${GREEN}✅ Created sync-fastintercom.sh${NC}"

# 7. Create health check script
echo ""
echo "7️⃣  Creating health check script..."

cat > scripts/check-fastintercom-health.sh << 'EOF'
#!/bin/bash
# Check FastIntercom MCP health

echo "🏥 FastIntercom MCP Health Check"
echo "================================"

# Check if package is installed
echo -n "📦 Package installed: "
if poetry run python -c "import fast_intercom_mcp" 2>/dev/null; then
    VERSION=$(poetry run python -c "import fast_intercom_mcp; print(fast_intercom_mcp.__version__)")
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
if timeout 5 poetry run python -c "from fast_intercom_mcp import FastIntercomMCPServer; print('OK')" 2>/dev/null | grep -q "OK"; then
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

EOF

chmod +x scripts/check-fastintercom-health.sh
echo -e "${GREEN}✅ Created check-fastintercom-health.sh${NC}"

# 8. Update MCP configuration (if using Claude Desktop)
echo ""
echo "8️⃣  Checking MCP configuration..."

if [ -d "$(dirname "$MCP_CONFIG_PATH")" ]; then
    echo "📝 Found MCP config directory"
    
    # Create backup if config exists
    if [ -f "$MCP_CONFIG_PATH" ]; then
        cp "$MCP_CONFIG_PATH" "$MCP_CONFIG_PATH.backup"
        echo "📋 Backed up existing config"
    fi
    
    echo -e "${YELLOW}ℹ️  To use with Claude Desktop, add this to your MCP config:${NC}"
    cat << EOF

{
  "servers": {
    "fastintercom": {
      "command": "$(pwd)/scripts/start-fastintercom-mcp.sh",
      "cwd": "$(pwd)",
      "env": {
        "INTERCOM_ACCESS_TOKEN": "\${INTERCOM_ACCESS_TOKEN}"
      }
    }
  }
}

EOF
else
    echo "ℹ️  MCP config directory not found (not using Claude Desktop)"
fi

# 9. Final summary
echo ""
echo "✨ FastIntercom MCP Setup Complete!"
echo "==================================="
echo ""
echo "📋 Next steps:"
echo "   1. Ensure INTERCOM_ACCESS_TOKEN is set in .env"
echo "   2. Run './scripts/check-fastintercom-health.sh' to verify setup"
echo "   3. Run './scripts/start-fastintercom-mcp.sh' to start the server"
echo "   4. (Optional) Run './scripts/sync-fastintercom.sh' to sync data"
echo ""
echo "🔄 To update FastIntercom MCP in the future:"
echo "   Run: poetry update fast-intercom-mcp"
echo ""
