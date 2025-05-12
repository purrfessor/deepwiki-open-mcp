"""
DeepWiki MCP Server implementation using the Model Context Protocol SDK.
This simplified version provides a single method to query the DeepWiki API's chat_completions_stream endpoint.
"""

import os
import logging
import httpx
from typing import Dict, List, Optional, Any

from mcp.server.fastmcp import FastMCP

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
DEEPWIKI_API_HOST = os.environ.get("DEEPWIKI_API_HOST", "http://deepwiki:9781")

class DeepWikiClient:
    """Client for communicating with the DeepWiki API."""

    def __init__(self, base_url: str = DEEPWIKI_API_HOST):
        """Initialize the client with the DeepWiki API host."""
        self.base_url = base_url
        self.http_client = httpx.AsyncClient(timeout=60.0)

    async def close(self):
        """Close the HTTP client."""
        await self.http_client.aclose()

    async def health_check(self) -> bool:
        """Check if the DeepWiki API is available."""
        try:
            response = await self.http_client.get(f"{self.base_url}/")
            if response.status_code == 200:
                return True
            logger.warning(f"DeepWiki API health check failed with status {response.status_code}")
            return False
        except Exception as e:
            logger.error(f"Error connecting to DeepWiki API: {str(e)}")
            return False

    async def query_repository(
        self,
        repo_url: str,
        query: str,
        messages: Optional[List[Dict[str, str]]] = None,
        file_path: Optional[str] = None,
        repo_type: str = "github",
        provider: str = "google",
        model: Optional[str] = None,
        language: str = "en",
        access_token: Optional[str] = None,
        excluded_dirs: Optional[str] = None,
        excluded_files: Optional[str] = None
    ) -> str:
        """
        Query the DeepWiki API about a repository using the chat_completions_stream endpoint.

        Args:
            repo_url: Repository URL or identifier
            query: The question to ask
            messages: Previous conversation messages
            file_path: Path to a file to provide as context
            repo_type: Repository type (github, gitlab, etc.)
            provider: Model provider to use
            model: Model to use with the provider
            language: Language for the response
            access_token: Access token for private repositories
            excluded_dirs: Comma-separated list of directories to exclude
            excluded_files: Comma-separated list of file patterns to exclude

        Returns:
            The response from the DeepWiki API
        """
        if messages is None:
            messages = [{"role": "user", "content": query}]

        api_request = {
            "repo_url": repo_url,
            "messages": messages,
            "filePath": file_path,
            "token": access_token,
            "type": repo_type,
            "provider": provider,
            "model": model,
            "language": language,
            "excluded_dirs": excluded_dirs,
            "excluded_files": excluded_files
        }

        try:
            api_url = f"{self.base_url}/chat/completions/stream"
            headers = {"Content-Type": "application/json"}

            response_text = ""

            # For direct queries, we accumulate streaming responses
            async with self.http_client.stream("POST", api_url, json=api_request, headers=headers) as response:
                async for chunk in response.aiter_text():
                    if chunk:
                        response_text += chunk

            return response_text
        except Exception as e:
            logger.error(f"Error querying DeepWiki API: {str(e)}")
            raise Exception(f"Error querying DeepWiki API: {str(e)}")

# Initialize FastMCP server
deepwiki_mcp = FastMCP("DeepWiki")

# Initialize DeepWiki API client
deepwiki_client = DeepWikiClient()

@deepwiki_mcp.tool()
async def query_repository(
    repo_url: str,
    query: str,
    file_path: Optional[str] = None,
    messages: Optional[List[Dict[str, str]]] = None,
    repo_type: str = "github",
    language: str = "en",
    provider: str = "google",
    model: Optional[str] = None,
    access_token: Optional[str] = None,
    excluded_dirs: Optional[str] = None,
    excluded_files: Optional[str] = None
) -> str:
    """
    Query a repository using DeepWiki's chat_completions_stream endpoint.

    This is the main method for interacting with DeepWiki's RAG system.

    Args:
        repo_url: The repository URL or identifier
        query: The question to ask about the repository
        file_path: Optional path to a file to provide as context
        messages: Optional previous messages in the conversation
        repo_type: Repository type (github, gitlab, etc.)
        language: Language for the response (default: en)
        provider: Model provider to use
        model: Model to use with the provider
        access_token: Access token for private repositories
        excluded_dirs: Comma-separated list of directories to exclude
        excluded_files: Comma-separated list of file patterns to exclude

    Returns:
        Answer to the query about the repository
    """
    try:
        response = await deepwiki_client.query_repository(
            repo_url=repo_url,
            query=query,
            messages=messages,
            file_path=file_path,
            repo_type=repo_type,
            provider=provider,
            model=model,
            language=language,
            access_token=access_token,
            excluded_dirs=excluded_dirs,
            excluded_files=excluded_files
        )
        return response
    except Exception as e:
        logger.error(f"Error querying repository: {str(e)}")
        return f"Error: {str(e)}"

@deepwiki_mcp.tool()
async def health_check() -> Dict[str, Any]:
    """
    Check the health of the DeepWiki API.

    Returns:
        Health status information
    """
    try:
        deepwiki_available = await deepwiki_client.health_check()

        if deepwiki_available:
            return {"status": "healthy", "deepwiki_api": "connected"}
        else:
            return {"status": "unhealthy", "deepwiki_api": "disconnected"}
    except Exception as e:
        logger.error(f"Error checking health: {str(e)}")
        return {"status": "error", "message": str(e)}

# Application lifecycle management
@deepwiki_mcp.on_startup
async def on_startup():
    """Handler for startup events."""
    logger.info("DeepWiki MCP Server starting up")

    # Check DeepWiki API connectivity
    try:
        deepwiki_available = await deepwiki_client.health_check()
        if deepwiki_available:
            logger.info("Successfully connected to DeepWiki API")
        else:
            logger.warning("Could not connect to DeepWiki API. Some functionality may be unavailable.")
    except Exception as e:
        logger.error(f"Error during startup: {str(e)}")

@deepwiki_mcp.on_shutdown
async def on_shutdown():
    """Handler for shutdown events."""
    logger.info("DeepWiki MCP Server shutting down")
    await deepwiki_client.close()

# Create FastAPI app
app = deepwiki_mcp.app