#!/usr/bin/env python3
import sys
import json
import logging
import argparse
from typing import Dict, Any, Optional, Union, List

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NCBIMCP:
    def __init__(self, api_key: Optional[str] = None, email: Optional[str] = None):
        self.api_key = api_key
        self.email = email
        self.initialized = False
        logger.info("NCBIMCP initialized")

    def handle_request(self, request: Union[Dict[str, Any], List[Dict[str, Any]]]) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        logger.debug(f"Handling request: {json.dumps(request, indent=2)}")
        
        if isinstance(request, list):
            return [self._handle_single_request(req) for req in request]
        return self._handle_single_request(request)

    def _handle_single_request(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            request_id = request.get("id")
            method = request.get("method")
            params = request.get("params", {})

            logger.debug(f"Processing request: method={method}, params={params}")

            if method == "initialize":
                return self._initialize(request_id, params)
            elif method == "tools/list":
                return self._tools_list(request_id)
            elif method == "tools/call":
                return self._tools_call(request_id, params)
            elif method == "resources/list":
                return self._resources_list(request_id)
            else:
                return self._error_response(request_id, 400, f"Unknown method: {method}")
        except Exception as e:
            logger.error(f"Error handling request: {str(e)}", exc_info=True)
            return self._error_response(request.get("id"), 500, str(e))

    def _initialize(self, request_id: Optional[Union[str, int]], params: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("Initializing MCP")
        self.initialized = True
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "capabilities": params.get("capabilities", {}),
                "status": "ok",
                "message": "Initialized successfully"
            }
        }

    def _tools_list(self, request_id: Optional[Union[str, int]]) -> Dict[str, Any]:
        logger.info("Listing tools")
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "tools": {
                    "ncbi-search": {
                        "description": "Search NCBI databases",
                        "parameters": {
                            "database": {"type": "string", "description": "NCBI database to search"},
                            "term": {"type": "string", "description": "Search term"},
                            "filters": {"type": "object", "description": "Optional filters"}
                        }
                    },
                    "ncbi-fetch": {
                        "description": "Fetch records from NCBI",
                        "parameters": {
                            "database": {"type": "string", "description": "NCBI database"},
                            "ids": {"type": "array", "description": "List of IDs to fetch"}
                        }
                    }
                }
            }
        }

    def _tools_call(self, request_id: Optional[Union[str, int]], params: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"Calling tool with params: {params}")
        tool = params.get("tool")
        tool_params = params.get("params", {})

        # Import the NCBI client here to avoid circular imports
        from ncbi_datasets_client import NCBIDatasetsClient
        
        client = NCBIDatasetsClient(api_key=self.api_key, email=self.email)
        
        if tool == "ncbi-search":
            result = client.esearch(
                database=tool_params["database"],
                term=tool_params["term"],
                filters=tool_params.get("filters", {})
            )
        elif tool == "ncbi-fetch":
            result = client.efetch(
                database=tool_params["database"],
                ids=tool_params["ids"]
            )
        else:
            return self._error_response(request_id, 400, f"Unknown tool: {tool}")

        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": result
        }

    def _resources_list(self, request_id: Optional[Union[str, int]]) -> Dict[str, Any]:
        logger.info("Listing resources")
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "resources": {}
            }
        }

    def _error_response(self, request_id: Optional[Union[str, int]], code: int, message: str) -> Dict[str, Any]:
        logger.error(f"Error: {message}")
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": code,
                "message": message
            }
        }

def main():
    parser = argparse.ArgumentParser(description="NCBI MCP Server")
    parser.add_argument("--api-key", help="NCBI API key")
    parser.add_argument("--email", help="Email for NCBI API")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    logger.info("Starting NCBI MCP server")
    mcp = NCBIMCP(api_key=args.api_key, email=args.email)
    
    # Log system information
    logger.debug(f"Python version: {sys.version}")
    logger.debug(f"Platform: {sys.platform}")
    
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                logger.debug("No more input, exiting")
                break
                
            logger.debug(f"Raw input: {line}")
            request = json.loads(line)
            response = mcp.handle_request(request)
            
            if response:
                logger.debug(f"Raw output: {json.dumps(response)}")
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()
                
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON: {e}")
            sys.stderr.write(f"Error decoding JSON: {e}\n")
            sys.stderr.flush()
        except Exception as e:
            logger.error(f"Error processing request: {e}", exc_info=True)
            sys.stderr.write(f"Error processing request: {e}\n")
            sys.stderr.flush()

if __name__ == "__main__":
    main() 