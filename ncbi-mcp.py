#!/usr/bin/env python3
import sys
import json
import uuid
import requests
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from ncbi_datasets_client import NCBIDatasetsClient
import logging
import os

# Configure logging
logging.basicConfig(level=logging.DEBUG)
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
        self.client = NCBIClient()
        self.initialized = False
        logger.debug("NCBIMCP initialized")

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
        logger.debug("Initializing MCP")
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
        logger.debug("Listing tools")
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
        logger.debug(f"Calling tool with params: {params}")
        tool = params.get("tool")
        tool_params = params.get("params", {})

        if tool == "ncbi-search":
            result = self.client.esearch(
                database=tool_params["database"],
                term=tool_params["term"],
                filters=tool_params.get("filters", {})
            )
        elif tool == "ncbi-fetch":
            result = self.client.efetch(
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
        logger.debug("Listing resources")
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
    logger.debug("Starting NCBI MCP server")
    mcp = NCBIMCP()
    
    # Log system information
    logger.debug(f"Python version: {sys.version}")
    logger.debug(f"Platform: {sys.platform}")
    logger.debug(f"Working directory: {os.getcwd()}")
    logger.debug(f"Script location: {os.path.abspath(__file__)}")
    
    # Log environment variables
    logger.debug("Environment variables:")
    for key, value in os.environ.items():
        if key.startswith('PATH') or key.startswith('PYTHON'):
            logger.debug(f"  {key}: {value}")
    
    # Log Python path
    logger.debug(f"Python path: {sys.path}")
    
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                logger.debug("No more input, exiting")
                break
                
            logger.debug(f"Raw input: {line}")
            request = json.loads(line)
            logger.debug(f"Received request: {json.dumps(request, indent=2)}")
            
            response = mcp.handle_request(request)
            if response:
                logger.debug(f"Sending response: {json.dumps(response, indent=2)}")
                print(json.dumps(response))
                sys.stdout.flush()
            else:
                logger.warning("No response generated for request")
                
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON: {str(e)}")
            logger.error(f"Problematic input: {line}")
            continue
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            continue

if __name__ == "__main__":
    main()
