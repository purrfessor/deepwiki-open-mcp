/**
 * Sample JavaScript client for the DeepWiki MCP API.
 *
 * This example demonstrates how to:
 * 1. Make a direct query to the MCP API
 * 2. Use WebSockets for streaming responses
 */

// Simple MCP client in JavaScript
const fetch = require('node-fetch');
const WebSocket = require('ws');

// Direct query
async function queryRepository() {
    const repoUrl = 'https://github.com/AsyncFuncAI/deepwiki-open';
    const query = 'How does the RAG system work?';

    // REST API query
    const response = await fetch('http://localhost:9783/query', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            repository: repoUrl,
            query: query
        }),
    });

    const data = await response.json();
    console.log('Response:', data);
}

// WebSocket streaming query
function streamingQuery() {
    const repoUrl = 'https://github.com/AsyncFuncAI/deepwiki-open';
    const query = 'How does the RAG system work?';

    const ws = new WebSocket('ws://localhost:9783/ws/query');

    ws.on('open', function open() {
        console.log('Connected to MCP server');
        ws.send(JSON.stringify({
            repository: repoUrl,
            query: query,
            stream: true
        }));
    });

    ws.on('message', function message(data) {
        const chunk = JSON.parse(data);
        process.stdout.write(chunk.text);

        if (chunk.done) {
            ws.close();
        }
    });

    ws.on('close', function close() {
        console.log('\nConnection closed');
    });

    ws.on('error', function error(err) {
        console.error('WebSocket error:', err);
    });
}

// Run examples
async function run() {
    console.log('Running direct query...');
    await queryRepository();

    console.log('\nRunning streaming query...');
    streamingQuery();
}

run();

// Node.js example (if running in Node.js environment)
if (typeof window === 'undefined') {
  // Example of how to use with Node.js
  console.log('This is a client-side example. To run in Node.js, you need:');
  console.log('npm install ws node-fetch');

  // Uncomment to run the examples in Node.js:
  // run();
}

// Browser example (if running in a browser)
if (typeof window !== 'undefined') {
  // The above functions will work directly in the browser

  document.addEventListener('DOMContentLoaded', () => {
    const repositoryInput = document.getElementById('repository');
    const questionInput = document.getElementById('question');
    const streamCheckbox = document.getElementById('stream');
    const submitButton = document.getElementById('submit');
    const responseDiv = document.getElementById('response');

    submitButton.addEventListener('click', async () => {
      const repository = repositoryInput.value;
      const question = questionInput.value;
      const useStreaming = streamCheckbox.checked;

      if (!repository || !question) {
        responseDiv.textContent = 'Please enter both a repository URL and a question.';
        return;
      }

      responseDiv.textContent = 'Loading...';

      if (useStreaming) {
        // Use WebSocket streaming
        streamingQuery();
      } else {
        // Use direct query
        queryRepository();
      }
    });
  });
}