# DeepWiki MCP Server

![DeepWiki Banner](../screenshots/Deepwiki.png)

DeepWiki MCP Server provides a [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) interface for DeepWiki, allowing AI agents like Cursor to interact with repository knowledge through a standardized protocol.

## 🚀 Introduction

The DeepWiki MCP Server exposes DeepWiki's repository analysis capabilities to AI agents through the Model Context Protocol. This allows tools like Cursor, Claude Desktop, and other MCP-compatible AI agents to:

- Ask questions about any code repository
- Get context-aware answers about repository structure, components, and functionality
- Access DeepWiki's knowledge directly from your coding environment

## 📋 Installation & Setup

### Option 1: Using Docker (Recommended)

The easiest way to run the DeepWiki MCP Server is using Docker Compose:

```bash
# Clone the repository
git clone https://github.com/AsyncFuncAI/deepwiki-open.git
cd deepwiki-open

# Create a .env file with your API keys
echo "GOOGLE_API_KEY=your_google_api_key" > .env
echo "OPENAI_API_KEY=your_openai_api_key" >> .env
# Optional: Add OpenRouter API key if you want to use OpenRouter models
echo "OPENROUTER_API_KEY=your_openrouter_api_key" >> .env

# Run with Docker Compose (includes DeepWiki and MCP server)
docker-compose up
```

With Docker Compose, the MCP server will be available at http://localhost:9783/sse.

### Option 2: Manual Setup

For development or customization, you can run the MCP server directly:

```bash
# Install Python dependencies
pip install -r deepwiki_mcp/requirements.txt

# Start the DeepWiki API first (required for the MCP server)
python -m api.main

# In a separate terminal, start the MCP server
python -m deepwiki_mcp.main
```

The MCP server will be available at http://localhost:9783/sse by default.

## ⚙️ Configuration

### Environment Variables

The MCP server can be configured using the following environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `MCP_PORT` | Port for the MCP server | `9783` |
| `DEEPWIKI_API_HOST` | URL of the DeepWiki API | `http://localhost:9781` (when running locally) or `http://deepwiki:9781` (in Docker) |

### Server Modes

The MCP server supports various transport modes:

- **Server-Sent Events (SSE)**: The default mode, accessible at `/sse`. Used for web clients.
- **Standard I/O (stdio)**: Used for direct integration with tools like Claude Desktop.

## 🔌 Configuring AI Tools

### Configuring Cursor

To use DeepWiki MCP with Cursor:

1. In Cursor, open settings (`Cmd+,` on Mac, `Ctrl+,` on Windows/Linux)
2. Go to "Integrations" > "MCP Servers"
3. Add a new MCP server with the following configuration:
```json
{
  "mcpServers": {
    "deepwiki": {
      "url": "http://localhost:9783/sse",
      "method": "GET",
      "description": "DeepWiki MCP server for code repository analysis",
      "tools": {
        "AskDeepWiki": {
          "description": "Ask questions about code repositories",
          "required_params": ["repository", "query"],
          "optional_params": ["repo_type", "language", "deep_research"]
        }
      }
    }
  }
}
```
4. To test the connection, ask Cursor a question about a repository, like: "Using DeepWiki, can you explain how the agno-agi/agno repository works?"

### Adding to Cursor User Rule

To enable AI assistants to use DeepWiki MCP effectively, add the following to your [Cursor User Rule](https://docs.cursor.com/context/rules):

```
# MCP
Here is a list of available MCPs and what to use them for.

## deepwiki
Use deepwiki MCP to chat with an AI agent that is built with RAG on top of a repository code embeddings, meaning this agent knows everything about the code of the repository and can provide answers to questions like "how to implement a feature like N using this library?", "how does a class N work?", etc.
Don't use deep research by default, but if you already tried regular questions and it didn't help to solve the problem, or if you're implementing a huge feature, use the deep research.
```

This tells the AI assistant when and how to use the DeepWiki MCP in the most effective way.

## 🧰 Tools Reference

The MCP server provides the following tools:

### `AskDeepWiki`

Ask questions about any code repository and get accurate, context-aware answers.

#### Parameters:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `repository` | string | Yes | Repository URL or GitHub repo name (e.g., "agno-agi/agno") |
| `query` | string | Yes | Your question about the repository |
| `repo_type` | string | No | Repository type (github, gitlab, etc.). Default: "github" |
| `language` | string | No | Language for the response. Default: "en" |
| `deep_research` | boolean | No | Enable deeper, more thorough analysis. Default: false |

#### Example Request/Response:

**Request:**
```json
{
  "repository": "agno-agi/agno",
  "query": "How do I use the AgnoAgent to generate responses? What's the correct way to call generate method and receive a response?"
}
```

**Response:**
```
To generate responses using the `AgnoAgent`, you can use the `run` or `print_response` methods.

*   **Using the `run` method:**

    ```python
    from agno.agent import Agent, RunResponse
    from agno.models.openai import OpenAI

    agent = Agent(model=OpenAI(id="gpt-4o"), markdown=True)

    run: RunResponse = agent.run("Share a 2 sentence horror story")
    print(run.content)
    ```

    This method returns a `RunResponse` object, which contains the generated content.

*   **Using the `print_response` method:**

    ```python
    from agno.agent import Agent
    from agno.models.openai import OpenAI

    agent = Agent(model=OpenAI(id="gpt-4o"), markdown=True)

    agent.print_response("Share a 2 sentence horror story")
    ```

    This method directly prints the response to the terminal.

*   **Streaming responses:**

    For streaming responses, use the `run` method with `stream=True`:

    ```python
    from agno.agent import Agent, RunResponse
    from agno.models.openai import OpenAI

    agent = Agent(model=OpenAI(id="gpt-4o"), markdown=True)

    run_response = agent.run("Share a 2 sentence horror story", stream=True)
    for chunk in run_response:
        print(chunk.content)
    ```

    Or, use the `print_response` method with `stream=True`:

    ```python
    from agno.agent import Agent
    from agno.models.openai import OpenAI

    agent = Agent(model=OpenAI(id="gpt-4o"), markdown=True)

    agent.print_response("Share a 2 sentence horror story", stream=True)
    ```
```

## 🔍 Usage Scenarios

### Scenario 1: Understanding New Repositories

When working with an unfamiliar codebase, you can ask DeepWiki for an overview:

**Request:**
```json
{
  "repository": "langchain-ai/langchain",
  "query": "Explain the overall architecture of this repository"
}
```

**Response:**
```
LangChain is organized into several key packages:

1. **Core Architecture (langchain-core):**
   - Defines base abstractions like Language Models, Output Parsers, and Retrievers
   - Implements the Runnable protocol for uniform calling interface
   - Provides standard messaging schemas and runtime tracing

2. **Integrations (langchain):**
   - Model integrations (OpenAI, Anthropic, etc.)
   - Vector store integrations (Chroma, Pinecone, etc.)
   - Data loaders and document transformers

3. **Templates (langchain-templates):**
   - Ready-to-use patterns for common LLM applications
   - Standardized project structures

The architecture follows a modular design with clean separation between:
- Abstract interfaces (defined in core)
- Concrete implementations (in integration packages)
- Composition patterns (chains, agents, retrievers)

This allows for easy swapping of components while maintaining a consistent interface.
```

### Scenario 2: Finding Implementation Details

Need to understand how specific functionality is implemented:

**Request:**
```json
{
  "repository": "agno-agi/agno",
  "query": "How is the BrowserBase toolkit implemented? Show me the core implementation details."
}
```

**Response:**
```
The BrowserBase toolkit in the Agno framework provides a foundation for browser-based interactions. Here's the core implementation:

The `BrowserBase` class is defined in `agno/tools/browser_base.py` and serves as a base for browser automation:

```python
class BrowserBase(BaseTool):
    """Base class for browser tools."""

    base: Optional[BaseBrowser] = None

    def setup(self, base: BaseBrowser) -> None:
        """Set up the browser base."""
        self.base = base

    def __call__(self, args: dict) -> Any:
        """Call the tool with args."""
        if self.base is None:
            raise ValueError("Browser base has not been set up.")
        return self._run(args)

    def _run(self, args: dict) -> Any:
        """Run the tool with args."""
        raise NotImplementedError()
```

The underlying `BaseBrowser` interface defines the core browser automation capabilities:

```python
class BaseBrowser(ABC):
    """Base class for browser implementations."""

    @abstractmethod
    def open(self, url: str) -> None:
        """Open a URL in the browser."""
        pass

    @abstractmethod
    def get_page_content(self) -> str:
        """Get the content of the current page."""
        pass

    @abstractmethod
    def find_element(self, selector: str) -> Any:
        """Find an element on the page."""
        pass

    @abstractmethod
    def click(self, element: Any) -> None:
        """Click an element."""
        pass

    @abstractmethod
    def input_text(self, element: Any, text: str) -> None:
        """Input text into an element."""
        pass

    @abstractmethod
    def take_screenshot(self) -> bytes:
        """Take a screenshot of the current page."""
        pass
```

The framework implements concrete browser drivers like `SeleniumBrowser` that inherit from `BaseBrowser`:

```python
class SeleniumBrowser(BaseBrowser):
    """Selenium-based browser implementation."""

    def __init__(self, headless: bool = False):
        """Initialize the browser."""
        options = webdriver.ChromeOptions()
        if headless:
            options.add_argument("--headless")
        self.driver = webdriver.Chrome(options=options)

    def open(self, url: str) -> None:
        """Open a URL in the browser."""
        self.driver.get(url)

    def get_page_content(self) -> str:
        """Get the content of the current page."""
        return self.driver.page_source

    # Implementation of other methods...
```

This architecture allows for:
1. Abstraction over different browser automation tools
2. Easy extension with new browser-based tools
3. Consistent interface for browser interactions
```

## 📚 Further Reading

- [DeepWiki Documentation](https://github.com/AsyncFuncAI/deepwiki-open)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [Cursor Documentation](https://cursor.sh/docs)

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](../LICENSE) file for details.