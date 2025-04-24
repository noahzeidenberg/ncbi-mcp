#!/usr/bin/env node

/**
 * Test script for NCBI MCP
 * This script tests the MCP server by sending a simple request
 */

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

// Get the path to the Python script
const pythonScript = path.join(__dirname, 'src', 'server', 'server.py');

// Check if Python script exists
if (!fs.existsSync(pythonScript)) {
  console.error(`Error: Python script not found at ${pythonScript}`);
  process.exit(1);
}

// Spawn the Python process
const pythonProcess = spawn('python', [pythonScript, '--debug'], {
  stdio: ['pipe', 'pipe', 'pipe']
});

// Handle Python process errors
pythonProcess.on('error', (err) => {
  console.error('Failed to start Python process:', err);
  process.exit(1);
});

// Send initialization request
const initRequest = {
  jsonrpc: "2.0",
  id: 1,
  method: "initialize",
  params: {
    capabilities: {
      tools: {
        enabled: true
      },
      resources: {
        enabled: true
      },
      logging: {
        enabled: true,
        level: "info"
      }
    }
  }
};

console.log('Sending initialization request...');
pythonProcess.stdin.write(JSON.stringify(initRequest) + '\n');

// Handle Python process output
pythonProcess.stdout.on('data', (data) => {
  console.log('Received response:');
  console.log(data.toString());
});

pythonProcess.stderr.on('data', (data) => {
  console.error('Error:');
  console.error(data.toString());
});

// Send tools list request
setTimeout(() => {
  const toolsRequest = {
    jsonrpc: "2.0",
    id: 2,
    method: "tools/list"
  };
  
  console.log('Sending tools list request...');
  pythonProcess.stdin.write(JSON.stringify(toolsRequest) + '\n');
}, 1000);

// Handle process termination
pythonProcess.on('close', (code) => {
  console.log(`Python process exited with code ${code}`);
  process.exit(code);
});

// Handle process termination
process.on('SIGINT', () => {
  pythonProcess.kill();
  process.exit();
}); 