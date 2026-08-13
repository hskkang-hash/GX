# Build stage
FROM node:18-alpine

# Cài đặt git và ssh client
RUN apk add --no-cache git openssh-client

# Setup SSH for git
RUN mkdir -p /root/.ssh && \
    chmod 700 /root/.ssh

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies với verbose và retry
RUN --mount=type=ssh \
    GIT_SSH_COMMAND="ssh -o StrictHostKeyChecking=no -v" \
    npm install --verbose --legacy-peer-deps

# Copy source code
COPY . .

# Build the application with increased memory limit
RUN NODE_OPTIONS="--max-old-space-size=8192" npm run build

EXPOSE 3002

# Serve the built application using Vite preview
CMD ["npm", "run", "preview"]