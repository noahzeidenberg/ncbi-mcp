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
const pythonScript = path.join(scriptDir, 'ncbi-mcp-fast.py');

// Check if the Python script exists
if (!fs.existsSync(pythonScript)) {
  console.error(`Error: Python script not found at ${pythonScript}`);
  process.exit(1);
}

// Function to find Python executable
function findPythonExecutable() {
  // Try common Python executable names
  const pythonNames = ['python', 'python3', 'py'];
  
  for (const name of pythonNames) {
    try {
      // Use 'where' on Windows, 'which' on Unix-like systems
      const command = process.platform === 'win32' ? 'where' : 'which';
      const result = require('child_process').spawnSync(command, [name], { stdio: 'ignore' });
      
      if (result.status === 0) {
        return name;
      }
    } catch (e) {
      // Ignore errors and continue to the next name
    }
  }
  
  // Default to 'python' if no executable is found
  return 'python';
}

// Initialize MCP protocol
const initMessage = {
  jsonrpc: "2.0",
  id: 1,
  method: "initialize",
  params: {
    protocolVersion: "2.0",
    capabilities: {
      logging: {
        level: "info",
        enabled: true
      },
      prompts: {
        enabled: true
      },
      resources: {
        enabled: true,
        "ncbi://databases": {
          description: "List available NCBI databases",
          mimeType: "application/json"
        }
      },
      tools: {
        enabled: true,
        "ncbi-search": {
          description: "Search NCBI databases",
          parameters: {
            type: "object",
            properties: {
              database: { 
                type: "string", 
                description: "NCBI database to search" 
              },
              term: { 
                type: "string", 
                description: "Search term" 
              },
              filters: { 
                type: "object", 
                description: "Optional filters",
                additionalProperties: true
              }
            },
            required: ["database", "term"]
          }
        },
        "ncbi-fetch": {
          description: "Fetch records from NCBI",
          parameters: {
            type: "object",
            properties: {
              database: { 
                type: "string", 
                description: "NCBI database" 
              },
              ids: { 
                type: "array", 
                description: "List of IDs to fetch",
                items: {
                  type: "string"
                }
              }
            },
            required: ["database", "ids"]
          }
        }
      }
    },
    serverInfo: {
      name: "NCBI MCP",
      version: "1.0.0",
      description: "Model Context Protocol server for NCBI databases"
    }
  }
};

// Spawn the Python process
const pythonExecutable = findPythonExecutable();
console.error(`Using Python executable: ${pythonExecutable}`);
const pythonProcess = spawn(pythonExecutable, [pythonScript], {
  stdio: ['pipe', 'pipe', 'pipe']
});

// Handle incoming messages from Python
pythonProcess.stdout.on('data', (data) => {
  console.log(data.toString());
});

// Handle errors from Python
pythonProcess.stderr.on('data', (data) => {
  console.error(data.toString());
});

// Send initialization message to Python process
pythonProcess.stdin.write(JSON.stringify(initMessage) + '\n');

// Handle process exit
pythonProcess.on('exit', (code) => {
  if (code !== 0) {
    console.error(`Python process exited with code ${code}`);
    process.exit(code);
  }
});

// Handle process errors
pythonProcess.on('error', (err) => {
  console.error('Failed to start Python process:', err);
  process.exit(1);
});

// Forward stdin to Python process
process.stdin.on('data', (data) => {
  pythonProcess.stdin.write(data);
});

// Handle process termination
process.on('SIGINT', () => {
  pythonProcess.kill('SIGINT');
  process.exit(0);
});

process.on('SIGTERM', () => {
  pythonProcess.kill('SIGTERM');
  process.exit(0);
});