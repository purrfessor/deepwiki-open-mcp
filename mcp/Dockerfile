FROM python:3.10-slim

WORKDIR /app

# Install curl and necessary tools
RUN apt-get update && apt-get install -y curl && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy only the requirements file first for better caching
COPY mcp/requirements.txt /app/mcp/

# Install dependencies
RUN pip install --no-cache-dir -r /app/mcp/requirements.txt

# Copy the project code
COPY . .

# Create a startup script with retry logic
RUN echo '#!/bin/bash\n\
echo "Starting MCP server with the following configuration:"\n\
echo "MCP_PORT: ${MCP_PORT:-9783}"\n\
echo "DEEPWIKI_API_HOST: ${DEEPWIKI_API_HOST:-http://deepwiki:8001}"\n\
\n\
# Wait for DeepWiki API to be available\n\
echo "Waiting for DeepWiki API to be available at ${DEEPWIKI_API_HOST}..."\n\
MAX_RETRIES=30\n\
RETRY_COUNT=0\n\
\n\
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do\n\
  if curl -s "${DEEPWIKI_API_HOST}" > /dev/null; then\n\
    echo "DeepWiki API is available!"\n\
    break\n\
  fi\n\
  echo "Attempt $((RETRY_COUNT+1))/$MAX_RETRIES: DeepWiki API not yet available. Retrying in 2 seconds..."\n\
  RETRY_COUNT=$((RETRY_COUNT+1))\n\
  sleep 2\n\
done\n\
\n\
if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then\n\
  echo "Warning: Could not connect to DeepWiki API after $MAX_RETRIES attempts."\n\
  echo "The MCP server will still start, but some functionality may be unavailable."\n\
fi\n\
\n\
# Start the MCP server\n\
echo "Starting MCP server on port ${MCP_PORT:-9783}..."\n\
python -m mcp.main\n' > /app/start-mcp.sh && chmod +x /app/start-mcp.sh

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV MCP_PORT=8003
ENV DEEPWIKI_API_HOST=http://deepwiki:8001

# Expose the port
EXPOSE 9783

# Run the server with the startup script
CMD ["/app/start-mcp.sh"]