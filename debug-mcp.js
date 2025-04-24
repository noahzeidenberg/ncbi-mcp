#!/usr/bin/env node

/**
 * Debug script for NCBI MCP
 * This script helps diagnose issues with the MCP client and server communication
 */

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

// Get the path to the Python script
const scriptDir = path.resolve(__dirname);
const pythonScript = path.join(scriptDir, 'ncbi-mcp.py');

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

// Spawn the Python process
const pythonExecutable = findPythonExecutable();
console.log(`Using Python executable: ${pythonExecutable}`);
const pythonProcess = spawn(pythonExecutable, [pythonScript], {
  stdio: ['pipe', 'pipe', 'pipe']
});

// Handle incoming messages from Python
pythonProcess.stdout.on('data', (data) => {
  console.log('Received from Python stdout:', data.toString());
});

// Handle errors from Python
pythonProcess.stderr.on('data', (data) => {
  console.log('Received from Python stderr:', data.toString());
});

// Send initialization message to Python process
console.log('Sending init message:', JSON.stringify(initMessage, null, 2));
pythonProcess.stdin.write(JSON.stringify(initMessage) + '\n');

// Wait for a response
setTimeout(() => {
  // Send a tools/list request
  const toolsListMessage = {
    jsonrpc: "2.0",
    id: 2,
    method: "tools/list"
  };
  
  console.log('Sending tools/list message:', JSON.stringify(toolsListMessage, null, 2));
  pythonProcess.stdin.write(JSON.stringify(toolsListMessage) + '\n');
  
  // Wait for a response
  setTimeout(() => {
    // Send a tools/call request
    const toolsCallMessage = {
      jsonrpc: "2.0",
      id: 3,
      method: "tools/call",
      params: {
        tool: "ncbi-search",
        params: {
          database: "gene",
          term: "BRCA1[Gene Name]",
          filters: {}
        }
      }
    };
    
    console.log('Sending tools/call message:', JSON.stringify(toolsCallMessage, null, 2));
    pythonProcess.stdin.write(JSON.stringify(toolsCallMessage) + '\n');
    
    // Wait for a response
    setTimeout(() => {
      console.log('Test completed, closing Python process');
      pythonProcess.kill();
    }, 5000);
  }, 5000);
}, 5000);

// Handle process exit
pythonProcess.on('close', (code) => {
  console.log('Python process exited with code:', code);
  process.exit(code);
});

// Handle errors
pythonProcess.on('error', (err) => {
  console.error('Failed to start Python process:', err);
  process.exit(1);
}); 