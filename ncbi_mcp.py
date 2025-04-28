#!/usr/bin/env python3
import sys
import json
import logging
import os
import argparse
import asyncio
import requests
import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Optional, Union
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, ListToolsRequest, CallToolRequest, TextContent
from ncbi_datasets import NCBIDatasetsClient
from ncbi_client import NCBIClient
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging - Switch to INFO level for production use
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class NCBIDatasetsClient:
    """Simple client for accessing NCBI Datasets API"""
    
    def __init__(self):
        self.base_url = "https://api.ncbi.nlm.nih.gov/datasets/v2alpha"
        self.session = requests.Session()
    
    def get_gene_metadata(self, gene_id: str) -> Dict[str, Any]:
        """Get metadata for a specific gene."""
        url = f"{self.base_url}/gene/id/{gene_id}"
        try:
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching gene metadata: {str(e)}")
            return {"error": str(e)}
    
    def get_genome_metadata(self, organism: str, reference: bool = False) -> Dict[str, Any]:
        """Get metadata for genomes matching an organism name."""
        url = f"{self.base_url}/genome/organism/{organism}"
        params = {"reference_only": "true" if reference else "false"}
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching genome metadata: {str(e)}")
            return {"error": str(e)}

class NCBIClient:
    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    
    def __init__(self, api_key: Optional[str] = None, email: Optional[str] = None):
        self.api_key = api_key
        self.email = email
        self.session = requests.Session()
        
    def _make_request(self, endpoint: str, params: Dict[str, Any], parse_as_json: bool = True) -> Union[Dict[str, Any], str]:
        """Make a request to NCBI E-utilities."""
        if self.api_key:
            params["api_key"] = self.api_key
        if self.email:
            params["email"] = self.email
            
        url = f"{self.BASE_URL}/{endpoint}"
        response = self.session.get(url, params=params)
        response.raise_for_status()
        
        if parse_as_json:
            return response.json()
        else:
            return response.text
    
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
    
    def efetch(self, database: str, ids: List[str], rettype: str = "gb") -> Union[Dict[str, Any], str]:
        """Perform an EFetch operation.
        
        Note: For many databases, XML is the most reliable return format for efetch.
        """
        params = {
            "db": database,
            "id": ",".join(ids),
            "retmode": "xml",  # Use XML mode for reliability
            "rettype": rettype
        }
        
        # For most databases, we'll want to return the raw XML/text rather than trying to parse as JSON
        return self._make_request("efetch.fcgi", params, parse_as_json=False)
    
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
    def __init__(self, api_key: str, email: str):
        self.api_key = api_key
        self.email = email
        self.http_client = NCBIClient(api_key=api_key, email=email)
        self.datasets_client = NCBIDatasetsClient()
        self.server = Server(name="ncbi-mcp", version="1.0.0")
        self._setup_handlers()

    def _setup_handlers(self):
        @self.server.list_tools()
        async def handle_list_tools() -> List[Tool]:
            return self._get_tools()

        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: Dict[str, Any] | None) -> List[TextContent]:
            return await self._handle_tool_call(name, arguments)

    async def _handle_tool_call(self, name: str, arguments: Dict[str, Any] | None) -> List[TextContent]:
        if name == "nlp-query":
            query = arguments["query"].lower()
            
            # Simple pattern matching to determine intent
            result = {}
            
            if any(term in query for term in ["article", "paper", "research", "publication", "pubmed"]):
                # PubMed search
                search_term = query.replace("find", "").replace("research articles about", "").replace("papers on", "").strip()
                result = self.http_client.esearch(
                    database="pubmed",
                    term=search_term,
                    filters={}
                )
                return [
                    TextContent(
                        type="text",
                        text=f"Searching PubMed for: {search_term}\n\n" + json.dumps(result, indent=2)
                    )
                ]
            
            elif any(term in query for term in ["gene", "genes"]):
                if "information" in query or "details" in query:
                    # Extract gene name or ID
                    gene_terms = ["gene", "information", "details", "about", "the", "get"]
                    search_term = query
                    for term in gene_terms:
                        search_term = search_term.replace(term, "").strip()
                    
                    # First try to find the gene ID
                    search_result = self.http_client.esearch(
                        database="gene",
                        term=search_term,
                        filters={}
                    )
                    
                    if "esearchresult" in search_result and int(search_result["esearchresult"].get("count", 0)) > 0:
                        gene_id = search_result["esearchresult"]["idlist"][0]
                        try:
                            result = self.datasets_client.get_gene_metadata(
                                gene_id=gene_id
                            )
                            result_json = json.dumps(result, indent=2)
                            return [
                                TextContent(
                                    type="text",
                                    text=f"Found gene information for: {search_term} (ID: {gene_id})\n\n{result_json}"
                                )
                            ]
                        except Exception as e:
                            return [
                                TextContent(
                                    type="text",
                                    text=f"Found gene ID {gene_id}, but couldn't get detailed information: {str(e)}\n\nBasic search results:\n{json.dumps(search_result, indent=2)}"
                                )
                            ]
                    else:
                        return [
                            TextContent(
                                type="text",
                                text=f"Couldn't find a gene matching: {search_term}\n\nSearch results:\n{json.dumps(search_result, indent=2)}"
                            )
                        ]
                else:
                    # General gene search
                    search_term = query.replace("find", "").replace("genes", "gene").replace("gene", "").strip()
                    result = self.http_client.esearch(
                        database="gene",
                        term=search_term,
                        filters={}
                    )
                    return [
                        TextContent(
                            type="text",
                            text=f"Searching gene database for: {search_term}\n\n" + json.dumps(result, indent=2)
                        )
                    ]
                    
            elif any(term in query for term in ["genome", "genomes", "species", "organism"]):
                # Extract organism name
                org_terms = ["genome", "genomes", "information", "about", "the", "get", "organism", "species", "for"]
                search_term = query
                for term in org_terms:
                    search_term = search_term.replace(term, "").strip()
                
                try:
                    result = self.datasets_client.get_genome_metadata(
                        organism=search_term,
                        reference=False
                    )
                    
                    if result is None:
                        return [
                            TextContent(
                                type="text",
                                text=f"No genome information found for: {search_term}"
                            )
                        ]
                    
                    result_json = json.dumps(result, indent=2)
                    return [
                        TextContent(
                            type="text",
                            text=f"Found genome information for: {search_term}\n\n{result_json}"
                        )
                    ]
                except Exception as e:
                    return [
                        TextContent(
                            type="text",
                            text=f"Error retrieving genome information for {search_term}: {str(e)}"
                        )
                    ]
            
            else:
                # Default to a general search if intent is unclear
                search_term = query
                result = self.http_client.esearch(
                    database="pubmed",
                    term=search_term,
                    filters={}
                )
                return [
                    TextContent(
                        type="text",
                        text=f"Performing general search for: {search_term}\n\n" + json.dumps(result, indent=2)
                    )
                ]
        
        elif name == "ncbi-search":
            result = self.http_client.esearch(
                database=arguments["database"],
                term=arguments["term"],
                filters=arguments.get("filters", {})
            )
        elif name == "ncbi-fetch":
            result = self.http_client.efetch(
                database=arguments["database"],
                ids=arguments["ids"],
                rettype=arguments.get("rettype", "gb")
            )
            # Result is already a string (XML or text)
            return [
                TextContent(
                    type="text",
                    text=result
                )
            ]
        elif name == "get_gene_info":
            try:
                result = self.datasets_client.get_gene_metadata(
                    gene_id=arguments["gene_id"]
                )
                
                # Handle the result, which might be a complex object
                if result is None:
                    return [
                        TextContent(
                            type="text",
                            text="No results found for the specified gene ID."
                        )
                    ]
                
                # Convert result to JSON string
                result_json = json.dumps(result, indent=2)
                return [
                    TextContent(
                        type="text",
                        text=result_json
                    )
                ]
            except Exception as e:
                return [
                    TextContent(
                        type="text",
                        text=f"Error retrieving gene information: {str(e)}"
                    )
                ]
        elif name == "get_genome_info":
            try:
                # Parse the reference parameter to handle string values
                reference = arguments.get("reference", False)
                if isinstance(reference, str):
                    reference = reference.lower() == "true"
                    
                result = self.datasets_client.get_genome_metadata(
                    organism=arguments["organism"],
                    reference=reference
                )
                
                # Handle the result, which might be a complex object
                if result is None:
                    return [
                        TextContent(
                            type="text",
                            text="No results found for the specified organism."
                        )
                    ]
                
                # Convert result to JSON string
                result_json = json.dumps(result, indent=2)
                return [
                    TextContent(
                        type="text",
                        text=result_json
                    )
                ]
            except Exception as e:
                return [
                    TextContent(
                        type="text",
                        text=f"Error retrieving genome information: {str(e)}"
                    )
                ]
        else:
            raise ValueError(f"Unknown tool: {name}")

        # For JSON results
        if isinstance(result, dict):
            return [
                TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
                )
            ]
        # For string results (like XML)
        else:
            return [
                TextContent(
                    type="text",
                    text=result
                )
            ]

    def _get_tools(self) -> List[Tool]:
        return [
            {
                "name": "nlp-query",
                "description": "Translate natural language queries to appropriate NCBI tool calls",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Natural language query about NCBI data"
                        }
                    },
                    "required": ["query"]
                },
                "examples": [
                    {
                        "example": "Find research articles about COVID-19 vaccines",
                        "arguments": {
                            "query": "Find research articles about COVID-19 vaccines"
                        }
                    },
                    {
                        "example": "Get information about the BRCA1 gene",
                        "arguments": {
                            "query": "Get information about the BRCA1 gene"
                        }
                    }
                ]
            },
            {
                "name": "ncbi-search",
                "description": "Search NCBI databases",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "database": {
                            "type": "string",
                            "description": "NCBI database to search"
                        },
                        "term": {
                            "type": "string",
                            "description": "Search term"
                        },
                        "filters": {
                            "type": "object",
                            "description": "Optional filters"
                        }
                    },
                    "required": ["database", "term"]
                },
                "examples": [
                    {
                        "example": "Search for BRCA1 in PubMed",
                        "arguments": {
                            "database": "pubmed",
                            "term": "BRCA1",
                            "filters": {}
                        }
                    },
                    {
                        "example": "Find E. coli genes",
                        "arguments": {
                            "database": "gene",
                            "term": "Escherichia coli",
                            "filters": {
                                "organism": "Escherichia coli"
                            }
                        }
                    }
                ]
            },
            {
                "name": "ncbi-fetch",
                "description": "Fetch records from NCBI",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "database": {
                            "type": "string",
                            "description": "NCBI database"
                        },
                        "ids": {
                            "type": "array",
                            "description": "List of IDs to fetch"
                        },
                        "rettype": {
                            "type": "string",
                            "description": "Return type (gb, fasta, etc.)",
                            "default": "gb"
                        }
                    },
                    "required": ["database", "ids"]
                },
                "examples": [
                    {
                        "example": "Get gene 70 from NCBI",
                        "arguments": {
                            "database": "gene",
                            "ids": ["70"]
                        }
                    },
                    {
                        "example": "Retrieve FASTA sequence for nucleotide ID NM_001126114.3",
                        "arguments": {
                            "database": "nucleotide",
                            "ids": ["NM_001126114.3"],
                            "rettype": "fasta"
                        }
                    }
                ]
            },
            {
                "name": "get_gene_info",
                "description": "Get detailed information about a specific gene using datasets.exe",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "gene_id": {
                            "type": "string",
                            "description": "NCBI Gene ID"
                        }
                    },
                    "required": ["gene_id"]
                },
                "examples": [
                    {
                        "example": "Get detailed information about the BRCA1 gene (ID: 672)",
                        "arguments": {
                            "gene_id": "672"
                        }
                    },
                    {
                        "example": "Show me information about TP53 gene (ID: 7157)",
                        "arguments": {
                            "gene_id": "7157"
                        }
                    }
                ]
            },
            {
                "name": "get_genome_info",
                "description": "Get detailed information about a specific genome using datasets.exe",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "organism": {
                            "type": "string",
                            "description": "Taxonomic name or NCBI TaxonomyID"
                        },
                        "reference": {
                            "type": "boolean",
                            "description": "Limit to reference genomes"
                        }
                    },
                    "required": ["organism"]
                },
                "examples": [
                    {
                        "example": "Get genome information for Homo sapiens",
                        "arguments": {
                            "organism": "Homo sapiens",
                            "reference": "true"
                        }
                    },
                    {
                        "example": "Show me the genome of E. coli",
                        "arguments": {
                            "organism": "Escherichia coli",
                            "reference": "false"
                        }
                    }
                ]
            }
        ]

async def main():
    parser = argparse.ArgumentParser(description="NCBI MCP Server")
    parser.add_argument("--api-key", help="NCBI API key (overrides .env)")
    parser.add_argument("--email", help="Email address for NCBI API (overrides .env)")
    args = parser.parse_args()

    # Get API key and email from args or environment variables
    api_key = args.api_key or os.getenv("NCBI_API_KEY")
    email = args.email or os.getenv("NCBI_EMAIL")

    if not api_key or not email:
        logger.error("NCBI API key and email are required. Set them in .env file or pass as arguments.")
        sys.exit(1)

    logger.debug("Starting NCBI MCP server")
    logger.debug(f"Python version: {sys.version}")
    logger.debug(f"Platform: {sys.platform}")
    logger.debug(f"Working directory: {os.getcwd()}")

    mcp = NCBIMCP(api_key=api_key, email=email)
    async with stdio_server() as (read_stream, write_stream):
        await mcp.server.run(
            read_stream,
            write_stream,
            mcp.server.create_initialization_options(),
        )

if __name__ == "__main__":
    asyncio.run(main())
