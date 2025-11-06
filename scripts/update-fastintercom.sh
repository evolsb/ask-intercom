#!/bin/bash
#
# FastIntercom MCP Auto-Update Script
# Checks for and installs updates to FastIntercom MCP
#

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

POETRY_BIN="${HOME}/.local/bin/poetry"

echo "🔄 FastIntercom MCP Update Check"
echo "==============================="

# Go to project root
cd "$(dirname "$0")/.."

# Function to get current version
get_current_version() {
    $POETRY_BIN run python -c "import fast_intercom_mcp; print(fast_intercom_mcp.__version__)" 2>/dev/null || echo "unknown"
}

# Function to get latest commit from GitHub
get_latest_commit() {
    curl -s https://api.github.com/repos/evolsb/FastIntercomMCP/commits/main | \
    python3 -c "import sys, json; print(json.load(sys.stdin)['sha'][:7])" 2>/dev/null || echo "unknown"
}

# Get current version info
echo "📦 Checking current installation..."
CURRENT_VERSION=$(get_current_version)
echo "Current version: $CURRENT_VERSION"

# Get latest available version
echo "🌐 Checking for updates..."
LATEST_COMMIT=$(get_latest_commit)
echo "Latest commit: $LATEST_COMMIT"

# Check if we have the latest
NEEDS_UPDATE=false

# If we can't determine versions, assume update needed
if [ "$CURRENT_VERSION" = "unknown" ] || [ "$LATEST_COMMIT" = "unknown" ]; then
    echo -e "${YELLOW}⚠️  Cannot determine versions, proceeding with update${NC}"
    NEEDS_UPDATE=true
elif [ "$CURRENT_VERSION" != "$LATEST_COMMIT" ]; then
    echo -e "${YELLOW}📈 Update available${NC}"
    NEEDS_UPDATE=true
else
    echo -e "${GREEN}✅ Already up to date${NC}"
fi

if [ "$NEEDS_UPDATE" = true ]; then
    echo ""
    echo "🚀 Updating FastIntercom MCP..."
    
    # Remove and reinstall to get latest
    echo "📦 Removing current version..."
    $POETRY_BIN remove fast-intercom-mcp --quiet || true
    
    echo "📦 Installing latest version..."
    $POETRY_BIN add git+https://github.com/evolsb/FastIntercomMCP.git
    
    # Verify new version
    NEW_VERSION=$(get_current_version)
    echo -e "${GREEN}✅ Updated to version: $NEW_VERSION${NC}"
    
    # Run health check
    echo ""
    echo "🏥 Running health check..."
    if [ -f "scripts/check-fastintercom-health.sh" ]; then
        ./scripts/check-fastintercom-health.sh
    else
        echo "Health check script not found, skipping"
    fi
    
    echo ""
    echo -e "${GREEN}🎉 Update complete!${NC}"
    echo ""
    echo "📋 You may need to restart any running MCP servers"
    
else
    echo ""
    echo "📋 No update needed"
fi

echo ""
echo "💡 To check for updates regularly, consider adding this to cron:"
echo "   0 */6 * * * cd $(pwd) && ./scripts/update-fastintercom.sh >> /tmp/fastintercom-update.log 2>&1"
