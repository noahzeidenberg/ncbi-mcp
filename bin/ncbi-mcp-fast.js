#!/usr/bin/env node

/**
 * NCBI MCP Adapter for Cursor
 * This script serves as a wrapper to call the Python FastMCP implementation
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

// Spawn the Python process
const pythonProcess = spawn('python', [pythonScript], {
  stdio: ['pipe', 'pipe', 'pipe']
});

// Pipe stdin/stdout between Node and Python
process.stdin.pipe(pythonProcess.stdin);
pythonProcess.stdout.pipe(process.stdout);

// Handle process exit
pythonProcess.on('close', (code) => {
  process.exit(code);
});

// Handle errors
pythonProcess.on('error', (err) => {
  console.error('Failed to start Python process:', err);
  process.exit(1);
}); 