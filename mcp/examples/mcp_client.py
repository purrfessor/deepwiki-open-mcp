#!/usr/bin/env python3
"""
Example client for the DeepWiki MCP Server using the official MCP Python SDK.

This example demonstrates how to:
1. Connect to the DeepWiki MCP server using a Streamable HTTP connection
2. Call the query_repository tool to query a repository
3. Handle the response

Usage:
    python mcp_client.py
"""

import asyncio
import argparse
from typing import Dict, Any, List

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


async def main(args: argparse.Namespace):
    """Main function to query the MCP server."""
    # Connect to the MCP server
    server_url = f"http://{args.host}:{args.port}"
    print(f"Connecting to DeepWiki MCP Server at {server_url}...")

    try:
        # Create a streamable HTTP connection to the MCP server
        async with streamablehttp_client(server_url) as (read_stream, write_stream, _):
            # Create a session using the client streams
            async with ClientSession(read_stream, write_stream) as session:
                # Initialize the connection
                await session.initialize()
                print("Connected successfully!")

                # List available tools
                tools = await session.list_tools()
                print(f"\nAvailable tools:")
                for tool in tools:
                    print(f"  - {tool.name}: {tool.description}")

                # Check the health of the DeepWiki API
                if "health_check" in [tool.name for tool in tools]:
                    health_result = await session.call_tool("health_check")
                    print(f"\nHealth check result: {health_result}")
                    if health_result.get("status") != "healthy":
                        print("Warning: DeepWiki API may not be available.")

                # Create arguments for the query_repository tool
                tool_args: Dict[str, Any] = {
                    "repo_url": args.repository,
                    "query": args.query
                }

                # Add optional parameters if provided
                if args.file_path:
                    tool_args["file_path"] = args.file_path

                if args.language:
                    tool_args["language"] = args.language

                if args.access_token:
                    tool_args["access_token"] = args.access_token

                # Example conversation history
                if args.with_history:
                    tool_args["messages"] = [
                        {"role": "user", "content": "What is this repository about?"},
                        {"role": "assistant", "content": "This repository appears to be a project called DeepWiki that automatically creates documentation for code repositories."},
                        {"role": "user", "content": args.query}
                    ]

                print(f"\nQuerying repository: {args.repository}")
                print(f"Query: {args.query}")

                # Call the query_repository tool
                start_time = asyncio.get_event_loop().time()
                result = await session.call_tool("query_repository", tool_args)
                end_time = asyncio.get_event_loop().time()

                print(f"\nResponse (took {end_time - start_time:.2f} seconds):")
                print("=" * 80)
                print(result)
                print("=" * 80)

    except Exception as e:
        print(f"Error: {str(e)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DeepWiki MCP Client Example")
    parser.add_argument("--host", default="localhost", help="MCP server host")
    parser.add_argument("--port", default=9783, type=int, help="MCP server port")
    parser.add_argument("--repository", default="https://github.com/AsyncFuncAI/deepwiki-open",
                        help="Repository URL to query")
    parser.add_argument("--query", default="How do I use the EmbeddingBuilder class?",
                        help="Question to ask about the repository")
    parser.add_argument("--file-path", help="Optional path to a file to provide as context")
    parser.add_argument("--language", default="en", help="Language for the response")
    parser.add_argument("--access-token", help="Access token for private repositories")
    parser.add_argument("--with-history", action="store_true", help="Include example conversation history")

    args = parser.parse_args()

    asyncio.run(main(args))