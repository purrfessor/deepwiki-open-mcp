"""
MCP Server implementation for DeepWiki.
Serves as an interface layer for external AI coding agents.
"""

import os
import logging
import json
import asyncio
from typing import Dict, List, Optional, Union, Any
from enum import Enum

import httpx
from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="DeepWiki MCP Server",
    description="Multi-Agent Communication Protocol (MCP) server for DeepWiki"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

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
    repository: str = Field(..., description="Repository URL or identifier")
    query: str = Field(..., description="Query text")
    messages: Optional[List[ChatMessage]] = Field(None, description="Previous messages in the conversation")
    file_path: Optional[str] = Field(None, description="Optional path to a file to provide as context")
    response_format: Optional[ResponseFormat] = Field(ResponseFormat.MARKDOWN, description="Format of the response")
    stream: Optional[bool] = Field(False, description="Whether to stream the response")
    language: Optional[str] = Field("en", description="Language for the response")
    access_token: Optional[str] = Field(None, description="Access token for private repositories")
    repo_type: Optional[str] = Field("github", description="Repository type (github, gitlab, etc.)")

    # Advanced parameters
    provider: Optional[str] = Field("google", description="Model provider to use")
    model: Optional[str] = Field(None, description="Model to use with the provider")
    excluded_dirs: Optional[str] = Field(None, description="Comma-separated list of directories to exclude")
    excluded_files: Optional[str] = Field(None, description="Comma-separated list of file patterns to exclude")

class StreamChunk(BaseModel):
    """Model for a streaming response chunk."""
    text: str = Field(..., description="Text chunk")
    done: bool = Field(False, description="Whether this is the final chunk")

class QueryResponse(BaseModel):
    """Model for a query response."""
    answer: str = Field(..., description="Answer to the query")
    contexts: Optional[List[str]] = Field(None, description="Context files used for the answer")

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
        messages = []
        if request.messages:
            messages = request.messages
        else:
            # If no messages, create one from the query
            messages = [ChatMessage(role="user", content=request.query)]

        # Prepare the request payload for DeepWiki API
        api_request = {
            "repo_url": request.repository,
            "messages": [{"role": msg.role, "content": msg.content} for msg in messages],
            "filePath": request.file_path,
            "token": request.access_token,
            "type": request.repo_type,
            "provider": request.provider,
            "model": request.model,
            "language": request.language,
            "excluded_dirs": request.excluded_dirs,
            "excluded_files": request.excluded_files
        }

        # Make the API request
        try:
            if request.stream:
                return await self._stream_query(api_request)
            else:
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
        contexts = []

        async with self.http_client.stream("POST", api_url, json=api_request, headers=headers) as response:
            async for chunk in response.aiter_text():
                if chunk:
                    response_text += chunk

        # Parse out any context information if available
        # This is a simplification - context info might not be available in this format

        return QueryResponse(
            answer=response_text,
            contexts=contexts
        )

# Initialize DeepWiki API client
deepwiki_client = DeepWikiClient()

# --- API Endpoints ---

@app.get("/")
async def root():
    """Root endpoint that returns information about the MCP server."""
    return {
        "name": "DeepWiki MCP Server",
        "version": "0.1.0",
        "description": "Multi-Agent Communication Protocol (MCP) server for DeepWiki",
        "endpoints": {
            "GET /": "Service information and health check",
            "GET /health": "Health check for MCP and DeepWiki API",
            "POST /query": "Query the DeepWiki knowledge base",
            "WebSocket /ws/query": "WebSocket endpoint for streaming query responses",
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint that also verifies connectivity to the DeepWiki API."""
    # Check DeepWiki API connectivity
    deepwiki_available = await deepwiki_client.health_check()

    if deepwiki_available:
        return {"status": "healthy", "deepwiki_api": "connected"}
    else:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "deepwiki_api": "disconnected"}
        )

@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """
    Query the DeepWiki knowledge base.

    Args:
        request: The query request

    Returns:
        QueryResponse: The answer to the query
    """
    if request.stream:
        # For streaming responses, return a StreamingResponse
        return await deepwiki_client.query(request)
    else:
        # For non-streaming responses, return a QueryResponse
        return await deepwiki_client.query(request)

@app.websocket("/ws/query")
async def websocket_query(websocket: WebSocket):
    """
    WebSocket endpoint for streaming query responses.

    The client should send a JSON-encoded QueryRequest with stream=True.
    """
    await websocket.accept()

    try:
        # Receive QueryRequest as JSON
        request_json = await websocket.receive_text()
        request_data = json.loads(request_json)
        request = QueryRequest(**request_data)

        # Force streaming for WebSocket
        request.stream = True

        # Create a DeepWiki API request
        messages = []
        if request.messages:
            messages = request.messages
        else:
            # If no messages, create one from the query
            messages = [ChatMessage(role="user", content=request.query)]

        # Prepare the request payload for DeepWiki API
        api_request = {
            "repo_url": request.repository,
            "messages": [{"role": msg.role, "content": msg.content} for msg in messages],
            "filePath": request.file_path,
            "token": request.access_token,
            "type": request.repo_type,
            "provider": request.provider,
            "model": request.model,
            "language": request.language,
            "excluded_dirs": request.excluded_dirs,
            "excluded_files": request.excluded_files
        }

        # Make the streaming API request
        try:
            api_url = f"{DEEPWIKI_API_HOST}/chat/completions/stream"
            headers = {"Content-Type": "application/json"}

            # Use httpx to make a streaming request
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream("POST", api_url, json=api_request, headers=headers) as response:
                    response_text = ""

                    async for chunk in response.aiter_text():
                        if chunk:
                            # Update the accumulated response
                            response_text += chunk

                            # Send the chunk as a StreamChunk
                            await websocket.send_json({
                                "text": chunk,
                                "done": False
                            })

                    # Send the final chunk
                    await websocket.send_json({
                        "text": "",
                        "done": True
                    })

        except Exception as e:
            logger.error(f"Error streaming response from DeepWiki API: {str(e)}")
            await websocket.send_json({
                "error": str(e),
                "done": True
            })

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")

    except Exception as e:
        logger.error(f"Error in WebSocket connection: {str(e)}")
        try:
            await websocket.send_json({
                "error": str(e),
                "done": True
            })
        except:
            pass

# Application lifecycle events

@app.on_event("startup")
async def startup_event():
    """Application startup event handler."""
    logger.info("MCP Server starting up")

    # Check DeepWiki API connectivity
    deepwiki_available = await deepwiki_client.health_check()
    if deepwiki_available:
        logger.info("Successfully connected to DeepWiki API")
    else:
        logger.warning("Could not connect to DeepWiki API. Some functionality may be unavailable.")

@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event handler."""
    logger.info("MCP Server shutting down")
    await deepwiki_client.close()