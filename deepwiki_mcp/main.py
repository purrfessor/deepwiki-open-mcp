"""
Main entry point for the DeepWiki MCP Server.
"""

import json
import logging
import os
import sys
from enum import Enum
from typing import Dict, List, Optional, Union, Any

import httpx
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from mcp.server import FastMCP
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="DeepWiki MCP Server",
    description="Multi-Agent Communication Protocol (MCP) server for DeepWiki"
)

mcp = FastMCP(name="DeepWikiMCP", log_level="INFO", host="0.0.0.0", stateless_http=True, port=9783)

# Constants
DEEPWIKI_API_HOST = os.environ.get("DEEPWIKI_API_HOST", "http://deepwiki:9781")

# --- Pydantic Models ---

class ResponseFormat(str, Enum):
    """Response format options."""
    JSON = "json"
    TEXT = "text"
    MARKDOWN = "markdown"

class ChatMessage(BaseModel):
    """Model for a chat message."""
    role: str = Field(..., description="Role of the message sender, either 'user' or 'assistant'")
    content: str = Field(..., description="Content of the message")

class QueryRequest(BaseModel):
    """Model for a query request to the MCP server."""
    repository: str = Field(..., description="Repository URL or identifier. For example https://github.com/agno-agi/agno")
    query: str = Field(..., description="Query text. For example \"How does agno BrowserBase integration work?\"")
    messages: Optional[List[ChatMessage]] = Field(None, description="Previous messages in the conversation.")
    response_format: Optional[ResponseFormat] = Field(ResponseFormat.MARKDOWN, description="Format of the response.")
    language: Optional[str] = Field("en", description="Language for the response.")
    repo_type: Optional[str] = Field("github", description="Repository type (github, gitlab, etc.)")

    # Advanced parameters
    provider: Optional[str] = Field("google", description="Model provider to use.")
    model: Optional[str] = Field("gemini-2.5-pro-preview-05-06", description="Model to use with the provider.")
    excluded_dirs: Optional[str] = Field(None, description="Comma-separated list of directories to exclude.")
    excluded_files: Optional[str] = Field(None, description="Comma-separated list of file patterns to exclude.")

class StreamChunk(BaseModel):
    """Model for a streaming response chunk."""
    text: str = Field(..., description="Text chunk")
    done: bool = Field(False, description="Whether this is the final chunk")

class QueryResponse(BaseModel):
    """Model for a query response."""
    answer: str = Field(..., description="Answer to the query")

# --- MCP API Client for DeepWiki ---

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

    async def query(self, request: QueryRequest) -> Union[StreamingResponse, QueryResponse]:
        """
        Query the DeepWiki API for an answer.

        Args:
            request: The query request

        Returns:
            Either a StreamingResponse for streaming responses or a QueryResponse for non-streaming responses
        """
        # Convert QueryRequest to DeepWiki API format


        # Prepare the request payload for DeepWiki API
        api_request = {
            "repo_url": request.repository,
            "type": request.repo_type,
            "language": request.language,
            "excluded_dirs": request.excluded_dirs,
            "excluded_files": request.excluded_files
        }

        # Make the API request
        try:
            # if request.stream:
            # return await self._stream_query(api_request)
            # else:
            return await self._direct_query(api_request)
        except Exception as e:
            logger.error(f"Error querying DeepWiki API: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error querying DeepWiki API: {str(e)}")

    async def _stream_query(self, api_request: Dict[str, Any]) -> StreamingResponse:
        """Process a streaming query to the DeepWiki API."""

        async def response_stream():
            try:
                api_url = f"{self.base_url}/chat/completions/stream"
                headers = {"Content-Type": "application/json"}

                # Use the HTTP client to make a streaming request
                async with self.http_client.stream("POST", api_url, json=api_request, headers=headers) as response:
                    async for chunk in response.aiter_text():
                        if chunk:
                            yield chunk
            except Exception as e:
                logger.error(f"Error streaming response from DeepWiki API: {str(e)}")
                yield json.dumps({"error": str(e)})

        return StreamingResponse(response_stream(), media_type="text/event-stream")

    async def _direct_query(self, api_request: Dict[str, Any]) -> QueryResponse:
        """Process a direct (non-streaming) query to the DeepWiki API."""
        api_url = f"{self.base_url}/chat/completions/stream"
        headers = {"Content-Type": "application/json"}

        # For direct queries, we still need to handle streaming responses from the API
        response_text = ""

        async with self.http_client.stream("POST", api_url, json=api_request, headers=headers) as response:
            async for chunk in response.aiter_text():
                if chunk:
                    response_text += chunk

        # Parse out any context information if available
        # This is a simplification - context info might not be available in this format

        return QueryResponse(
            answer=response_text
        )

# Initialize DeepWiki API client
deepwiki_client = DeepWikiClient()

@mcp.tool(
    name="AskDeepWiki",
    description="Ask questions about code repositories using DeepWiki: a tool that generates embeddings from the repository code and provides an AI agent chatting interface for asking questions about the codebase."
)
async def ask_deepwiki(
        repository: str,
        query: str,
        repo_type: str = "github",
        language: str = "en",
        excluded_dirs: Optional[str] = None,
        excluded_files: Optional[str] = None,
        stream: bool = False
) -> Union[StreamingResponse, QueryResponse]:
    """
    Ask DeepWiki questions about repositories.

    Args:
        repository: Repository URL or identifier
        query: Question to ask about the repository
        repo_type: Repository type (github, gitlab, etc.)
        language: Language for the response
        excluded_dirs: Comma-separated list of directories to exclude
        excluded_files: Comma-separated list of file patterns to exclude
        stream: Whether to stream the response

    Returns:
        Either a StreamingResponse or QueryResponse containing DeepWiki's answer
    """
    logger.info(f"DeepWiki query for repository: {repository}")

    # Create a QueryRequest with the provided parameters
    request = QueryRequest(
        repository=repository,
        query=query,
        repo_type=repo_type,
        language=language,
        excluded_dirs=excluded_dirs,
        excluded_files=excluded_files,
    )

    # Query the DeepWiki API
    response = await deepwiki_client.query(request)
    return response

# Load environment variables from .env file
load_dotenv()

# Add the current directory to the path so we can import modules properly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if __name__ == "__main__":
    mcp.run(transport="sse")