#!/usr/bin/env node

/**
 * NCBI MCP Adapter for Cursor
 * This script serves as a wrapper to call the Python MCP implementation
 */

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

// Get the path to the Python script
const pythonScript = path.join(__dirname, '..', 'ncbi-mcp.py');

// Check if Python script exists
if (!fs.existsSync(pythonScript)) {
  console.error(`Error: Python script not found at ${pythonScript}`);
  process.exit(1);
}

// Spawn the Python process
const pythonProcess = spawn('python', [pythonScript], {
  stdio: ['pipe', 'pipe', 'pipe']
});

// Handle Python process errors
pythonProcess.on('error', (err) => {
  console.error('Failed to start Python process:', err);
  process.exit(1);
});

// Pipe stdin/stdout between Node and Python
process.stdin.pipe(pythonProcess.stdin);
pythonProcess.stdout.pipe(process.stdout);
pythonProcess.stderr.pipe(process.stderr);

// Handle process termination
process.on('SIGINT', () => {
  pythonProcess.kill();
  process.exit();
});

pythonProcess.on('close', (code) => {
  process.exit(code);
});