#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting GuardianX Frontend Setup...${NC}"

# Check Node.js and npm
if ! command -v node &> /dev/null; then
    echo -e "${YELLOW}Node.js is not installed. Installing Node.js...${NC}"
    curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
    sudo apt install -y nodejs
fi

# Check Node.js version
echo -e "${YELLOW}Node.js version:${NC}"
node --version

# Check npm version
echo -e "${YELLOW}npm version:${NC}"
npm --version

# Install dependencies
echo -e "${YELLOW}Installing dependencies...${NC}"
npm install

# Check .env file
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}Creating .env file from .env.example...${NC}"
    cp .env.example .env
    echo -e "${YELLOW}Please update the .env file with your configuration${NC}"
    exit 1
fi

# Start development server
echo -e "${GREEN}Starting development server...${NC}"
npm start 