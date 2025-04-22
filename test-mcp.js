#!/usr/bin/env node

/**
 * Test script for NCBI MCP
 * This script sends a simple request to the MCP and displays the response
 */

const { spawn } = require('child_process');
const path = require('path');

// Path to the MCP script
const mcpScript = path.join(__dirname, 'bin', 'ncbi-mcp.js');

// Create a test request
const testRequest = {
  jsonrpc: '2.0',
  id: 1,
  operation: 'search',
  database: 'gene',
  term: 'BRCA1[Gene Name] AND human[Organism]',
  pagination: {
    retmax: 1
  }
};

// Spawn the MCP process
const mcpProcess = spawn('node', [mcpScript], {
  stdio: ['pipe', 'pipe', 'pipe']
});

// Send the test request
mcpProcess.stdin.write(JSON.stringify(testRequest) + '\n');
mcpProcess.stdin.end();

// Collect the response
let response = '';
mcpProcess.stdout.on('data', (data) => {
  response += data.toString();
});

// Handle process completion
mcpProcess.on('close', (code) => {
  console.log(`MCP process exited with code ${code}`);
  try {
    const parsedResponse = JSON.parse(response);
    console.log('Response:', JSON.stringify(parsedResponse, null, 2));
  } catch (error) {
    console.error('Error parsing response:', error);
    console.log('Raw response:', response);
  }
});

// Handle errors
mcpProcess.stderr.on('data', (data) => {
  console.error(`MCP error: ${data}`);
});

mcpProcess.on('error', (err) => {
  console.error('Failed to start MCP process:', err);
}); 