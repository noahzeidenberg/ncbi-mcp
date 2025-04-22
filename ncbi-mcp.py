#!/usr/bin/env python3
import sys
import json
import uuid
import requests
from datetime import datetime
from typing import Dict, List, Any, Optional
from ncbi_datasets_client import NCBIDatasetsClient

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

def main():
    # Read request from stdin
    try:
        request = json.loads(sys.stdin.read())
        print(f"DEBUG: Received request: {json.dumps(request)}", file=sys.stderr)
    except json.JSONDecodeError as e:
        print(f"DEBUG: Error decoding request: {e}", file=sys.stderr)
        print(json.dumps({"status": "error", "error": {"message": f"Invalid JSON request: {str(e)}"}}))
        return
    except Exception as e:
        print(f"DEBUG: Unexpected error reading request: {e}", file=sys.stderr)
        print(json.dumps({"status": "error", "error": {"message": f"Error reading request: {str(e)}"}}))
        return
    
    # Initialize NCBI client
    ncbi_client = NCBIClient()
    
    # Process request based on operation
    operation = request.get("operation")
    response = {"status": "ok", "data": []}
    
    try:
        if operation == "search":
            database = request.get("database")
            term = request.get("term")
            filters = request.get("filters", {})
            pagination = request.get("pagination", {})
            retstart = pagination.get("retstart", 0)
            retmax = pagination.get("retmax", 20)
            
            print(f"DEBUG: Performing search with database={database}, term={term}", file=sys.stderr)
            
            if not database or not term:
                response["status"] = "error"
                response["error"] = {"message": "Database and search term are required"}
                print(json.dumps(response))
                return
                
            search_result = ncbi_client.esearch(database, term, filters, retstart, retmax)
            print(f"DEBUG: Search result: {json.dumps(search_result)}", file=sys.stderr)
            
            if "esearchresult" in search_result and "idlist" in search_result["esearchresult"]:
                ids = search_result["esearchresult"]["idlist"]
                count = int(search_result["esearchresult"].get("count", 0))
                
                # Format response data
                for id in ids:
                    response["data"].append({"id": id})
                
                response["pagination"] = {
                    "count": count,
                    "retstart": retstart,
                    "retmax": retmax
                }
            else:
                response["status"] = "error"
                response["error"] = {"message": "Invalid search result format"}
        
        elif operation == "summary":
            database = request.get("database")
            ids = request.get("ids", [])
            fields = request.get("fields", [])
            
            if not database or not ids:
                response["status"] = "error"
                response["error"] = {"message": "Database and IDs are required"}
                print(json.dumps(response))
                return
                
            summary_result = ncbi_client.esummary(database, ids)
            
            if "result" in summary_result:
                response["data"] = normalize_summary(summary_result, fields)
            else:
                response["status"] = "error"
                response["error"] = {"message": "Invalid summary result format"}
        
        elif operation == "link":
            database = request.get("database")
            ids = request.get("ids", [])
            linkname = request.get("linkname")
            
            if not database or not ids or not linkname:
                response["status"] = "error"
                response["error"] = {"message": "Database, IDs, and linkname are required"}
                print(json.dumps(response))
                return
                
            link_result = ncbi_client.elink(database, ids, linkname)
            
            if "linksets" in link_result:
                response["data"] = link_result["linksets"]
            else:
                response["status"] = "error"
                response["error"] = {"message": "Invalid link result format"}
        
        elif operation in ["genome_metadata", "gene_metadata"]:
            # Initialize datasets client only when needed
            datasets_path = request.get("cli_paths", {}).get("datasets_path")
            dataformat_path = request.get("cli_paths", {}).get("dataformat_path")
            try:
                datasets_client = NCBIDatasetsClient(datasets_path=datasets_path, dataformat_path=dataformat_path)
            except ValueError as e:
                response["status"] = "error"
                response["error"] = {"message": str(e)}
                print(json.dumps(response))
                return
            
            if operation == "genome_metadata":
                organism = request.get("organism")
                if not organism:
                    response["status"] = "error"
                    response["error"] = {"message": "Organism parameter is required"}
                    print(json.dumps(response))
                    return
                
                try:
                    # Use the correct command format: summary genome taxon <organism>
                    result = datasets_client.get_genome_metadata(organism)
                    if result:
                        response["status"] = "ok"
                        response["data"] = result
                        response["provenance"] = {
                            "assembly_accession": result[0].get("assembly_accession")
                        }
                    else:
                        response["status"] = "error"
                        response["error"] = {"message": "No genome metadata found"}
                        print(json.dumps(response))
                        return
                except Exception as e:
                    response["status"] = "error"
                    response["error"] = {"message": str(e)}
                    print(json.dumps(response))
                    return
            
            elif operation == "gene_metadata":
                gene_id = request.get("gene_id")
                if not gene_id:
                    response["status"] = "error"
                    response["error"] = {"message": "Gene ID parameter is required"}
                    print(json.dumps(response))
                    return
                
                try:
                    # Use the correct command format: summary gene gene-id <gene_id>
                    result = datasets_client.get_gene_metadata(gene_id)
                    if result:
                        response["status"] = "ok"
                        response["data"] = result
                    else:
                        response["status"] = "error"
                        response["error"] = {"message": "No gene metadata found"}
                        print(json.dumps(response))
                        return
                except Exception as e:
                    response["status"] = "error"
                    response["error"] = {"message": str(e)}
                    print(json.dumps(response))
                    return
        
        else:
            response["status"] = "error"
            response["error"] = {"message": f"Unknown operation: {operation}"}
    
    except Exception as e:
        print(f"DEBUG: Error processing request: {e}", file=sys.stderr)
        response["status"] = "error"
        response["error"] = {"message": str(e)}
    
    print(json.dumps(response))

if __name__ == "__main__":
    main()
