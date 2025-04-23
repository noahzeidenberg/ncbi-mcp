#!/usr/bin/env python3
import asyncio
import json
import sys
import os
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def test_mcp_tool(tool_name, tool_params):
    """Test the NCBI MCP implementation with a specific tool and parameters."""
    print(f"Testing NCBI MCP with tool: {tool_name}")
    print(f"Parameters: {json.dumps(tool_params, indent=2)}")
    
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
                
                # Call the specified tool with the provided parameters
                print(f"\nCalling tool '{tool_name}'...")
                result = await client.call_tool(tool_name, tool_params)
                print(f"Result: {json.dumps(result, indent=2)}")
                
                print("\nTest completed successfully!")
    except Exception as e:
        print(f"Error during testing: {e}")

if __name__ == "__main__":
    # Default tool and parameters
    tool_name = "search"
    tool_params = {
        "database": "gene",
        "term": "BRCA1[Gene Name] AND human[Organism]",
        "retmax": 1
    }
    
    # If command-line arguments are provided, use them
    if len(sys.argv) > 1:
        tool_name = sys.argv[1]
        if len(sys.argv) > 2:
            # Try to parse the second argument as JSON
            try:
                tool_params = json.loads(sys.argv[2])
            except json.JSONDecodeError:
                print("Error: Tool parameters must be valid JSON")
                sys.exit(1)
    
    asyncio.run(test_mcp_tool(tool_name, tool_params)) 