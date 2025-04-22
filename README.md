# NCBI MCP for Cursor

A Model Control Protocol (MCP) adapter for NCBI Entrez databases that can be used with Cursor.

## Features

- Query NCBI databases (PubMed, Gene, Protein, etc.)
- Retrieve gene information and summaries
- Analyze gene lists and relationships
- Access NCBI Datasets API

## Installation

### Using npm/npx

```bash
# Install globally
npm install -g ncbi-mcp

# Or use directly with npx
npx ncbi-mcp
```

### Manual Installation

1. Clone this repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Make the Python script executable:
   ```bash
   chmod +x ncbi-mcp.py
   ```

## Usage

### In Cursor

1. Open Cursor
2. Go to Settings > Extensions
3. Add the MCP with the command: `ncbi-mcp`

### Command Line

```bash
# Using npx
npx ncbi-mcp

# Or if installed globally
ncbi-mcp
```

## Configuration

Create a `.env` file in the project root with your NCBI API key:

```
NCBI_API_KEY=your_api_key_here
```

## License

MIT 