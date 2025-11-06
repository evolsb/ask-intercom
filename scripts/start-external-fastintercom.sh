#!/bin/bash
# Start external FastIntercom MCP Docker container

echo "🐳 Starting External FastIntercom MCP Container..."

# Load environment
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Check for required environment variables
if [ -z "$INTERCOM_ACCESS_TOKEN" ]; then
    echo "❌ Error: INTERCOM_ACCESS_TOKEN not set"
    echo "Please set it in your .env file"
    exit 1
fi

# Set defaults
CONTAINER_NAME=${FASTINTERCOM_CONTAINER_NAME:-fastintercom-mcp}
IMAGE_NAME=${FASTINTERCOM_IMAGE:-fast-intercom-mcp-fastintercom}
INITIAL_SYNC_DAYS=${FASTINTERCOM_INITIAL_SYNC_DAYS:-90}
LOG_LEVEL=${FASTINTERCOM_LOG_LEVEL:-INFO}

echo "📋 Configuration:"
echo "  Container: $CONTAINER_NAME"
echo "  Image: $IMAGE_NAME"
echo "  Initial sync: $INITIAL_SYNC_DAYS days"
echo "  Log level: $LOG_LEVEL"

# Check if container is already running
if docker ps --filter "name=$CONTAINER_NAME" --format "{{.Names}}" | grep -q "$CONTAINER_NAME"; then
    echo "✅ Container $CONTAINER_NAME is already running"
    docker logs --tail 10 "$CONTAINER_NAME"
    exit 0
fi

# Check if container exists but is stopped
if docker ps -a --filter "name=$CONTAINER_NAME" --format "{{.Names}}" | grep -q "$CONTAINER_NAME"; then
    echo "🔄 Starting existing container: $CONTAINER_NAME"
    docker start "$CONTAINER_NAME"
    
    # Wait for startup
    echo "⏳ Waiting for container to start..."
    sleep 5
    
    # Check if it's running
    if docker ps --filter "name=$CONTAINER_NAME" --format "{{.Names}}" | grep -q "$CONTAINER_NAME"; then
        echo "✅ Container started successfully"
        docker logs --tail 10 "$CONTAINER_NAME"
    else
        echo "❌ Container failed to start"
        docker logs --tail 20 "$CONTAINER_NAME"
        exit 1
    fi
else
    echo "🚀 Creating new container: $CONTAINER_NAME"
    
    # Create and start new container
    docker run -d \
        --name "$CONTAINER_NAME" \
        -e "INTERCOM_ACCESS_TOKEN=$INTERCOM_ACCESS_TOKEN" \
        -e "FASTINTERCOM_INITIAL_SYNC_DAYS=$INITIAL_SYNC_DAYS" \
        -e "FASTINTERCOM_LOG_LEVEL=$LOG_LEVEL" \
        -v fastintercom-data:/data \
        "$IMAGE_NAME" start
    
    if [ $? -eq 0 ]; then
        echo "✅ Container created successfully"
        
        # Wait for initial startup and sync
        echo "⏳ Waiting for initial startup (30 seconds)..."
        sleep 30
        
        # Show logs
        echo "📋 Container logs:"
        docker logs --tail 20 "$CONTAINER_NAME"
        
        # Check if container is still running
        if docker ps --filter "name=$CONTAINER_NAME" --format "{{.Names}}" | grep -q "$CONTAINER_NAME"; then
            echo "✅ Container is running and ready!"
        else
            echo "❌ Container stopped unexpectedly"
            docker logs "$CONTAINER_NAME"
            exit 1
        fi
    else
        echo "❌ Failed to create container"
        exit 1
    fi
fi

echo ""
echo "🎉 External FastIntercom MCP is ready!"
echo "📊 To check status: docker exec $CONTAINER_NAME python -m fast_intercom_mcp.cli status"
echo "🔄 To force sync: docker exec $CONTAINER_NAME python -m fast_intercom_mcp.cli sync --force"
echo "📋 To view logs: docker logs -f $CONTAINER_NAME"
