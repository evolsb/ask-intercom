#!/bin/bash
#
# FastIntercom MCP Monitor Script
# Ensures FastIntercom MCP server stays running and healthy
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PID_FILE="/tmp/fastintercom-mcp.pid"
LOG_FILE="${PROJECT_DIR}/.ask-intercom-analytics/logs/fastintercom-mcp.log"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Create log directory if needed
mkdir -p "$(dirname "$LOG_FILE")"

# Function to log with timestamp
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# Function to check if FastIntercom MCP is running
is_mcp_running() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            return 0  # Running
        else
            rm -f "$PID_FILE"  # Clean up stale PID file
            return 1  # Not running
        fi
    else
        return 1  # Not running
    fi
}

# Function to start FastIntercom MCP
start_mcp() {
    log "Starting FastIntercom MCP server..."
    
    cd "$PROJECT_DIR"
    
    # Start server in background
    nohup ./scripts/start-fastintercom-mcp.sh > "$LOG_FILE" 2>&1 &
    MCP_PID=$!
    
    # Save PID
    echo "$MCP_PID" > "$PID_FILE"
    
    # Wait a moment and check if it's still running
    sleep 2
    if ps -p "$MCP_PID" > /dev/null 2>&1; then
        log "FastIntercom MCP started successfully (PID: $MCP_PID)"
        return 0
    else
        log "Failed to start FastIntercom MCP"
        rm -f "$PID_FILE"
        return 1
    fi
}

# Function to stop FastIntercom MCP
stop_mcp() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        log "Stopping FastIntercom MCP (PID: $PID)..."
        
        if ps -p "$PID" > /dev/null 2>&1; then
            kill "$PID"
            sleep 2
            
            # Force kill if still running
            if ps -p "$PID" > /dev/null 2>&1; then
                kill -9 "$PID"
                sleep 1
            fi
        fi
        
        rm -f "$PID_FILE"
        log "FastIntercom MCP stopped"
    else
        log "FastIntercom MCP was not running"
    fi
}

# Function to restart FastIntercom MCP
restart_mcp() {
    log "Restarting FastIntercom MCP..."
    stop_mcp
    sleep 1
    start_mcp
}

# Function to check health
check_health() {
    # Basic health checks
    local healthy=true
    
    # Check if process is running
    if ! is_mcp_running; then
        log "❌ FastIntercom MCP is not running"
        healthy=false
    fi
    
    # Check if log file is growing (indicates activity)
    if [ -f "$LOG_FILE" ]; then
        local log_age=$(($(date +%s) - $(stat -c%Y "$LOG_FILE" 2>/dev/null || stat -f%m "$LOG_FILE" 2>/dev/null || echo 0)))
        if [ $log_age -gt 3600 ]; then  # 1 hour
            log "⚠️  Log file hasn't been updated in $((log_age/60)) minutes"
        fi
    fi
    
    if $healthy; then
        log "✅ FastIntercom MCP is healthy"
        return 0
    else
        log "❌ FastIntercom MCP health check failed"
        return 1
    fi
}

# Main logic based on command
case "${1:-monitor}" in
    "start")
        if is_mcp_running; then
            echo -e "${YELLOW}FastIntercom MCP is already running${NC}"
        else
            start_mcp
        fi
        ;;
        
    "stop")
        stop_mcp
        ;;
        
    "restart")
        restart_mcp
        ;;
        
    "status")
        if is_mcp_running; then
            PID=$(cat "$PID_FILE")
            echo -e "${GREEN}✅ FastIntercom MCP is running (PID: $PID)${NC}"
            
            # Show recent log entries
            if [ -f "$LOG_FILE" ]; then
                echo ""
                echo "Recent log entries:"
                tail -5 "$LOG_FILE"
            fi
        else
            echo -e "${RED}❌ FastIntercom MCP is not running${NC}"
        fi
        ;;
        
    "health")
        check_health
        ;;
        
    "monitor")
        log "Starting FastIntercom MCP monitor..."
        
        # Main monitoring loop
        while true; do
            if ! is_mcp_running; then
                log "FastIntercom MCP is not running, starting..."
                start_mcp
            else
                # Periodic health check
                check_health || {
                    log "Health check failed, restarting..."
                    restart_mcp
                }
            fi
            
            # Wait before next check
            sleep 300  # 5 minutes
        done
        ;;
        
    "logs")
        if [ -f "$LOG_FILE" ]; then
            tail -f "$LOG_FILE"
        else
            echo "No log file found at $LOG_FILE"
        fi
        ;;
        
    *)
        echo "Usage: $0 {start|stop|restart|status|health|monitor|logs}"
        echo ""
        echo "Commands:"
        echo "  start    - Start FastIntercom MCP server"
        echo "  stop     - Stop FastIntercom MCP server"
        echo "  restart  - Restart FastIntercom MCP server"
        echo "  status   - Check if server is running"
        echo "  health   - Run health checks"
        echo "  monitor  - Start monitoring loop (keeps server running)"
        echo "  logs     - Show live logs"
        exit 1
        ;;
esac
