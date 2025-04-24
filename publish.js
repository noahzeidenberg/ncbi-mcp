#!/usr/bin/env node

/**
 * Publish script for NCBI MCP
 * This script publishes the package to npm and Smithery
 */

require('dotenv').config();
const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const https = require('https');

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

// Check for Smithery API key
const smitheryApiKey = process.env.SMITHERY_API_KEY;
if (!smitheryApiKey) {
  console.error('Error: SMITHERY_API_KEY environment variable is not set');
  process.exit(1);
}

// Check if working directory is clean
try {
  execSync('git diff-index --quiet HEAD --', { stdio: 'ignore' });
} catch (error) {
  console.error('Error: Working directory is not clean. Please commit all changes before publishing.');
  process.exit(1);
}

// Create git tag if it doesn't exist
const version = packageJson.version;
try {
  // Check if tag exists
  try {
    execSync(`git rev-parse v${version}`, { stdio: 'ignore' });
    console.log(`Git tag v${version} already exists, skipping tag creation`);
  } catch {
    // Tag doesn't exist, create it
    execSync(`git tag -a v${version} -m "Release version ${version}"`, { stdio: 'inherit' });
    console.log(`Created git tag v${version}`);
    
    // Push git tag
    execSync(`git push origin v${version}`, { stdio: 'inherit' });
    console.log(`Pushed git tag v${version}`);
  }
} catch (error) {
  console.error('Error handling git tag:', error.message);
  process.exit(1);
}

// Publish to npm
console.log(`Publishing ${packageJson.name}@${version} to npm...`);
try {
  execSync('npm publish', { stdio: 'inherit' });
  console.log(`Successfully published ${packageJson.name}@${version} to npm`);
} catch (error) {
  console.error('Error publishing package to npm:', error.message);
  process.exit(1);
}

// Publish to Smithery
console.log('Publishing to Smithery...');
const smitheryData = JSON.stringify({
  name: packageJson.name,
  version: version,
  description: packageJson.description,
  repository: packageJson.repository.url,
  author: packageJson.author,
  license: packageJson.license,
  changelog: `https://github.com/${packageJson.repository.url.split('/').slice(-2).join('/')}/releases/tag/v${version}`
});

const options = {
  hostname: 'api.smithery.dev',
  path: '/v1/mcp/publish',
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${smitheryApiKey}`,
    'Content-Length': smitheryData.length
  }
};

const req = https.request(options, (res) => {
  let data = '';
  res.on('data', (chunk) => data += chunk);
  res.on('end', () => {
    if (res.statusCode === 200) {
      console.log('Successfully published to Smithery');
      console.log('\nRelease Summary:');
      console.log(`- Version: ${version}`);
      console.log(`- NPM: https://www.npmjs.com/package/${packageJson.name}`);
      console.log(`- Smithery: https://smithery.dev/mcp/${packageJson.name}`);
      console.log(`- GitHub: https://github.com/${packageJson.repository.url.split('/').slice(-2).join('/')}/releases/tag/v${version}`);
    } else {
      console.error('Error publishing to Smithery:', data);
      process.exit(1);
    }
  });
});

req.on('error', (error) => {
  console.error('Error publishing to Smithery:', error.message);
  process.exit(1);
});

req.write(smitheryData);
req.end(); 