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

// Function to cleanup on failure
function cleanup(version) {
  try {
    // Delete local tag if it exists
    try {
      execSync(`git tag -d v${version}`, { stdio: 'ignore' });
      console.log(`Deleted local tag v${version}`);
    } catch (e) {
      // Tag doesn't exist locally, ignore
    }
    
    // Delete remote tag if it exists
    try {
      execSync(`git push origin :refs/tags/v${version}`, { stdio: 'ignore' });
      console.log(`Deleted remote tag v${version}`);
    } catch (e) {
      // Tag doesn't exist remotely, ignore
    }
  } catch (error) {
    console.error('Warning: Cleanup failed:', error.message);
  }
}

const version = packageJson.version;

// Publish to npm first
console.log(`Publishing ${packageJson.name}@${version} to npm...`);
try {
  execSync('npm publish', { stdio: 'inherit' });
  console.log(`Successfully published ${packageJson.name}@${version} to npm`);
} catch (error) {
  console.error('Error publishing package to npm:', error.message);
  process.exit(1);
}

// Only create git tag after successful npm publish
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
  cleanup(version);
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
    'Content-Length': Buffer.byteLength(smitheryData)
  }
};

const req = https.request(options, (res) => {
  let data = '';
  res.on('data', (chunk) => {
    data += chunk;
  });
  res.on('end', () => {
    if (res.statusCode === 200) {
      console.log('Successfully published to Smithery');
    } else {
      console.error('Error publishing to Smithery:', data);
      cleanup(version);
      process.exit(1);
    }
  });
});

req.on('error', (error) => {
  console.error('Error publishing to Smithery:', error.message);
  cleanup(version);
  process.exit(1);
});

req.write(smitheryData);
req.end(); 