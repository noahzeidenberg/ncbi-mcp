#!/usr/bin/env python3
import subprocess
import json
import os
import sys
from typing import Dict, Any, Optional, List
import logging

class NCBIDatasetsClient:
    """Client for interacting with NCBI Datasets CLI tools."""
    
    def __init__(self, datasets_path=None, dataformat_path=None):
        """Initialize the NCBI Datasets client.
        
        Args:
            datasets_path (str, optional): Path to the datasets executable. Defaults to '~/datasets.exe'.
            dataformat_path (str, optional): Path to the dataformat executable. Defaults to '~/dataformat.exe'.
        """
        # Get user's home directory
        home_dir = os.path.expanduser("~")
        
        # Use provided paths or default to executables in home directory
        self.datasets_path = datasets_path or os.path.join(home_dir, "datasets.exe")
        self.dataformat_path = dataformat_path or os.path.join(home_dir, "dataformat.exe")

        # Verify datasets executable
        if not self._verify_executable(self.datasets_path):
            raise ValueError(f"datasets executable not found or not accessible at {self.datasets_path}")

        # Verify dataformat executable
        if not self._verify_executable(self.dataformat_path):
            raise ValueError(f"dataformat executable not found or not accessible at {self.dataformat_path}")
            
        # Store base paths for later use
        self.datasets_dir = os.path.dirname(os.path.abspath(self.datasets_path))
        self.dataformat_dir = os.path.dirname(os.path.abspath(self.dataformat_path))
    
    def _verify_executable(self, path):
        """Verify that the executable exists and is accessible.
        
        Args:
            path (str): Path to the executable to verify.
            
        Returns:
            bool: True if executable exists and is accessible, False otherwise.
        """
        try:
            # Check if path exists and is executable
            if not os.path.exists(path):
                logging.error(f"Executable not found at path: {path}")
                return False
                
            if not os.access(path, os.X_OK):
                logging.error(f"File exists but is not executable: {path}")
                return False

            # For datasets.exe, also verify it responds to --version
            if path.endswith("datasets.exe"):
                try:
                    subprocess.run([path, "--version"], check=True, capture_output=True)
                except subprocess.CalledProcessError as e:
                    logging.error(f"Failed to verify datasets version: {e}")
                    return False
                except Exception as e:
                    logging.error(f"Unexpected error verifying datasets: {e}")
                    return False

            return True
            
        except Exception as e:
            logging.error(f"Error verifying executable {path}: {e}")
            return False
    
    def _run_command(self, command: List[str]) -> Dict[str, Any]:
        """Run a command and return the JSON output."""
        try:
            print(f"Running command: {' '.join(command)}")
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding='utf-8',  # Explicitly use UTF-8 encoding
                check=True
            )
            response = json.loads(result.stdout)
            
            # Check for error status in response
            if isinstance(response, dict) and response.get('status') == 'error':
                error_msg = response.get('error', {}).get('message', 'Unknown error')
                raise ValueError(f"NCBI Datasets API error: {error_msg}")
                
            return response
        except subprocess.CalledProcessError as e:
            print(f"Error running command: {' '.join(command)}")
            print(f"Error output: {e.stderr}")
            raise
        except json.JSONDecodeError:
            print(f"Error parsing JSON output from command: {' '.join(command)}")
            print(f"Raw output: {result.stdout}")
            raise
    
    def _parse_response(self, response: Dict[str, Any], data_type: str) -> Dict[str, Any]:
        """Parse the NCBI Datasets API response based on data type.
        
        Args:
            response (dict): Raw API response
            data_type (str): Type of data being parsed ('genome', 'gene', etc.)
            
        Returns:
            dict: Parsed response data
        """
        if not isinstance(response, dict):
            return response
            
        # Check for error status
        if response.get('status') == 'error':
            error_msg = response.get('error', {}).get('message', 'Unknown error')
            raise ValueError(f"NCBI Datasets API error: {error_msg}")
            
        # Extract data based on type
        if data_type == 'genome':
            if 'reports' in response:
                return response['reports']
            return response
            
        elif data_type == 'gene':
            if not response.get('reports'):
                return {
                    'name': 'Unknown',
                    'description': 'No description available',
                    'chromosome': 'Unknown',
                    'map_location': 'Unknown',
                    'type': 'Unknown',
                    'summary': 'No summary available'
                }
            
            # Get the query from the first report
            query = response['reports'][0].get('query', [''])[0] if response['reports'] else ''
            
            # First try to find an exact match by symbol
            for report in response['reports']:
                if 'gene' in report:
                    gene_data = report['gene']
                    if gene_data.get('symbol') == query:
                        return self._extract_gene_info(gene_data)
            
            # Then try to find a match in synonyms
            for report in response['reports']:
                if 'gene' in report:
                    gene_data = report['gene']
                    if query in gene_data.get('synonyms', []):
                        return self._extract_gene_info(gene_data)
            
            # If no match found, use the first report
            if response['reports'][0].get('gene'):
                return self._extract_gene_info(response['reports'][0]['gene'])
            
            return {
                'name': 'Unknown',
                'description': 'No description available',
                'chromosome': 'Unknown',
                'map_location': 'Unknown',
                'type': 'Unknown',
                'summary': 'No summary available'
            }
        
        return response
    
    def _extract_gene_info(self, gene_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract relevant gene information from the gene data.
        
        Args:
            gene_data (dict): Raw gene data from the API response
            
        Returns:
            dict: Extracted gene information
        """
        # Get chromosome and location information
        chromosome = gene_data.get('chromosomes', ['Unknown'])[0] if gene_data.get('chromosomes') else 'Unknown'
        map_location = 'Unknown'
        if gene_data.get('annotations'):
            for annotation in gene_data['annotations']:
                if annotation.get('genomic_locations'):
                    for location in annotation['genomic_locations']:
                        if location.get('sequence_name'):
                            map_location = location['sequence_name']
                            break
                    if map_location != 'Unknown':
                        break
        
        # Extract summary from the summary array if available
        summary = 'No summary available'
        if gene_data.get('summary'):
            summary_items = []
            for summary_item in gene_data['summary']:
                if isinstance(summary_item, dict) and 'description' in summary_item:
                    summary_items.append(summary_item['description'])
            if summary_items:
                summary = ' '.join(summary_items)
        
        return {
            'name': gene_data.get('symbol', 'Unknown'),  # Use symbol as name
            'description': gene_data.get('description', 'No description available'),
            'chromosome': chromosome,
            'map_location': map_location,
            'type': gene_data.get('type', 'Unknown'),
            'summary': summary
        }
    
    def get_genome_metadata(self, organism, reference=False, annotated=False, assembly_level=None, 
                          released_after=None, released_before=None, search=None, assembly_source="all",
                          assembly_version="latest", exclude_atypical=False, exclude_multi_isolate=False,
                          from_type=False, limit="all", mag="all", report="genome", as_json_lines=False,
                          input_file=None, tax_exact_match=False):
        """Get genome metadata for an organism.
        
        Args:
            organism (str): Taxonomic name or NCBI TaxonomyID
            reference (bool, optional): Limit to reference genomes
            annotated (bool, optional): Limit to annotated genomes
            assembly_level (str, optional): Limit to specific assembly levels (comma-separated: chromosome,complete,contig,scaffold)
            released_after (str, optional): Limit to genomes released after date (YYYY-MM-DD)
            released_before (str, optional): Limit to genomes released before date (YYYY-MM-DD)
            search (list, optional): List of search terms to filter results
            assembly_source (str, optional): Limit to 'RefSeq' or 'GenBank' genomes (default "all")
            assembly_version (str, optional): Limit to 'latest' or 'all' versions (default "latest")
            exclude_atypical (bool, optional): Exclude atypical assemblies
            exclude_multi_isolate (bool, optional): Exclude multi-isolate projects
            from_type (bool, optional): Only return records with type material
            limit (str, optional): Limit number of results ("all" or number)
            mag (str, optional): Filter metagenome assemblies ("all", "only", or "exclude")
            report (str, optional): Output type ("genome", "sequence", or "ids_only")
            as_json_lines (bool, optional): Output in JSON Lines format
            input_file (str, optional): Path to file containing taxonomy identifiers
            tax_exact_match (bool, optional): Exclude sub-species when a species-level taxon is specified
            
        Returns:
            dict: Genome metadata in JSON format
        """
        try:
            # Use the correct command structure: summary genome taxon <organism>
            command = [self.datasets_path, "summary", "genome", "taxon", organism]
            
            # Add optional filters
            if reference:
                command.append("--reference")
            if annotated:
                command.append("--annotated")
            if assembly_level:
                command.extend(["--assembly-level", assembly_level])
            if released_after:
                command.extend(["--released-after", released_after])
            if released_before:
                command.extend(["--released-before", released_before])
            if search:
                if isinstance(search, str):
                    command.extend(["--search", search])
                elif isinstance(search, (list, tuple)):
                    for term in search:
                        command.extend(["--search", term])
            if assembly_source != "all":
                command.extend(["--assembly-source", assembly_source])
            if assembly_version != "latest":
                command.extend(["--assembly-version", assembly_version])
            if exclude_atypical:
                command.append("--exclude-atypical")
            if exclude_multi_isolate:
                command.append("--exclude-multi-isolate")
            if from_type:
                command.append("--from-type")
            if limit != "all":
                command.extend(["--limit", limit])
            if mag != "all":
                command.extend(["--mag", mag])
            if report != "genome":
                command.extend(["--report", report])
            if as_json_lines:
                command.append("--as-json-lines")
            if input_file:
                command.extend(["--inputfile", input_file])
            if tax_exact_match:
                command.append("--tax-exact-match")
            
            # Log at INFO level
            logging.info(f"Getting genome metadata for {organism}")
            
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding='utf-8',
                check=True
            )
            
            try:
                response = json.loads(result.stdout)
                return self._parse_response(response, 'genome')
            except json.JSONDecodeError as e:
                logging.error(f"Failed to parse JSON: {e}")
                return {"error": "Failed to parse response", "details": str(e)}
        except subprocess.SubprocessError as e:
            logging.error(f"Error getting genome metadata: {e}")
            if hasattr(e, 'stderr'):
                logging.error(f"STDERR: {e.stderr}")
            return {"error": "Subprocess error", "details": str(e)}
    
    def get_genome_assembly(self, assembly_accession, report="genome", assembly_source="all",
                          assembly_version="latest", exclude_atypical=False, exclude_multi_isolate=False,
                          from_type=False):
        """Get detailed information about a genome assembly.
        
        Args:
            assembly_accession (str): NCBI Assembly accession (e.g., GCF_000001405.40)
            report (str, optional): Output type ("genome", "sequence", or "ids_only")
            assembly_source (str, optional): Limit to 'RefSeq' or 'GenBank' genomes
            assembly_version (str, optional): Limit to 'latest' or 'all' versions
            exclude_atypical (bool, optional): Exclude atypical assemblies
            exclude_multi_isolate (bool, optional): Exclude multi-isolate projects
            from_type (bool, optional): Only return records with type material
            
        Returns:
            dict: Assembly metadata in JSON format
        """
        try:
            command = [self.datasets_path, "summary", "genome", "accession", assembly_accession]
            
            # Add optional filters
            if report != "genome":
                command.extend(["--report", report])
            if assembly_source != "all":
                command.extend(["--assembly-source", assembly_source])
            if assembly_version != "latest":
                command.extend(["--assembly-version", assembly_version])
            if exclude_atypical:
                command.append("--exclude-atypical")
            if exclude_multi_isolate:
                command.append("--exclude-multi-isolate")
            if from_type:
                command.append("--from-type")
            
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding='utf-8',
                check=True
            )
            response = json.loads(result.stdout)
            return self._parse_response(response, 'genome')
        except subprocess.SubprocessError as e:
            print(f"Error getting genome assembly: {e}")
            return None
    
    def format_genome_data(self, assembly_data):
        """Format genome assembly data using dataformat."""
        try:
            # Write assembly data to temporary file
            with open("temp_assembly.json", "w") as f:
                json.dump(assembly_data, f)
            
            # Format the data
            result = subprocess.run(
                [self.dataformat_path, "json", "temp_assembly.json"],
                capture_output=True,
                text=True,
                check=True
            )
            
            # Clean up temporary file
            os.remove("temp_assembly.json")
            
            return {"formatted_data": result.stdout}
        except (subprocess.SubprocessError, IOError) as e:
            print(f"Error formatting genome data: {e}")
            return None
    
    def get_gene_metadata(self, gene_id, report="complete", limit="all", input_file=None, 
                         ortholog=None, as_json_lines=False, api_key=None, debug=False):
        """Get metadata for a gene by ID.
        
        Args:
            gene_id (str): NCBI Gene ID
            report (str, optional): Output type ("gene", "product", or "ids_only")
            limit (str, optional): Limit number of results ("all" or number)
            input_file (str, optional): Path to file containing gene IDs
            ortholog (list, optional): List of taxa for ortholog filtering
            as_json_lines (bool, optional): Output in JSON Lines format
            api_key (str, optional): NCBI API key
            debug (bool, optional): Enable debug output
            
        Returns:
            dict: Gene metadata in JSON format
        """
        try:
            # Use the correct command structure: summary gene gene-id <gene_id>
            command = [self.datasets_path, "summary", "gene", "gene-id", gene_id]
            
            # Add optional filters
            if report != "complete":
                command.extend(["--report", report])
            if limit != "all":
                command.extend(["--limit", limit])
            if input_file:
                command.extend(["--inputfile", input_file])
            if ortholog:
                for tax in ortholog:
                    command.extend(["--ortholog", tax])
            if as_json_lines:
                command.append("--as-json-lines")
            if api_key:
                command.extend(["--api-key", api_key])
            if debug:
                command.append("--debug")
                
            # Log at INFO level
            logging.info(f"Getting gene metadata for gene ID {gene_id}")
            
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding='utf-8',
                check=True
            )
            
            try:
                response = json.loads(result.stdout)
                return self._parse_response(response, 'gene')
            except json.JSONDecodeError as e:
                logging.error(f"Failed to parse JSON: {e}")
                return {"error": "Failed to parse response", "details": str(e)}
        except subprocess.SubprocessError as e:
            logging.error(f"Error getting gene metadata: {e}")
            if hasattr(e, 'stderr'):
                logging.error(f"STDERR: {e.stderr}")
            return {"error": "Subprocess error", "details": str(e)}
    
    def get_gene_by_symbol(self, symbol, taxon="human", report="complete", limit="all", ortholog=None):
        """Get gene metadata by symbol and taxon.
        
        Args:
            symbol (str): Gene symbol
            taxon (str, optional): Taxonomic name or NCBI TaxonomyID (default: "human")
            report (str, optional): Output type ("gene", "product", or "ids_only")
            limit (str, optional): Limit number of results ("all" or number)
            ortholog (list, optional): List of taxa for ortholog filtering
            
        Returns:
            dict: Gene metadata in JSON format
        """
        try:
            # Use the correct command structure: summary gene symbol <symbol> --taxon <taxon>
            command = [self.datasets_path, "summary", "gene", "symbol", symbol, "--taxon", taxon]
            
            # Add optional filters
            if report != "complete":
                command.extend(["--report", report])
            if limit != "all":
                command.extend(["--limit", limit])
            if ortholog:
                for tax in ortholog:
                    command.extend(["--ortholog", tax])
            
            # Try to get API key from environment
            api_key = os.environ.get("NCBI_API_KEY")
            if api_key:
                command.extend(["--api-key", api_key])
            
            print(f"\nDEBUG: Running command: {' '.join(command)}")
            
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding='utf-8',
                check=True
            )
            
            print(f"DEBUG: Command stdout: {result.stdout}")
            if result.stderr:
                print(f"DEBUG: Command stderr: {result.stderr}")
            
            # Parse the response
            response = json.loads(result.stdout)
            print(f"DEBUG: Parsed response: {json.dumps(response, indent=2)}")
            
            # Check for error status
            if isinstance(response, dict) and response.get('status') == 'error':
                error_msg = response.get('error', {}).get('message', 'Unknown error')
                raise ValueError(f"NCBI Datasets API error: {error_msg}")
            
            # Parse the response using the _parse_response method
            parsed_response = self._parse_response(response, 'gene')
            return parsed_response
            
        except subprocess.SubprocessError as e:
            print(f"Error getting gene by symbol: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON response: {e}")
            print(f"Raw output: {result.stdout}")
            return None 