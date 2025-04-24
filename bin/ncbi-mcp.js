#!/usr/bin/env node

/**
 * NCBI MCP Adapter for Cursor
 * This script serves as a wrapper to call the Python MCP implementation
 */

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

// Get the path to the Python script
const scriptDir = path.resolve(__dirname, '..');
const pythonScript = path.join(scriptDir, 'ncbi-mcp.py');

// Check if the Python script exists
if (!fs.existsSync(pythonScript)) {
  console.error(`Error: Python script not found at ${pythonScript}`);
  process.exit(1);
}

// Initialize MCP protocol
const initMessage = {
  jsonrpc: "2.0",
  id: 1,
  method: "initialize",
  params: {
    capabilities: {
      resources: {},
      tools: {
        "ncbi-search": {
          description: "Search NCBI databases",
          parameters: {
            database: { type: "string", description: "NCBI database to search" },
            term: { type: "string", description: "Search term" },
            filters: { type: "object", description: "Optional filters" }
          }
        },
        "ncbi-fetch": {
          description: "Fetch records from NCBI",
          parameters: {
            database: { type: "string", description: "NCBI database" },
            ids: { type: "array", description: "List of IDs to fetch" }
          }
        }
      }
    }
  }
};

// Send initialization message
console.error('Sending init message:', JSON.stringify(initMessage, null, 2));

// Spawn the Python process
const pythonProcess = spawn('python3', [pythonScript], {
  stdio: ['pipe', 'pipe', 'pipe']
});

// Send initialization message to Python process
pythonProcess.stdin.write(JSON.stringify(initMessage) + '\n');

// Handle incoming messages from Python
pythonProcess.stdout.on('data', (data) => {
  console.error('Received from Python stdout:', data.toString());
  process.stdout.write(data);
});

// Handle errors from Python
pythonProcess.stderr.on('data', (data) => {
  console.error('Received from Python stderr:', data.toString());
  process.stderr.write(data);
});

// Pipe stdin to Python
process.stdin.on('data', (data) => {
  console.error('Sending to Python:', data.toString());
  pythonProcess.stdin.write(data);
});

// Handle process exit
pythonProcess.on('close', (code) => {
  console.error('Python process exited with code:', code);
  process.exit(code);
});

// Handle errors
pythonProcess.on('error', (err) => {
  console.error('Failed to start Python process:', err);
  process.exit(1);
});