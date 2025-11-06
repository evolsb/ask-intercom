#!/bin/bash
# Script to fetch and display Railway deployment logs

echo "=== Railway Project Status ==="
railway status

echo -e "\n=== Railway Environment Variables ==="
railway variables | grep -E "RAILWAY_|INTERCOM_" | head -10

echo -e "\n=== Recent Deployment Logs ==="
echo "Fetching deployment logs..."
railway logs -d 2>&1 | tail -100

echo -e "\n=== Recent Build Logs ==="
echo "Fetching build logs..."
railway logs -b 2>&1 | tail -50

echo -e "\n=== Live Application Status ==="
RAILWAY_URL=$(railway variables | grep RAILWAY_PUBLIC_DOMAIN | awk -F'│' '{print $2}' | xargs)
if [ ! -z "$RAILWAY_URL" ]; then
    echo "Checking https://$RAILWAY_URL/api/health"
    curl -s "https://$RAILWAY_URL/api/health" | python3 -m json.tool 2>/dev/null || echo "Failed to fetch health status"
fi

echo -e "\n=== Access Logs via Web ==="
echo "You can also access logs via:"
echo "- Debug logs: https://$RAILWAY_URL/api/logs?lines=50"
echo "- Health check: https://$RAILWAY_URL/api/health"
echo "- Debug info: https://$RAILWAY_URL/api/debug"
