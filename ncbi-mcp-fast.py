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

# Initialize FastMCP server with proper configuration
mcp = FastMCP(
    name="NCBI MCP",
    instructions="This server provides tools for interacting with NCBI databases.",
    protocol_version="2.0",
    capabilities={
        "logging": {
            "enabled": True,
            "level": "info"
        },
        "prompts": {
            "enabled": True
        },
        "resources": {
            "enabled": True
        },
        "tools": {
            "enabled": True
        }
    },
    server_info={
        "name": "NCBI MCP",
        "version": "1.0.0",
        "description": "Model Context Protocol server for NCBI databases"
    }
)

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
async def ncbi_search(database: str, term: str, filters: Optional[Dict[str, Any]] = None, ctx: Context = None) -> Dict[str, Any]:
    """Search NCBI databases with optional filters."""
    if ctx:
        await ctx.info(f"Searching {database} for term: {term}")
    
    params = {
        "db": database,
        "term": term,
        "retmode": "json"
    }
    
    if filters:
        params.update(filters)
    
    try:
        result = ncbi_client._make_request("esearch.fcgi", params)
        if ctx:
            await ctx.info(f"Found {result.get('esearchresult', {}).get('count', 0)} results")
        return result
    except Exception as e:
        if ctx:
            await ctx.error(f"Error searching NCBI: {str(e)}")
        raise

@mcp.tool()
async def ncbi_fetch(database: str, ids: List[str], ctx: Context = None) -> Dict[str, Any]:
    """Fetch records from NCBI using their IDs."""
    if ctx:
        await ctx.info(f"Fetching {len(ids)} records from {database}")
    
    params = {
        "db": database,
        "id": ",".join(ids),
        "retmode": "json"
    }
    
    try:
        result = ncbi_client._make_request("efetch.fcgi", params)
        if ctx:
            await ctx.info(f"Successfully fetched records")
        return result
    except Exception as e:
        if ctx:
            await ctx.error(f"Error fetching from NCBI: {str(e)}")
        raise

@mcp.resource("ncbi://databases/{database}")
async def list_databases(database: str = None, ctx: Context = None) -> List[str]:
    """List available NCBI databases or get information about a specific database."""
    if ctx:
        await ctx.info(f"Fetching information about database: {database if database else 'all databases'}")
    
    try:
        if database:
            # Get specific database info
            result = ncbi_client._make_request("einfo.fcgi", {"db": database})
            db_info = result.get("einforesult", {}).get("dbinfo", {})
            if ctx:
                await ctx.info(f"Found information for database: {database}")
            return [db_info]
        else:
            # List all databases
            result = ncbi_client._make_request("einfo.fcgi", {})
            databases = result.get("einforesult", {}).get("dblist", [])
            if ctx:
                await ctx.info(f"Found {len(databases)} databases")
            return databases
    except Exception as e:
        if ctx:
            await ctx.error(f"Error listing databases: {str(e)}")
        raise

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
        prompt_lower = prompt.lower()
        words = prompt.strip().split()
        
        # Handle gene-related queries
        if any(word in prompt_lower for word in ["gene", "protein", "enzyme", "do", "function"]):
            # Look for potential gene symbols (all uppercase words)
            gene_symbols = [word for word in words if word.isupper() and len(word) >= 2]
            
            if gene_symbols:
                # Search for the first gene symbol found with specific filters
                gene_symbol = gene_symbols[0]
                search_term = f'"{gene_symbol}"[Gene Name] AND "Homo sapiens"[Organism]'
                
                search_result = await search("gene", search_term, retmax=1, context=context)
                if search_result["status"] == "ok" and search_result["data"]:
                    gene_id = search_result["data"][0]["id"]
                    # Get detailed summary with all available fields
                    summary_result = await summary("gene", [gene_id], [
                        "title", "summary", "name", "description", "chromosome",
                        "maplocation", "type", "organism", "status"
                    ], context=context)
                    
                    if summary_result["status"] == "ok" and summary_result["data"]:
                        # Format the response in a more readable way
                        gene_info = summary_result["data"][0]
                        formatted_response = {
                            "status": "ok",
                            "data": {
                                "name": gene_info.get("name", "Unknown"),
                                "title": gene_info.get("title", "No title available"),
                                "summary": gene_info.get("summary", "No summary available"),
                                "description": gene_info.get("description", "No description available"),
                                "location": f"Chromosome {gene_info.get('chromosome', 'Unknown')}: {gene_info.get('maplocation', 'Unknown')}",
                                "type": gene_info.get("type", "Unknown"),
                                "organism": gene_info.get("organism", "Unknown"),
                                "status": gene_info.get("status", "Unknown")
                            }
                        }
                        return json.dumps(formatted_response, indent=2)
            
            # If we get here, either no gene symbol was found or search/summary failed
            return json.dumps({
                "status": "error",
                "error": {"message": "Could not find information about the specified gene"}
            }, indent=2)
        
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