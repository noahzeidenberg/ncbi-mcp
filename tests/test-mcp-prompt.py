#!/usr/bin/env python3
import asyncio
import json
import sys
import os
import logging
from dotenv import load_dotenv
from fastmcp import Client
from fastmcp.client.transports import PythonStdioTransport

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

def format_prompt_message(message):
    """Format a PromptMessage object into a dictionary."""
    if hasattr(message, 'content') and hasattr(message.content, 'text'):
        return {
            'role': message.role,
            'content': message.content.text
        }
    return str(message)

async def test_mcp_with_prompt(prompt):
    """Test the NCBI MCP implementation with a custom prompt."""
    logger.info(f"Testing NCBI MCP with prompt: {prompt}")
    
    # Create transport with explicit configuration
    transport = PythonStdioTransport(
        script_path="ncbi-mcp-fast.py",
        python_cmd=sys.executable,  # Use current Python interpreter
        env=os.environ.copy()  # Pass current environment
    )
    
    # Create client with explicit transport
    client = Client(transport)
    
    try:
        # Connect to the MCP server
        logger.debug("Connecting to MCP server...")
        async with client:
            logger.debug("Connected to MCP server")
            
            # List available tools
            tools = await client.list_tools()
            logger.debug(f"Available tools: {tools}")
            
            # Send the prompt to the MCP server
            logger.info("Sending prompt to MCP server...")
            try:
                # Call the process_prompt tool
                response = await client.get_prompt("process_prompt", {"prompt": prompt})
                logger.debug(f"Raw response: {response}")
                
                # Format and print the response
                print("\nResponse from MCP server:")
                formatted_response = [format_prompt_message(msg) for msg in response]
                print(json.dumps(formatted_response, indent=2))
                
                logger.info("Test completed successfully!")
            except Exception as e:
                logger.error(f"Error sending prompt: {e}")
                raise
    except asyncio.CancelledError:
        logger.warning("Test was cancelled")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error during testing: {e}", exc_info=True)
        sys.exit(1)

def main():
    # Load environment variables
    load_dotenv()
    
    # Example prompt - you can modify this or pass it as a command-line argument
    prompt = "Find information about the BRCA1 gene in humans"
    
    # If a command-line argument is provided, use it as the prompt
    if len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:])
    
    # Run the async test
    try:
        asyncio.run(test_mcp_with_prompt(prompt))
    except KeyboardInterrupt:
        logger.warning("Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main() 