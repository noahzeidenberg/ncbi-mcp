#!/usr/bin/env python3
import json
import sys
from ncbi_datasets_client import NCBIDatasetsClient
from typing import List, Dict, Optional

def get_gene_summary(symbol: str, taxon: str = "human", client: Optional[NCBIDatasetsClient] = None) -> Dict:
    """Get a summary of a gene's function and characteristics.
    
    Args:
        symbol (str): Gene symbol
        taxon (str): Taxonomic name (default: "human")
        client (NCBIDatasetsClient, optional): Existing client instance
        
    Returns:
        dict: Gene summary containing name, description, and key characteristics
    """
    if client is None:
        client = NCBIDatasetsClient()
    
    try:
        print(f"\nDEBUG: Getting gene summary for {symbol} in {taxon}")
        
        # Get gene metadata using the MCP protocol
        gene_data = client.get_gene_by_symbol(symbol, taxon)
        print(f"DEBUG: Raw gene data: {json.dumps(gene_data, indent=2)}")
        
        if not gene_data:
            print(f"DEBUG: No gene data found for {symbol}")
            return {
                "symbol": symbol,
                "error": "No data found"
            }
        
        # The response is now already parsed by the client
        # We can directly use the gene data
        summary = {
            "symbol": symbol,
            "name": gene_data.get("name", "Unknown"),
            "description": gene_data.get("description", "No description available"),
            "chromosome": gene_data.get("chromosome", "Unknown"),
            "location": gene_data.get("map_location", "Unknown"),
            "type": gene_data.get("type", "Unknown"),
            "summary": gene_data.get("summary", "No summary available")
        }
        
        print(f"DEBUG: Final summary: {json.dumps(summary, indent=2)}")
        return summary
    except Exception as e:
        print(f"DEBUG: Error getting gene summary: {str(e)}")
        return {
            "symbol": symbol,
            "error": str(e)
        }

def analyze_gene_list(genes: List[str], taxon: str = "human") -> List[Dict]:
    """Analyze a list of gene symbols and return summaries.
    
    Args:
        genes (List[str]): List of gene symbols
        taxon (str): Taxonomic name (default: "human")
        
    Returns:
        List[Dict]: List of gene summaries
    """
    client = NCBIDatasetsClient()
    summaries = []
    
    for gene in genes:
        summary = get_gene_summary(gene, taxon, client)
        summaries.append(summary)
    
    return summaries

def format_summary(summary: Dict) -> str:
    """Format a gene summary for display.
    
    Args:
        summary (Dict): Gene summary dictionary
        
    Returns:
        str: Formatted summary string
    """
    if "error" in summary:
        return f"❌ {summary['symbol']}: {summary['error']}"
    
    return f"""📌 {summary['symbol']} ({summary['name']})
   Location: {summary['chromosome']} {summary['location']}
   Type: {summary['type']}
   Description: {summary['description']}
   Summary: {summary['summary']}
"""

def main():
    # Example gene list - replace with your actual list
    genes = [
        "TP53", "BRCA1", "EGFR", "KRAS", "PTEN",
        "MYC", "CDKN2A", "PIK3CA", "APC", "VEGFA",
        "IL6", "TNF", "IFNG", "TGFB1", "CXCL8",
        "CCL2", "MMP9", "TIMP1", "VIM", "CDH1"
    ]
    
    print("🔍 Analyzing gene list...\n")
    summaries = analyze_gene_list(genes)
    
    print("📊 Gene Analysis Results:\n")
    for summary in summaries:
        print(format_summary(summary))
        print("-" * 80)

if __name__ == "__main__":
    main() 