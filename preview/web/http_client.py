"""
HTTP client for weather API requests using standard Python requests
"""


class HTTPClient:
    """HTTP client using standard Python requests library"""

    def get(self, url):
        """Make GET request and return JSON response"""
        import requests

        response = requests.get(url)
        response.raise_for_status()
        return response.json()
