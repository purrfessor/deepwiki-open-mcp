"""
Main entry point for the DeepWiki MCP Server.
"""

import json
import logging
import os
from enum import Enum
from typing import Dict, List, Optional, Union, Any

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from mcp.server import FastMCP
from mcp.server.session import ServerSession
from pydantic import BaseModel, Field
import socket

logger = logging.getLogger(__name__)

# Patch for handling "Received request before initialization was complete" error
# This works around an issue where clients (like Cursor) send requests before initialization
original_received_request = ServerSession._received_request
async def patched_received_request(self, *args, **kwargs):
    try:
        return await original_received_request(self, *args, **kwargs)
    except RuntimeError as e:
        if "Received request before initialization was complete" in str(e):
            logger.warning("Received request before initialization was complete, handling gracefully")
            # Just pass to avoid the error, the client will need to retry or timeout
            pass
        else:
            # Re-raise other RuntimeErrors
            raise

# Apply the patch
ServerSession._received_request = patched_received_request

# Initialize FastAPI app
app = FastAPI(
    title="DeepWiki MCP Server",
    description="Multi-Agent Communication Protocol (MCP) server for DeepWiki"
)

mcp = FastMCP(name="DeepWikiMCP", log_level="INFO", host="0.0.0.0", port=9783)

# Constants
# Try to resolve the deepwiki hostname
try:
    # Try to resolve the Docker hostname
    socket.gethostbyname('deepwiki')
    DEEPWIKI_API_HOST = os.environ.get("DEEPWIKI_API_HOST", "http://deepwiki:9781")
    logger.info(f"Using Docker hostname: {DEEPWIKI_API_HOST}")
except socket.gaierror:
    # Fall back to localhost if hostname resolution fails
    DEEPWIKI_API_HOST = os.environ.get("DEEPWIKI_API_HOST", "http://localhost:9781")
    logger.info(f"Using localhost: {DEEPWIKI_API_HOST}")

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
    repository: str = Field(...,
                            description="Repository URL or identifier. For example https://github.com/agno-agi/agno")
    query: str = Field(...,
                       description="Query text. For example \"How does agno BrowserBase integration work?\"")
    deep_research: bool = Field(False, description="Whether to conduct a deep research or not.")
    messages: Optional[List[ChatMessage]] = Field(None, description="Previous messages in the conversation.")
    response_format: Optional[ResponseFormat] = Field(ResponseFormat.MARKDOWN, description="Format of the response.")
    language: Optional[str] = Field("en", description="Language for the response.")
    repo_type: Optional[str] = Field("github", description="Repository type (github, gitlab, etc.)")

    # Advanced parameters
    provider: Optional[str] = Field("google", description="Model provider to use.")
    model: Optional[str] = Field("gemini-2.5-pro-preview-05-06", description="Model to use with the provider.")

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
        self.http_client = httpx.AsyncClient(timeout=300.0)

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

    async def query(self, request: QueryRequest) -> str:
        """
        Query the DeepWiki API for an answer.

        Args:
            request: The query request

        Returns:
            String containing DeepWiki's answer
        """

        # Create a simple dict without Pydantic models
        messages_for_api = [
            {
                "role": "user",
                "content": f"[DEEP RESEARCH] {request.query}" if request.deep_research else f"{request.query}"
            }
        ]

        # Prepare the request payload for DeepWiki API using plain dictionaries
        api_request = {
            "repo_url": request.repository,
            "type": request.repo_type,
            "language": request.language,
            "messages": messages_for_api  # This is explicitly List[Dict[str, str]]
        }

        logger.info(f"DeepWikiClient: Preparing to send api_request. Structure:")
        for key, value in api_request.items():
            value_repr = str(value)[:200] # Truncate long values for logging
            logger.info(f"  api_request['{key}']: type={type(value)}, value='{value_repr}'")
            if isinstance(value, list):
                for i, item in enumerate(value):
                    item_repr = str(item)[:200]
                    logger.info(f"    api_request['{key}'][{i}]: type={type(item)}, value='{item_repr}'")
            elif isinstance(value, dict):
                 for sub_key, sub_value in value.items():
                    sub_value_repr = str(sub_value)[:200]
                    logger.info(f"    api_request['{key}']['{sub_key}']: type={type(sub_value)}, value='{sub_value_repr}'")

        # Make the API request
        try:
            return await self._stream_query(api_request)
        except Exception as e:
            error_msg = f"Error querying DeepWiki API: {str(e)}"
            logger.error(error_msg)
            return error_msg

    async def _stream_query(self, api_request: Dict[str, Any]) -> str:
        """Process a streaming query to the DeepWiki API and collect the full response."""
        try:
            api_url = f"{self.base_url}/chat/completions/stream"
            headers = {"Content-Type": "application/json"}

            # Use the HTTP client to make a streaming request and collect all chunks
            full_response = ""
            async with self.http_client.stream("POST", api_url, json=api_request, headers=headers) as response:
                async for chunk in response.aiter_text():
                    if chunk:
                        # Some APIs send data in JSON format even in streams
                        try:
                            # Try to parse as JSON
                            parsed = json.loads(chunk)
                            if 'text' in parsed:
                                full_response += parsed['text']
                            elif 'content' in parsed:
                                full_response += parsed['content']
                            elif 'delta' in parsed and 'content' in parsed['delta']:
                                full_response += parsed['delta']['content']
                            else:
                                full_response += str(parsed)
                        except json.JSONDecodeError:
                            # Just append as raw text
                            full_response += chunk

            logger.info(f"Collected full response of length: {len(full_response)}")
            return full_response
        except Exception as e:
            error_msg = f"Error streaming response from DeepWiki API: {str(e)}"
            logger.error(error_msg)
            return error_msg

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
        repository: str = Field(..., description="Repository URL or GitHub repo name (e.g., 'agno-agi/agno')"),
        query: str = Field(..., description="Your question about the repository"),
        repo_type: str = Field(default="github", description="Repository type (github, gitlab, etc.)"),
        language: str = Field(default="en", description="Language for the response"),
        deep_research: bool = Field(default=False, description="Enable deeper, more thorough analysis")
) -> str:
    """
    Ask DeepWiki questions about repositories.

    Args:
        repository: Repository URL or identifier
        query: Question to ask about the repository
        repo_type: Repository type (github, gitlab, etc.)
        language: Language for the response
        deep_research: Whether to conduct a deep research or not

    Returns:
        String containing DeepWiki's answer
    """
    logger.info(f"DeepWiki query for repository: {repository}")

    request_obj = QueryRequest(
        repository=repository,
        query=query,
        repo_type=repo_type,
        language=language,
        deep_research=deep_research
    )

    # Query the DeepWiki API
    response = await deepwiki_client.query(request_obj)
    return response


if __name__ == "__main__":
    mcp.run(transport="sse")
