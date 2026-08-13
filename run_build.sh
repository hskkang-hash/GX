#!/bin/bash

# Default to dev environment if not specified
ENV=${2:-dev}
ENV_FILE="frontend/.env"
COMPOSE_FILE="docker-compose.yml"

# Set environment-specific files
if [ "$ENV" == "stg" ]; then
    ENV_FILE="frontend/.env.stg"
    COMPOSE_FILE="docker-compose.stg.yml"
    echo "Setting up for STAGING environment"
else
    echo "Setting up for DEVELOPMENT environment"
fi

# Check if IP address parameter is provided
if [ -z "$1" ]; then
    # If no IP provided, use the default from the .env file or set a fallback
    IP_ADDRESS=$(grep VITE_API_URL $ENV_FILE | cut -d'=' -f2 | cut -d':' -f1,2 | sed 's/http:\/\///')
    if [ -z "$IP_ADDRESS" ]; then
        if [ "$ENV" == "stg" ]; then
            IP_ADDRESS="192.168.89.132"
        else
            IP_ADDRESS="192.168.102.17"
        fi
    fi
    echo "No IP address provided. Using default: $IP_ADDRESS"
else
    IP_ADDRESS="$1"
    echo "Using provided IP address: $IP_ADDRESS"
    
    # Update the frontend .env file with the new IP
    sed -i "s|VITE_API_URL=http://[^:]*:|VITE_API_URL=http://$IP_ADDRESS:|" $ENV_FILE
    echo "Updated $ENV_FILE with new IP: $IP_ADDRESS"
fi

# Build and start the services
echo "Starting services for $ENV environment with IP: $IP_ADDRESS"
eval $(ssh-agent)
ssh-add ~/.ssh/id_ed25519
echo $SSH_AUTH_SOCK
docker compose -f $COMPOSE_FILE up -d

echo "Services started for $ENV environment:"
if [ "$ENV" == "stg" ]; then
    echo "  - Frontend: http://$IP_ADDRESS:3002"
    echo "  - Backend: http://$IP_ADDRESS:8002"
else
    echo "  - Frontend: http://$IP_ADDRESS:3002"
    echo "  - Backend: http://$IP_ADDRESS:8000"
fi