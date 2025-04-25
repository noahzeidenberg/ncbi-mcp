import requests
from typing import Dict, List, Any, Optional

class NCBIClient:
    """Client for interacting with the NCBI E-utilities API."""

    def __init__(self, api_key: Optional[str] = None, email: Optional[str] = None):
        self.api_key = api_key
        self.email = email
        self.base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

    def _build_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Build request parameters with API key and email."""
        if self.api_key:
            params["api_key"] = self.api_key
        if self.email:
            params["email"] = self.email
        params["retmode"] = "json"
        return params

    def esearch(self, database: str, term: str, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Search the NCBI database using E-utilities."""
        params = self._build_params({
            "db": database,
            "term": term,
            **(filters or {})
        })
        response = requests.get(f"{self.base_url}/esearch.fcgi", params=params)
        response.raise_for_status()
        return response.json()

    def efetch(self, database: str, ids: List[str]) -> Dict[str, Any]:
        """Fetch records from NCBI database using E-utilities."""
        params = self._build_params({
            "db": database,
            "id": ",".join(ids)
        })
        response = requests.get(f"{self.base_url}/efetch.fcgi", params=params)
        response.raise_for_status()
        return response.json() 