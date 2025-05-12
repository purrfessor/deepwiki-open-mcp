"""
Main entry point for the DeepWiki MCP Server.
"""

import os
import sys
import logging
from dotenv import load_dotenv
import uvicorn

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler()
    ],
    force=True  # Ensure this configuration takes precedence
)

# Get a logger for this module
logger = logging.getLogger(__name__)

# Add the current directory to the path so we can import modules properly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if __name__ == "__main__":
    # Get port from environment variable or use default
    port = int(os.environ.get("MCP_PORT", 9783))

    # Check for required environment variables
    deepwiki_api_host = os.environ.get("DEEPWIKI_API_HOST")
    if not deepwiki_api_host:
        logger.warning("DEEPWIKI_API_HOST environment variable not set. Using default: http://deepwiki:9781")

    logger.info(f"Starting DeepWiki MCP Server on port {port}")

    # Run the FastAPI app with uvicorn
    uvicorn.run(
        "mcp.server:app",
        host="0.0.0.0",
        port=port,
        reload=False
    )