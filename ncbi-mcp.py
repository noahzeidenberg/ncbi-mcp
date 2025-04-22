#!/usr/bin/env python3
import sys
import json
import uuid
import requests
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from ncbi_datasets_client import NCBIDatasetsClient
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NCBIClient:
    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    
    def __init__(self, api_key: Optional[str] = None, email: Optional[str] = None):
        self.api_key = api_key
        self.email = email
        self.session = requests.Session()
        
    def _make_request(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make a request to NCBI E-utilities."""
        if self.api_key:
            params["api_key"] = self.api_key
        if self.email:
            params["email"] = self.email
            
        url = f"{self.BASE_URL}/{endpoint}"
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()
    
    def esearch(self, database: str, term: str, filters: Dict[str, Any], 
                retstart: int = 0, retmax: int = 20) -> Dict[str, Any]:
        """Perform an ESearch operation."""
        params = {
            "db": database,
            "term": term,
            "retstart": retstart,
            "retmax": retmax,
            "retmode": "json"
        }
        
        # Apply filters
        if filters:
            if filters.get("organism"):
                params["term"] += f' AND {filters["organism"]}[Organism]'
            if filters.get("date_range"):
                date_range = filters["date_range"]
                if date_range.get("start"):
                    params["term"] += f' AND {date_range["start"]}:3000[Date - Publication]'
                if date_range.get("end"):
                    params["term"] += f' AND 1900:{date_range["end"]}[Date - Publication]'
            if filters.get("field"):
                params["term"] += f'[{filters["field"]}]'
                
        return self._make_request("esearch.fcgi", params)
    
    def esummary(self, database: str, ids: List[str]) -> Dict[str, Any]:
        """Perform an ESummary operation."""
        params = {
            "db": database,
            "id": ",".join(ids),
            "retmode": "json"
        }
        return self._make_request("esummary.fcgi", params)
    
    def efetch(self, database: str, ids: List[str], rettype: str = "json") -> Dict[str, Any]:
        """Perform an EFetch operation."""
        params = {
            "db": database,
            "id": ",".join(ids),
            "retmode": "json",
            "rettype": rettype
        }
        return self._make_request("efetch.fcgi", params)
    
    def elink(self, database: str, ids: List[str], linkname: str) -> Dict[str, Any]:
        """Perform an ELink operation."""
        params = {
            "db": database,
            "id": ",".join(ids),
            "linkname": linkname,
            "retmode": "json"
        }
        return self._make_request("elink.fcgi", params)

def normalize_summary(raw: Dict[str, Any], fields: List[str]) -> List[Dict[str, Any]]:
    """Normalize ESummary response into a list of records."""
    out = []
    for uid, rec in raw["result"].items():
        if uid == "uids":
            continue
        entry = {"id": uid}
        for field in fields:
            if field in rec:
                entry[field] = rec[field]
        out.append(entry)
    return out

class NCBIMCP:
    def __init__(self):
        self.client = NCBIDatasetsClient()
        self.initialized = False

    def handle_request(self, request: Union[Dict[str, Any], List[Dict[str, Any]]]) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """Handle JSON-RPC 2.0 requests."""
        try:
            # Handle batch requests
            if isinstance(request, list):
                responses = []
                for req in request:
                    response = self._handle_single_request(req)
                    if response is not None:  # Skip notifications
                        responses.append(response)
                return responses if responses else None

            # Handle single request
            return self._handle_single_request(request)

        except Exception as e:
            logger.error(f"Error handling request: {str(e)}")
            return self._error_response(None, -32000, str(e))

    def _handle_single_request(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle a single JSON-RPC 2.0 request."""
        try:
            # Validate request format
            if not isinstance(request, dict):
                return self._error_response(None, -32600, "Invalid Request")

            # Check for required fields
            if "jsonrpc" not in request or request["jsonrpc"] != "2.0":
                return self._error_response(None, -32600, "Invalid Request: jsonrpc field missing or invalid")

            if "method" not in request:
                return self._error_response(None, -32600, "Invalid Request: method field missing")

            # Extract request parameters
            request_id = request.get("id")
            method = request["method"]
            params = request.get("params", {})

            # Handle different methods
            if method == "initialize":
                return self._initialize(request_id, params)
            elif method == "tools/list":
                return self._tools_list(request_id)
            elif method == "tools/call":
                return self._tools_call(request_id, params)
            elif method == "resources/list":
                return self._resources_list(request_id)
            else:
                return self._error_response(request_id, -32601, f"Method {method} not found")

        except Exception as e:
            logger.error(f"Error handling request: {str(e)}")
            return self._error_response(request_id, -32000, str(e))

    def _initialize(self, request_id: Optional[Union[str, int]], params: Dict[str, Any]) -> Dict[str, Any]:
        """Initialize the MCP."""
        try:
            # Perform any necessary initialization
            self.initialized = True
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "capabilities": {
                        "tools": True,
                        "resources": True
                    }
                }
            }
        except Exception as e:
            return self._error_response(request_id, -32000, str(e))

    def _tools_list(self, request_id: Optional[Union[str, int]]) -> Dict[str, Any]:
        """List available tools."""
        tools = [
            {
                "name": "search_genes",
                "description": "Search for genes in NCBI databases",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query for genes"
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "get_gene_info",
                "description": "Get detailed information about a specific gene",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "gene_id": {
                            "type": "string",
                            "description": "NCBI Gene ID"
                        }
                    },
                    "required": ["gene_id"]
                }
            }
        ]
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {"tools": tools}
        }

    def _tools_call(self, request_id: Optional[Union[str, int]], params: Dict[str, Any]) -> Dict[str, Any]:
        """Call a specific tool."""
        try:
            tool_name = params.get("name")
            tool_params = params.get("parameters", {})

            if not tool_name:
                return self._error_response(request_id, -32602, "Invalid params: name is required")

            if tool_name == "search_genes":
                result = self.client.search_genes(tool_params.get("query"))
            elif tool_name == "get_gene_info":
                result = self.client.get_gene_info(tool_params.get("gene_id"))
            else:
                return self._error_response(request_id, -32601, f"Tool {tool_name} not found")

            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": result
            }
        except Exception as e:
            return self._error_response(request_id, -32000, str(e))

    def _resources_list(self, request_id: Optional[Union[str, int]]) -> Dict[str, Any]:
        """List available resources."""
        resources = [
            {
                "name": "ncbi_datasets",
                "description": "NCBI Datasets API",
                "type": "api"
            }
        ]
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {"resources": resources}
        }

    def _error_response(self, request_id: Optional[Union[str, int]], code: int, message: str) -> Dict[str, Any]:
        """Generate error response."""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": code,
                "message": message
            }
        }

def main():
    """Main entry point for the MCP."""
    mcp = NCBIMCP()
    
    # Read input from stdin
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break

            request = json.loads(line)
            response = mcp.handle_request(request)
            
            # Write response to stdout (skip notifications)
            if response is not None:
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()

        except json.JSONDecodeError:
            logger.error("Invalid JSON received")
            error_response = {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32700,
                    "message": "Parse error"
                },
                "id": None
            }
            sys.stdout.write(json.dumps(error_response) + "\n")
            sys.stdout.flush()
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            error_response = {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32000,
                    "message": str(e)
                },
                "id": None
            }
            sys.stdout.write(json.dumps(error_response) + "\n")
            sys.stdout.flush()

if __name__ == "__main__":
    main()
