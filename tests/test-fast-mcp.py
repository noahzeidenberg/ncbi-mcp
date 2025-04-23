#!/usr/bin/env python3
import asyncio
import json
import sys
import os
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

def format_result(result):
    """Format a result object for display."""
    if hasattr(result, 'to_dict'):
        return result.to_dict()
    elif hasattr(result, '__dict__'):
        return result.__dict__
    else:
        return str(result)

async def test_mcp():
    """Test the NCBI MCP implementation using FastMCP."""
    print("Testing NCBI MCP with FastMCP...")
    
    # Create server parameters
    server_params = StdioServerParameters(
        command="python",
        args=["ncbi-mcp-fast.py"],
        env=None
    )
    
    try:
        # Connect to the MCP server using stdio transport
        async with stdio_client(server_params) as (stdio, write):
            async with ClientSession(stdio, write) as client:
                # Initialize the session
                await client.initialize()
                
                # Test search functionality with a simple query
                print("\nTesting search functionality...")
                try:
                    search_result = await client.call_tool(
                        "search",
                        {
                            "database": "gene",
                            "term": "BRCA1",
                            "retmax": 1
                        }
                    )
                    print(f"Search result: {format_result(search_result)}")
                    
                    # If we got a result, test summary functionality
                    if hasattr(search_result, 'status') and search_result.status == "ok" and hasattr(search_result, 'data'):
                        gene_id = search_result.data[0]["id"]
                        print(f"\nTesting summary functionality with gene ID: {gene_id}...")
                        summary_result = await client.call_tool(
                            "summary",
                            {
                                "database": "gene",
                                "ids": [gene_id],
                                "fields": ["title", "summary"]
                            }
                        )
                        print(f"Summary result: {format_result(summary_result)}")
                except Exception as e:
                    print(f"Error during search/summary: {str(e)}")
                    print("This might be due to NCBI API rate limiting or network issues.")
                    print("Please try again later or check your network connection.")
                
                # Test genome metadata functionality
                print("\nTesting genome metadata functionality...")
                try:
                    genome_result = await client.call_tool(
                        "genome_metadata",
                        {
                            "organism": "Homo sapiens",
                            "datasets_path": "datasets.exe",  # Use the globally available executable
                            "dataformat_path": "dataformat.exe"  # Use the globally available executable
                        }
                    )
                    print(f"Genome metadata result: {format_result(genome_result)}")
                except Exception as e:
                    print(f"Error during genome metadata test: {str(e)}")
                    print("This might be due to:")
                    print("1. NCBI API rate limiting")
                    print("2. Network connectivity issues")
                    print("3. Issues with datasets.exe or dataformat.exe")
                
                print("\nAll tests completed!")
    except Exception as e:
        print(f"Error during testing: {str(e)}")
        print("This might be due to:")
        print("1. NCBI API rate limiting")
        print("2. Network connectivity issues")
        print("3. Missing or incorrect dependencies")
        print("\nPlease check your network connection and try again later.")

if __name__ == "__main__":
    asyncio.run(test_mcp()) 