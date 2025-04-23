#!/usr/bin/env python3
import sys
import json
import uuid
import asyncio
import requests
from datetime import datetime
from typing import Dict, List, Any, Optional
from fastmcp import FastMCP, Context
from ncbi_datasets_client import NCBIDatasetsClient

# Initialize FastMCP server
mcp = FastMCP("ncbi-mcp")

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

# Initialize NCBI client
ncbi_client = NCBIClient()

@mcp.tool()
async def search(database: str, term: str, filters: Dict[str, Any] = None, 
                retstart: int = 0, retmax: int = 20, context: Context = None) -> Dict[str, Any]:
    """Search NCBI databases."""
    if not database or not term:
        return {"status": "error", "error": {"message": "Database and search term are required"}}
    
    try:
        # Run the request in a thread pool to avoid blocking
        loop = asyncio.get_running_loop()
        search_result = await loop.run_in_executor(
            None,
            lambda: ncbi_client.esearch(database, term, filters or {}, retstart, retmax)
        )
        
        if "esearchresult" in search_result and "idlist" in search_result["esearchresult"]:
            ids = search_result["esearchresult"]["idlist"]
            count = int(search_result["esearchresult"].get("count", 0))
            
            return {
                "status": "ok",
                "data": [{"id": id} for id in ids],
                "pagination": {
                    "count": count,
                    "retstart": retstart,
                    "retmax": retmax
                }
            }
        else:
            return {"status": "error", "error": {"message": "Invalid search result format"}}
    except Exception as e:
        return {"status": "error", "error": {"message": str(e)}}

@mcp.tool()
async def summary(database: str, ids: List[str], fields: List[str] = None, context: Context = None) -> Dict[str, Any]:
    """Get summary information for NCBI records."""
    if not database or not ids:
        return {"status": "error", "error": {"message": "Database and IDs are required"}}
    
    try:
        # Run the request in a thread pool to avoid blocking
        loop = asyncio.get_running_loop()
        summary_result = await loop.run_in_executor(
            None,
            lambda: ncbi_client.esummary(database, ids)
        )
        
        if "result" in summary_result:
            return {
                "status": "ok",
                "data": normalize_summary(summary_result, fields or [])
            }
        else:
            return {"status": "error", "error": {"message": "Invalid summary result format"}}
    except Exception as e:
        return {"status": "error", "error": {"message": str(e)}}

@mcp.tool()
async def link(database: str, ids: List[str], linkname: str, context: Context = None) -> Dict[str, Any]:
    """Get linked records from NCBI."""
    if not database or not ids or not linkname:
        return {"status": "error", "error": {"message": "Database, IDs, and linkname are required"}}
    
    try:
        # Run the request in a thread pool to avoid blocking
        loop = asyncio.get_running_loop()
        link_result = await loop.run_in_executor(
            None,
            lambda: ncbi_client.elink(database, ids, linkname)
        )
        
        if "linksets" in link_result:
            return {
                "status": "ok",
                "data": link_result["linksets"]
            }
        else:
            return {"status": "error", "error": {"message": "Invalid link result format"}}
    except Exception as e:
        return {"status": "error", "error": {"message": str(e)}}

@mcp.tool()
async def genome_metadata(organism: str, datasets_path: str = None, dataformat_path: str = None, context: Context = None) -> Dict[str, Any]:
    """Get genome metadata from NCBI Datasets."""
    if not organism:
        return {"status": "error", "error": {"message": "Organism parameter is required"}}
    
    try:
        # Run the request in a thread pool to avoid blocking
        loop = asyncio.get_running_loop()
        datasets_client = NCBIDatasetsClient(datasets_path=datasets_path, dataformat_path=dataformat_path)
        result = await loop.run_in_executor(
            None,
            lambda: datasets_client.get_genome_metadata(organism)
        )
        
        if result:
            return {
                "status": "ok",
                "data": result,
                "provenance": {
                    "assembly_accession": result[0].get("assembly_accession")
                }
            }
        else:
            return {"status": "error", "error": {"message": "No genome metadata found"}}
    except Exception as e:
        return {"status": "error", "error": {"message": str(e)}}

@mcp.tool()
async def gene_metadata(gene_id: str, datasets_path: str = None, dataformat_path: str = None, context: Context = None) -> Dict[str, Any]:
    """Get gene metadata from NCBI Datasets."""
    if not gene_id:
        return {"status": "error", "error": {"message": "Gene ID parameter is required"}}
    
    try:
        # Run the request in a thread pool to avoid blocking
        loop = asyncio.get_running_loop()
        datasets_client = NCBIDatasetsClient(datasets_path=datasets_path, dataformat_path=dataformat_path)
        result = await loop.run_in_executor(
            None,
            lambda: datasets_client.get_gene_metadata(gene_id)
        )
        
        if result:
            return {
                "status": "ok",
                "data": result
            }
        else:
            return {"status": "error", "error": {"message": "No gene metadata found"}}
    except Exception as e:
        return {"status": "error", "error": {"message": str(e)}}

@mcp.prompt()
async def process_prompt(prompt: str, context: Context = None) -> str:
    """Process a natural language prompt and convert it into tool calls."""
    try:
        # Extract key information from the prompt
        if "gene" in prompt.lower():
            # Search for gene information
            search_result = await search("gene", prompt, retmax=1, context=context)
            if search_result["status"] == "ok" and search_result["data"]:
                gene_id = search_result["data"][0]["id"]
                summary_result = await summary("gene", [gene_id], ["title", "summary"], context=context)
                if summary_result["status"] == "ok":
                    return json.dumps(summary_result["data"], indent=2)
        
        # Default to a basic search if no specific pattern is matched
        search_result = await search("gene", prompt, retmax=5, context=context)
        return json.dumps(search_result, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "error": {"message": str(e)}}, indent=2)

if __name__ == "__main__":
    try:
        # Run the MCP server with stdio transport
        mcp.run(transport="stdio")
    except Exception as e:
        print(f"Error running MCP server: {str(e)}", file=sys.stderr)
        sys.exit(1) 