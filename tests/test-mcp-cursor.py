#!/usr/bin/env python3
import asyncio
import json
import sys
import os
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def test_mcp_with_cursor(prompt, context=None):
    """Test the NCBI MCP implementation with Cursor's AI capabilities."""
    print(f"Testing NCBI MCP with Cursor prompt: {prompt}")
    if context:
        print(f"Context: {context}")
    
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
                
                # Create a message with the prompt and context
                message = {
                    "role": "user",
                    "content": prompt
                }
                
                if context:
                    message["context"] = context
                
                # Send the message to the MCP server
                print("\nSending message to MCP server...")
                response = await client.send_message(message)
                print(f"Response: {json.dumps(response, indent=2)}")
                
                print("\nTest completed successfully!")
    except Exception as e:
        print(f"Error during testing: {e}")

if __name__ == "__main__":
    # Example prompt and context
    prompt = "Find information about the BRCA1 gene in humans"
    context = {
        "tools": ["search", "summary", "genome_metadata"],
        "preferences": {
            "format": "json",
            "detail_level": "high"
        }
    }
    
    # If command-line arguments are provided, use them
    if len(sys.argv) > 1:
        prompt = sys.argv[1]
        if len(sys.argv) > 2:
            # Try to parse the second argument as JSON for context
            try:
                context = json.loads(sys.argv[2])
            except json.JSONDecodeError:
                print("Error: Context must be valid JSON")
                sys.exit(1)
    
    asyncio.run(test_mcp_with_cursor(prompt, context)) 