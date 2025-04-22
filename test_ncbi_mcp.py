#!/usr/bin/env python3
import json
import subprocess
import uuid
import sys
import os
import argparse
from typing import Dict, Any

def run_test(request: Dict[str, Any], datasets_path: str = None, dataformat_path: str = None) -> Dict[str, Any]:
    """Run a test request through the NCBI MCP."""
    # Ensure request has a UUID
    if "request_id" not in request:
        request["request_id"] = str(uuid.uuid4())
    
    # Add paths to the request if provided
    if datasets_path or dataformat_path:
        request["cli_paths"] = {
            "datasets_path": datasets_path,
            "dataformat_path": dataformat_path
        }
    
    # Convert request to JSON and run through ncbi-mcp.py
    request_json = json.dumps(request)
    print(f"DEBUG: Sending request: {request_json}", file=sys.stderr)
    
    result = subprocess.run(
        [sys.executable, "ncbi-mcp.py"],
        input=request_json,
        capture_output=True,
        text=True,
        encoding='utf-8'
    )
    
    print(f"DEBUG: Raw stdout: {result.stdout}", file=sys.stderr)
    print(f"DEBUG: Raw stderr: {result.stderr}", file=sys.stderr)
    
    if result.returncode != 0:
        raise RuntimeError(f"Command failed with return code {result.returncode}: {result.stderr}")
    
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as e:
        print(f"DEBUG: JSON decode error: {e}", file=sys.stderr)
        print(f"DEBUG: Failed to parse: {result.stdout!r}", file=sys.stderr)
        raise

def test_search():
    """Test the search operation."""
    print("\nTesting search operation...")
    request = {
        "operation": "search",
        "database": "pubmed",
        "term": "cancer immunotherapy",
        "filters": {
            "date_range": {
                "start": "2020/01/01",
                "end": "2024/12/31"
            }
        },
        "pagination": {
            "retstart": 0,
            "retmax": 5
        }
    }
    
    response = run_test(request)
    print(f"Status: {response['status']}")
    if response['status'] == 'ok':
        print(f"Found {len(response['data'])} results")
        print(f"Total count: {response['pagination']['count']}")
        return response['data']
    else:
        print(f"Error: {response.get('error', {}).get('message', 'Unknown error')}")
        return None

def test_summary(pubmed_ids):
    """Test the summary operation."""
    if not pubmed_ids:
        print("No PubMed IDs to test summary with")
        return
        
    print("\nTesting summary operation...")
    request = {
        "operation": "summary",
        "database": "pubmed",
        "ids": [item['id'] for item in pubmed_ids[:2]],  # Test with first 2 IDs
        "fields": ["title", "abstract", "authors"]
    }
    
    response = run_test(request)
    print(f"Status: {response['status']}")
    if response['status'] == 'ok':
        print(f"Retrieved {len(response['data'])} summaries")
        for item in response['data']:
            print(f"\nTitle: {item.get('title', 'N/A')}")
            print(f"Authors: {item.get('authors', 'N/A')}")
            if 'abstract' in item:
                abstract = item['abstract'][:200] + '...' if len(item['abstract']) > 200 else item['abstract']
                print(f"Abstract: {abstract}")
    else:
        print(f"Error: {response.get('error', {}).get('message', 'Unknown error')}")

def test_link(pubmed_ids):
    """Test the link operation."""
    if not pubmed_ids:
        print("No PubMed IDs to test linking with")
        return
        
    print("\nTesting link operation...")
    request = {
        "operation": "link",
        "database": "pubmed",
        "ids": [item['id'] for item in pubmed_ids[:1]],  # Test with first ID
        "linkname": "pubmed_protein"
    }
    
    response = run_test(request)
    print(f"Status: {response['status']}")
    if response['status'] == 'ok':
        print(f"Retrieved {len(response['data'])} link sets")
        for linkset in response['data']:
            print(f"Link set: {json.dumps(linkset, indent=2)}")
    else:
        print(f"Error: {response.get('error', {}).get('message', 'Unknown error')}")

def test_biosample_search():
    """Test searching for mouse cancer immunotherapy datasets in BioSample."""
    print("\nTesting BioSample search for mouse cancer immunotherapy datasets...")
    request = {
        "operation": "search",
        "database": "biosample",
        "term": "(immunotherapy[All Fields] OR immunotherapies[All Fields]) AND (cancer[All Fields] OR tumor[All Fields] OR tumour[All Fields])",
        "filters": {
            "organism": "\"Mus musculus\""
        },
        "pagination": {
            "retstart": 0,
            "retmax": 5
        }
    }
    
    response = run_test(request)
    print(f"Status: {response['status']}")
    if response['status'] == 'ok':
        print(f"Found {len(response['data'])} results")
        print(f"Total count: {response['pagination']['count']}")
        
        # Get summaries for the found samples
        if response['data']:
            print("\nSample Details:")
            sample_ids = [item['id'] for item in response['data']]
            summary_response = run_test({
                "operation": "summary",
                "database": "biosample",
                "ids": sample_ids,
                "fields": ["accession", "title", "organism", "attribute"]
            })
            
            if summary_response['status'] == 'ok':
                for sample in summary_response['data']:
                    print(f"\nAccession: {sample.get('accession', 'N/A')}")
                    print(f"Title: {sample.get('title', 'N/A')}")
                    print(f"Organism: {sample.get('organism', 'N/A')}")
                    if 'attribute' in sample:
                        print("Attributes:")
                        for attr in sample['attribute']:
                            print(f"  - {attr}")
        
        return response['data']
    else:
        print(f"Error: {response.get('error', {}).get('message', 'Unknown error')}")
        return None

def test_gene_orthologs():
    """Test retrieving gene information and orthologs."""
    print("\nTesting gene search and ortholog retrieval...")
    
    # First search for the gene
    search_request = {
        "operation": "search",
        "database": "gene",
        "term": "ACTC1[Gene Name] AND human[Organism]",
        "pagination": {
            "retstart": 0,
            "retmax": 1
        }
    }
    
    search_response = run_test(search_request)
    if search_response['status'] != 'ok' or not search_response['data']:
        print("Error finding gene")
        return
        
    gene_id = search_response['data'][0]['id']
    
    # Get gene summary
    summary_request = {
        "operation": "summary",
        "database": "gene",
        "ids": [gene_id],
        "fields": ["name", "description", "summary", "chromosome", "map_location", "other_aliases", "organism"]
    }
    
    summary_response = run_test(summary_request)
    print("\nGene Summary:")
    if summary_response['status'] == 'ok' and summary_response['data']:
        gene_info = summary_response['data'][0]
        print(f"Name: {gene_info.get('name', 'N/A')}")
        print(f"Description: {gene_info.get('description', 'N/A')}")
        print(f"Organism: {gene_info.get('organism', 'N/A')}")
        print(f"Summary: {gene_info.get('summary', 'N/A')[:200]}...")
        print(f"Location: {gene_info.get('chromosome', 'N/A')} {gene_info.get('map_location', '')}")
        print(f"Aliases: {gene_info.get('other_aliases', 'N/A')}")
    
    # Get orthologs using HomoloGene
    ortholog_request = {
        "operation": "link",
        "database": "gene",
        "ids": [gene_id],
        "linkname": "gene_homologene_homologene"
    }
    
    ortholog_response = run_test(ortholog_request)
    print("\nOrthologs:")
    if ortholog_response['status'] == 'ok':
        print(f"Retrieved {len(ortholog_response['data'])} ortholog sets")
        for linkset in ortholog_response['data']:
            print(f"Ortholog set: {json.dumps(linkset, indent=2)}")
            
            # If we got ortholog IDs, get their summaries
            if 'linksetdbs' in linkset:
                for db in linkset['linksetdbs']:
                    if 'links' in db:
                        ortholog_ids = db['links']
                        ortholog_summary = run_test({
                            "operation": "summary",
                            "database": "gene",
                            "ids": ortholog_ids,
                            "fields": ["name", "description", "organism"]
                        })
                        if ortholog_summary['status'] == 'ok':
                            print("\nOrtholog Details:")
                            for ortholog in ortholog_summary['data']:
                                print(f"- {ortholog.get('name', 'N/A')} ({ortholog.get('organism', 'N/A')})")
    else:
        print(f"Error: {ortholog_response.get('error', {}).get('message', 'Unknown error')}")

def test_genome_metadata():
    """Test retrieving genome metadata for Mus musculus using the NCBI Datasets CLI."""
    print("\nTesting genome metadata retrieval for Mus musculus...")
    request = {
        "operation": "genome_metadata",
        "organism": "Mus musculus",
        "format_output": True
    }
    
    try:
        response = run_test(request)
        print(f"Status: {response['status']}")
        if response['status'] == 'ok':
            print("\nGenome Information:")
            for info in response['data']:
                print(f"Assembly Name: {info.get('assembly_name', 'N/A')}")
                print(f"Assembly Level: {info.get('assembly_level', 'N/A')}")
                print(f"Submission Date: {info.get('submission_date', 'N/A')}")
                print(f"Genome Size: {info.get('genome_size', 'N/A')}")
                print(f"L50: {info.get('l50', 'N/A')}")
                print(f"Total Contigs: {info.get('total_contigs', 'N/A')}")
                
                if 'formatted_data' in info:
                    print("\nFormatted Data:")
                    print(info['formatted_data'])
                    
            if 'provenance' in response:
                print(f"\nAssembly Accession: {response['provenance'].get('assembly_accession', 'N/A')}")
        else:
            print(f"Error: {response.get('error', {}).get('message', 'Unknown error')}")
            if "datasets executable not found" in response.get('error', {}).get('message', ''):
                print("Skipping test as datasets CLI is not available")
    except Exception as e:
        print(f"Error running test: {e}")
        print("Skipping test as datasets CLI is not available")

def test_gene_metadata():
    """Test retrieving gene metadata using the NCBI Datasets CLI."""
    print("\nTesting gene metadata retrieval...")
    
    try:
        # Test by gene ID
        print("\nTesting gene metadata by ID (ACTC1)...")
        request = {
            "operation": "gene_metadata",
            "gene_id": "70"  # ACTC1 gene ID
        }
        
        response = run_test(request)
        print(f"Status: {response['status']}")
        if response['status'] == 'ok':
            print(f"Retrieved {len(response['data'])} gene records")
            for gene in response['data']:
                print(f"\nGene ID: {gene.get('gene-id', 'N/A')}")
                print(f"Symbol: {gene.get('symbol', 'N/A')}")
                print(f"Name: {gene.get('name', 'N/A')}")
                print(f"Description: {gene.get('description', 'N/A')[:100]}...")
        else:
            print(f"Error: {response.get('error', {}).get('message', 'Unknown error')}")
            if "datasets executable not found" in response.get('error', {}).get('message', ''):
                print("Skipping test as datasets CLI is not available")
                return
        
        # Test by symbol and taxon
        print("\nTesting gene metadata by symbol and taxon (BRCA1 in human)...")
        request = {
            "operation": "gene_metadata",
            "symbol": "BRCA1",
            "taxon": "human"
        }
        
        response = run_test(request)
        print(f"Status: {response['status']}")
        if response['status'] == 'ok':
            print(f"Retrieved {len(response['data'])} gene records")
            for gene in response['data']:
                print(f"\nGene ID: {gene.get('gene-id', 'N/A')}")
                print(f"Symbol: {gene.get('symbol', 'N/A')}")
                print(f"Name: {gene.get('name', 'N/A')}")
                print(f"Description: {gene.get('description', 'N/A')[:100]}...")
        else:
            print(f"Error: {response.get('error', {}).get('message', 'Unknown error')}")
            if "datasets executable not found" in response.get('error', {}).get('message', ''):
                print("Skipping test as datasets CLI is not available")
    except Exception as e:
        print(f"Error running test: {e}")
        print("Skipping test as datasets CLI is not available")

def main():
    print("Starting NCBI MCP tests...")
    
    # Test basic PubMed search and operations
    print("\n=== Testing Basic PubMed Operations ===")
    pubmed_ids = test_search() or []
    test_summary(pubmed_ids)
    test_link(pubmed_ids)
    
    # Test BioSample search
    print("\n=== Testing BioSample Search ===")
    test_biosample_search()
    
    # Test gene search and orthologs
    print("\n=== Testing Gene Search and Orthologs ===")
    test_gene_orthologs()
    
    # Test genome metadata
    print("\n=== Testing Genome Metadata ===")
    test_genome_metadata()
    
    # Test gene metadata
    print("\n=== Testing Gene Metadata ===")
    test_gene_metadata()
    
    print("\nTests completed!")

if __name__ == "__main__":
    main() 