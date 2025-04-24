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
  protocolVersion: "1.0",
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
  },
  serverInfo: {
    name: "ncbi-mcp",
    version: "1.0.6",
    description: "NCBI Entrez MCP adapter for Cursor"
  }
};

// Send initialization message
console.log(JSON.stringify(initMessage));

// Spawn the Python process
const pythonProcess = spawn('python', [pythonScript], {
  stdio: ['pipe', 'pipe', 'pipe']
});

// Handle incoming messages from Python
pythonProcess.stdout.on('data', (data) => {
  process.stdout.write(data);
});

// Handle errors from Python
pythonProcess.stderr.on('data', (data) => {
  process.stderr.write(data);
});

// Pipe stdin to Python
process.stdin.on('data', (data) => {
  pythonProcess.stdin.write(data);
});

// Handle process exit
pythonProcess.on('close', (code) => {
  process.exit(code);
});

// Handle errors
pythonProcess.on('error', (err) => {
  console.error('Failed to start Python process:', err);
  process.exit(1);
}); 