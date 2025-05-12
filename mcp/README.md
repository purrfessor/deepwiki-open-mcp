# DeepWiki MCP Server

Multi-Agent Communication Protocol (MCP) server for DeepWiki, providing an interface for external AI coding agents to interact with DeepWiki's RAG system.

## Overview

The DeepWiki MCP server serves as an intermediary between external AI coding agents (like Cursor) and DeepWiki's RAG-based knowledge retrieval system. It implements the [Model Context Protocol](https://github.com/modelcontextprotocol/python-sdk) standard for AI agent communication and provides a clean API for agents to:

- Ask context-aware questions about a repository
- Receive answers powered by DeepWiki's RAG system
- Maintain conversation history for multi-turn interactions

## MCP Implementation

The server exposes a single primary tool through the Model Context Protocol:

### `query_repository` Tool

This tool allows agents to query a repository about code, usage patterns, implementation details, etc.

**Parameters:**

| Parameter       | Type    | Description                                                 | Required |
|-----------------|---------|-------------------------------------------------------------|----------|
| repo_url        | string  | Repository URL or identifier                                | Yes      |
| query           | string  | The question to ask about the repository                    | Yes      |
| file_path       | string  | Optional path to a file to provide as context               | No       |
| messages        | array   | Previous conversation messages for multi-turn interactions  | No       |
| repo_type       | string  | Repository type (github, gitlab, etc.)                      | No       |
| language        | string  | Language for the response (default: en)                     | No       |
| provider        | string  | Model provider to use (google, openai, etc.)                | No       |
| model           | string  | Model to use with the provider                              | No       |
| access_token    | string  | Access token for private repositories                       | No       |
| excluded_dirs   | string  | Comma-separated list of directories to exclude              | No       |
| excluded_files  | string  | Comma-separated list of file patterns to exclude            | No       |

### Additional Tools

The server also provides a health check tool:

- `health_check`: Verifies connectivity to the DeepWiki API

## MCP Client Examples

The MCP server can be accessed using any MCP-compatible client. An example Python client is provided in the `examples` directory:

```python
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

async def query_repository():
    async with streamablehttp_client("http://localhost:9783") as (read, write, _):
        async with ClientSession(read, write) as session:
            # Initialize the connection
            await session.initialize()

            # Call the query_repository tool
            result = await session.call_tool("query_repository", {
                "repo_url": "https://github.com/AsyncFuncAI/deepwiki-open",
                "query": "How does the repository structure work?",
                "language": "en"
            })

            print(result)
```

For a complete example, see `examples/mcp_client.py`.

## Environment Variables

| Variable           | Default               | Description                       |
|--------------------|------------------------|-----------------------------------|
| MCP_PORT           | 9783                   | Port for the MCP server          |
| DEEPWIKI_API_HOST  | http://deepwiki:9781   | URL of the DeepWiki API          |

## Deployment

The MCP server is designed to run alongside DeepWiki in a Docker Compose setup. See the project's docker-compose.yml file for details.