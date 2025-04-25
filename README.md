# NCBI-MCP - NCBI Model Context Protocol

A Model Context Protocol (MCP) implementation for accessing NCBI databases and tools.

## Features

- Query NCBI databases (PubMed, Gene, Protein, etc.)
- Retrieve gene information and summaries
- Analyze gene lists and relationships
- Access NCBI Datasets API

## Installation

### For Cursor

```bash
npm install -g ncbi-mcp
```

After installation, restart Cursor and go to Settings > Extensions. Add the MCP with the command: `ncbi-mcp`

### For Claude Desktop

1. Clone this repository
2. Add the following to your Claude Desktop configuration file:

#### On macOS:
`~/Library/Application Support/Claude/claude_desktop_config.json`

#### On Windows:
`%APPDATA%/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "ncbi-mcp": {
      "command": "python",
      "args": [
        "ncbi_mcp.py",
        "--api-key",
        "YOUR_NCBI_API_KEY",
        "--email",
        "YOUR_EMAIL"
      ],
      "env": {
        "PYTHONPATH": "PATH_TO_NCBI_MCP_DIRECTORY"
      }
    }
  }
}
```

Replace `PATH_TO_NCBI_MCP_DIRECTORY` with the absolute path to the directory where you cloned this repository.

### Setting up Environment Variables

This package requires an NCBI API key. You can provide this key in two ways:

1. **Command line arguments** (as shown in the Claude Desktop configuration above)
2. **Environment variables** using a `.env` file in the root directory of the package:

```
# .env file
NCBI_API_KEY=your_api_key_here
NCBI_EMAIL=your_email_here
```

To obtain an NCBI API key:
1. Register for an NCBI account at https://www.ncbi.nlm.nih.gov/
2. Get your API key from https://www.ncbi.nlm.nih.gov/account/settings/

## Usage

Once installed, you can use the NCBI MCP in your conversations with Claude or Cursor. The MCP provides the following tools:

- `ncbi-search`: Search NCBI databases
- `ncbi-fetch`: Fetch records from NCBI
- `get_gene_info`: Get detailed information about a specific gene
- `get_genome_info`: Get detailed information about a specific genome

## Development

### Prerequisites

- Python 3.8+
- Node.js 14+
- NCBI Datasets CLI tools (for some advanced features)

### Setup

1. Clone this repository
2. Install dependencies:

```bash
# Install Python dependencies
pip install -r requirements.txt
```

3. Set up your .env file with your NCBI credentials as described above

### Testing

```bash
# Test the MCP server
python test_ncbi_mcp.py
```

## License

Apache-2.0 