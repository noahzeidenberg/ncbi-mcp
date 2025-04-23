#!/usr/bin/env python3
import json
import requests

def test_search():
    """Send a test search request to the MCP server."""
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "search",
        "params": {
            "database": "gene",
            "term": "BRCA1[Gene Name] AND human[Organism]",
            "retmax": 1
        }
    }
    
    try:
        response = requests.post(
            "http://localhost:8000/jsonrpc",
            json=request,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        result = response.json()
        print(f"Search result: {json.dumps(result, indent=2)}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_search() 