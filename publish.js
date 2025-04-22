#!/usr/bin/env node

/**
 * Publish script for NCBI MCP
 * This script publishes the package to npm
 */

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

// Check if package.json exists
const packageJsonPath = path.join(__dirname, 'package.json');
if (!fs.existsSync(packageJsonPath)) {
  console.error('Error: package.json not found');
  process.exit(1);
}

// Read package.json
const packageJson = JSON.parse(fs.readFileSync(packageJsonPath, 'utf8'));

// Check if npm is installed
try {
  execSync('npm --version', { stdio: 'ignore' });
} catch (error) {
  console.error('Error: npm is not installed');
  process.exit(1);
}

// Check if user is logged in to npm
try {
  execSync('npm whoami', { stdio: 'ignore' });
} catch (error) {
  console.error('Error: You are not logged in to npm. Please run "npm login" first.');
  process.exit(1);
}

// Publish the package
console.log(`Publishing ${packageJson.name}@${packageJson.version} to npm...`);
try {
  execSync('npm publish', { stdio: 'inherit' });
  console.log(`Successfully published ${packageJson.name}@${packageJson.version} to npm`);
} catch (error) {
  console.error('Error publishing package:', error.message);
  process.exit(1);
} 