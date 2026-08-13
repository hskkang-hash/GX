#!/bin/bash

# Clear Docker containers, images, volumes, and networks for GuardianX project
# Must be run with proper permissions (sudo if necessary)

echo "=== GuardianX Docker Cleanup Script ==="
echo ""

# Stop and remove containers
echo "Stopping and removing containers..."
docker compose down || echo "No running compose services found."

# Clean up any dead/exited containers
echo "Cleaning up dead/exited containers..."
docker container prune -f

docker image prune -a -f

docker volume prune -a -f

docker builder prune -a -f

docker system prune -a -f --volumes


# Remove project networks
echo "Removing project networks..."
docker network ls | grep -i "guardianx\|guardianx-network" | awk '{print $1}' | xargs -r docker network rm

echo ""
echo "=== Cleanup Complete ==="
echo "Docker resources for GuardianX project have been cleaned up."
