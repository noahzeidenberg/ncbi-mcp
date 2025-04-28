# NCBI Model Context Protocol (MCP)

A Python implementation of the Model Context Protocol for interacting with NCBI databases.

## Setup

1. Clone this repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Create a `.env` file with your NCBI API key:
   ```
   NCBI_API_KEY=your_api_key_here
   NCBI_EMAIL=your_email@example.com
   ```

## Running the MCP Server

```
python ncbi_mcp.py
```

## Using with Cursor/Claude

Once the MCP server is running, you can interact with it using natural language in Cursor/Claude.

### Using Natural Language Queries

You can use natural language to perform searches and retrieve information:

```
tools/call
{
  "name": "nlp-query",
  "arguments": {
    "query": "Find research articles about BRCA1"
  }
}
```

Or more simply, just use the query directly:

```
@ncbi-mcp Find research articles about BRCA1
```

### Example Queries

Here are some example queries you can try:

1. Search for scientific articles:
   ```
   @ncbi-mcp Find the latest research on COVID-19 vaccines
   ```

2. Get gene information:
   ```
   @ncbi-mcp Tell me about the BRCA1 gene
   ```

3. Fetch genome information:
   ```
   @ncbi-mcp Get genome information for Homo sapiens
   ```

4. Fetch a specific record:
   ```
   @ncbi-mcp Get gene ID 70
   ```

## Testing

To test the MCP server with various queries, you can use the included test files:

```
# Test natural language query functionality (default)
.\run_test.bat

# Test all tools
.\run_test.bat all

# Test specific test file
.\run_test.bat test_all_tools.jsonl
```

The test script will:
1. Start the MCP server in background
2. Send test requests from the specified file
3. Wait for a few seconds to allow processing
4. Terminate the server and display the output

This approach is used because the MCP server is designed to run continuously as a service. For manual testing without automatic termination, you can use:

```
# Run manually with any test file
type test_nlp_query.jsonl | python ncbi_mcp.py
```

The test files contain example JSON-RPC requests that simulate how Cursor/Claude would interact with the MCP server.

## Advanced Usage

For more advanced usage, you can directly call the specific tools:

### Search NCBI Databases

```
tools/call
{
  "name": "ncbi-search",
  "arguments": {
    "database": "pubmed",
    "term": "BRCA1",
    "filters": {
      "organism": "Homo sapiens",
      "date_range": {
        "start": "2020"
      }
    }
  }
}
```

### Fetch NCBI Records

```
tools/call
{
  "name": "ncbi-fetch",
  "arguments": {
    "database": "gene",
    "ids": ["70"],
    "rettype": "gb"
  }
}
```

### Get Gene Information

```
tools/call
{
  "name": "get_gene_info",
  "arguments": {
    "gene_id": "672"
  }
}
```

### Get Genome Information

```
tools/call
{
  "name": "get_genome_info",
  "arguments": {
    "organism": "Homo sapiens",
    "reference": true
  }
}
```

## License

Apache-2.0 