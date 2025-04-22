#!/usr/bin/env node

/**
 * Install script for NCBI MCP in Cursor
 * This script installs the MCP in Cursor
 */

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const os = require('os');

// Get the Cursor extensions directory
const cursorExtensionsDir = path.join(os.homedir(), '.cursor', 'extensions');

// Check if Cursor extensions directory exists
if (!fs.existsSync(cursorExtensionsDir)) {
  console.error('Error: Cursor extensions directory not found');
  console.error(`Expected path: ${cursorExtensionsDir}`);
  console.error('Please make sure Cursor is installed and the extensions directory exists');
  process.exit(1);
}

// Create the MCP directory
const mcpDir = path.join(cursorExtensionsDir, 'ncbi-mcp');
if (!fs.existsSync(mcpDir)) {
  fs.mkdirSync(mcpDir, { recursive: true });
}

// Copy the necessary files
const filesToCopy = [
  'plugin.json',
  'ncbi-mcp.py',
  'ncbi_datasets_client.py',
  'analyze_genes.py',
  'ncbi_requests.json',
  'ncbi_response.json'
];

console.log('Copying files to Cursor extensions directory...');
for (const file of filesToCopy) {
  const sourcePath = path.join(__dirname, file);
  const targetPath = path.join(mcpDir, file);
  
  if (fs.existsSync(sourcePath)) {
    fs.copyFileSync(sourcePath, targetPath);
    console.log(`Copied ${file} to ${targetPath}`);
  } else {
    console.warn(`Warning: ${file} not found, skipping`);
  }
}

// Make the Python script executable
const pythonScriptPath = path.join(mcpDir, 'ncbi-mcp.py');
try {
  fs.chmodSync(pythonScriptPath, '755');
  console.log(`Made ${pythonScriptPath} executable`);
} catch (error) {
  console.warn(`Warning: Could not make ${pythonScriptPath} executable: ${error.message}`);
}

console.log('\nNCBI MCP has been installed in Cursor.');
console.log('Please restart Cursor to use the MCP.');
console.log('\nTo use the MCP in Cursor:');
console.log('1. Open Cursor');
console.log('2. Go to Settings > Extensions');
console.log('3. Add the MCP with the command: ncbi-mcp'); 