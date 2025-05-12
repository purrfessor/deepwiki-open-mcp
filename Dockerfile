# syntax=docker/dockerfile:1-labs

FROM node:20-alpine AS node_base

FROM node_base AS node_deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --legacy-peer-deps

FROM node_base AS node_builder
WORKDIR /app
COPY --from=node_deps /app/node_modules ./node_modules
COPY --exclude=./api . .
# Set port explicitly for Next.js build
ENV PORT=9782
RUN NODE_ENV=production npm run build

FROM python:3.11-slim AS py_deps
WORKDIR /app
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY api/requirements.txt ./api/
RUN pip install --no-cache -r api/requirements.txt

# Use Python 3.11 as final image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install Node.js and npm
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    git \
    && mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list \
    && apt-get update \
    && apt-get install -y nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

ENV PATH="/opt/venv/bin:$PATH"

# Copy Python dependencies
COPY --from=py_deps /opt/venv /opt/venv
COPY api/ ./api/

# Copy Node app
COPY --from=node_builder /app/public ./public
COPY --from=node_builder /app/.next/standalone ./
COPY --from=node_builder /app/.next/static ./.next/static

# Expose the port the app runs on
EXPOSE 9781 9782

# Create a script to run both backend and frontend
RUN echo '#!/bin/bash\n\
set -e # Exit immediately if a command exits with a non-zero status.\n\
# Source .env file if it exists\n\
if [ -f .env ]; then\n\
  export $(grep -v "^#" .env | xargs -r)\n\
fi\n\
\n\
# Print environment variables for debugging\n\
echo "Starting DeepWiki with the following configuration:"\n\
echo "API PORT (deepwiki python backend): ${PORT:-9781}"\n\
echo "NEXT.JS PORT (deepwiki frontend): ${NEXT_PUBLIC_PORT:-9782}"\n\
echo "SERVER_BASE_URL (for Next.js to call API): ${SERVER_BASE_URL:-http://localhost:9781}"\n\
\n\
# Check for required environment variables\n\
if [ -z "$OPENAI_API_KEY" ] || [ -z "$GOOGLE_API_KEY" ]; then\n\
  echo "Warning: OPENAI_API_KEY and/or GOOGLE_API_KEY environment variables are not set."\n\
  echo "DeepWiki may not function correctly without them."\n\
fi\n\
\n\
# Start the API server in the background with the configured port\n\
echo "Starting API server on port 9781..."\n\
python -m api.main --port 9781 &\n\
\n\
# Wait for API to be available\n\
echo "Waiting for API to be available..."\n\
until curl -sf http://localhost:9781/ > /dev/null; do\n\
  echo -n "."\n\
  sleep 1\n\
done\n\
echo "API is up and running."\n\
\n\
# Start Next.js with explicit port configuration\n\
echo "Starting Next.js server on port 9782..."\n\
export PORT=9782 # Next.js standalone server listens to this PORT env var\n\
export HOSTNAME=0.0.0.0 # Listen on all interfaces\n\
# SERVER_BASE_URL is already set from .env or Dockerfile ENV, needed by the Next.js app at runtime\n\
node server.js &\n\
\n\
# Wait for any child process to exit\n\
wait -n\n\
exit $?' > /app/start.sh && chmod +x /app/start.sh

# Set environment variables
ENV PORT=9781
ENV NEXT_PUBLIC_PORT=9782
ENV NODE_ENV=production
ENV SERVER_BASE_URL=http://localhost:9781

# Create empty .env file (will be overridden if one exists at runtime)
RUN touch .env

# Install curl for healthcheck
RUN apt-get update && apt-get install -y curl && apt-get clean && rm -rf /var/lib/apt/lists/*

# Command to run the application
CMD ["/app/start.sh"]
