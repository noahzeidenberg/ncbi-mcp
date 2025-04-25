#!/usr/bin/env python3
import json
import sys
import asyncio
from ncbi_datasets import NCBIDatasetsClient
from ncbi_mcp import NCBIClient, NCBIMCP

async def test_ncbi_client():
    """Test the NCBIClient class."""
    print("Testing NCBIClient...")
    
    # Initialize the client
    client = NCBIClient()
    
    # Test esearch
    print("\nTesting esearch...")
    result = client.esearch("gene", "BRCA1[Gene Name] AND human[Organism]")
    print(json.dumps(result, indent=2))
    
    # Test efetch
    print("\nTesting efetch...")
    if "esearchresult" in result and "idlist" in result["esearchresult"]:
        ids = result["esearchresult"]["idlist"][:5]  # Get up to 5 IDs
        if ids:
            result = client.efetch("gene", ids)
            print(json.dumps(result, indent=2))
    
    print("NCBIClient tests completed.")

async def test_datasets_client():
    """Test the NCBIDatasetsClient class."""
    print("\nTesting NCBIDatasetsClient...")
    
    try:
        # Initialize the client
        client = NCBIDatasetsClient()
        
        # Test get_gene_metadata
        print("\nTesting get_gene_metadata...")
        result = client.get_gene_metadata("7157")  # BRCA1 gene ID
        print(json.dumps(result, indent=2))
        
        # Test get_genome_metadata
        print("\nTesting get_genome_metadata...")
        result = client.get_genome_metadata("human", reference=True)
        print(json.dumps(result, indent=2))
        
        print("NCBIDatasetsClient tests completed.")
    except Exception as e:
        print(f"Error testing NCBIDatasetsClient: {e}")
        print("Make sure datasets.exe and dataformat.exe are installed and accessible.")

async def test_mcp_server():
    """Test the NCBIMCP server."""
    print("\nTesting NCBIMCP server...")
    
    # Initialize the server
    mcp = NCBIMCP()
    
    # Test tools list
    print("\nTesting tools list...")
    tools_list = await mcp._handle_tools_list(None)
    print(json.dumps(tools_list, indent=2))
    
    # Test tool calls
    print("\nTesting tool calls...")
    
    # Test ncbi-search
    print("\nTesting ncbi-search...")
    search_params = {
        "database": "gene",
        "term": "BRCA1[Gene Name] AND human[Organism]",
        "filters": {}
    }
    result = await mcp._handle_tool_call(type("Request", (), {"params": type("Params", (), {"name": "ncbi-search", "arguments": search_params})})())
    print(json.dumps(result, indent=2))
    
    # Test get_gene_info
    print("\nTesting get_gene_info...")
    gene_params = {
        "gene_id": "7157"  # BRCA1 gene ID
    }
    result = await mcp._handle_tool_call(type("Request", (), {"params": type("Params", (), {"name": "get_gene_info", "arguments": gene_params})})())
    print(json.dumps(result, indent=2))
    
    print("NCBIMCP server tests completed.")

async def main():
    """Run all tests."""
    await test_ncbi_client()
    await test_datasets_client()
    await test_mcp_server()

if __name__ == "__main__":
    asyncio.run(main()) 