"""
Caching HTTP client wrapper that combines requests with API cache
"""

import hashlib
import time

from .api_cache import APICache
from .http_client import HTTPClient


class CachingHTTPClient:
    """HTTP client with automatic API response caching"""

    def __init__(self):
        self.http_client = HTTPClient()
        self.cache = APICache()

    def get(self, url):
        """Make GET request with caching"""
        # Create a cache key from the URL
        url_hash = hashlib.md5(url.encode()).hexdigest()
        provider = "http"
        lat = url_hash[:8]  # Use part of hash as fake lat/lon for cache key
        lon = url_hash[8:16]

        # Check cache first
        cached_response = self.cache.get(provider, lat, lon)
        if cached_response is not None:
            print(f"DEBUG CACHE: Cache HIT for {provider} {lat},{lon}")
            return cached_response

        print(f"DEBUG CACHE: Cache MISS for {provider} {lat},{lon} - making API call")

        # Make actual request
        print(f"DEBUG CACHE: Making HTTP request to {url}")
        response = self.http_client.get(url)

        # Cache the response
        print(f"DEBUG CACHE: Caching response for {provider} {lat},{lon}")
        self.cache.set(provider, lat, lon, response)

        return response
