#!/bin/bash

echo "🔍 Polling FastIntercom MCP repository for new MCP tool implementations..."
echo "Looking for: get_data_info, check_coverage, get_sync_status, force_sync"
echo ""

REPO_URL="https://raw.githubusercontent.com/evolsb/FastIntercomMCP/main/fastintercom/mcp_server.py"
POLL_INTERVAL=30
MAX_POLLS=20  # 10 minutes total

for i in $(seq 1 $MAX_POLLS); do
    echo -n "Poll $i/$MAX_POLLS - $(date '+%H:%M:%S') - "
    
    # Check for the new MCP tools
    TOOLS_FOUND=$(curl -s -L "$REPO_URL" | grep -E "(get_data_info|check_coverage|get_sync_status|force_sync)" | wc -l)
    
    if [ "$TOOLS_FOUND" -ge 4 ]; then
        echo "✅ New MCP tools found! ($TOOLS_FOUND/4 tools detected)"
        echo ""
        echo "🎉 FastIntercom MCP has been updated with the new tools!"
        echo "Ready to reinstall and test integration."
        exit 0
    else
        echo "⏳ Tools not ready yet ($TOOLS_FOUND/4 found). Waiting..."
    fi
    
    if [ $i -lt $MAX_POLLS ]; then
        sleep $POLL_INTERVAL
    fi
done

echo ""
echo "⏰ Polling timeout reached. Changes may not be ready yet."
echo "You can manually check: $REPO_URL"
exit 1
