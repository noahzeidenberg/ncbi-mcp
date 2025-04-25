# NCBI MCP

NCBI Model Context Protocol (MCP) adapter for Cursor and Claude Desktop.

This MCP server provides access to NCBI databases through the Model Context Protocol, allowing AI assistants to search and retrieve data from NCBI databases.

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

## Usage

Once installed, you can use the NCBI MCP in your conversations with Claude or Cursor. The MCP provides the following tools:

- `ncbi-search`: Search NCBI databases
- `ncbi-fetch`: Fetch records from NCBI
- `get_gene_info`: Get detailed information about a specific gene using datasets.exe
- `get_genome_info`: Get detailed information about a specific genome using datasets.exe

## Development

### Prerequisites

- Python 3.8+
- Node.js 14+
- NCBI Datasets CLI tools (datasets.exe and dataformat.exe)

### Setup

1. Clone this repository
2. Install dependencies:

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install Node.js dependencies
npm install
```

3. Download and install NCBI Datasets CLI tools:
   - Visit [NCBI Datasets](https://www.ncbi.nlm.nih.gov/datasets/docs/v2/download-and-install/)
   - Download and install the tools for your platform
   - Place the executables in your home directory or specify their paths when initializing the client

### Testing

```bash
# Test the MCP server
python test_ncbi_mcp.py
```

## License

Apache-2.0 