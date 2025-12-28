"""
API response caching to avoid burning API credits
Cache responses for 1 hour
"""

import json
import time
from pathlib import Path


class APICache:
    """Simple file-based cache for API responses"""

    def __init__(self, cache_dir="cache"):
        self.cache_dir = Path(__file__).parent / cache_dir
        self.cache_dir.mkdir(exist_ok=True)
        self.cache_duration = 3600  # 1 hour in seconds

    def get_cache_key(self, provider, lat, lon):
        """Generate cache key for location and provider"""
        return f"{provider}_{lat}_{lon}"

    def get(self, provider, lat, lon):
        """Get cached response if still valid"""
        cache_key = self.get_cache_key(provider, lat, lon)
        cache_file = self.cache_dir / f"{cache_key}.json"

        if not cache_file.exists():
            return None

        try:
            with open(cache_file) as f:
                cached_data = json.load(f)

            # Check if cache is still valid
            cached_time = cached_data.get("timestamp", 0)
            if time.time() - cached_time < self.cache_duration:
                return cached_data.get("data")
            else:
                # Cache expired
                cache_file.unlink()
                return None

        except Exception:
            return None

    def set(self, provider, lat, lon, data):
        """Cache API response"""
        cache_key = self.get_cache_key(provider, lat, lon)
        cache_file = self.cache_dir / f"{cache_key}.json"

        cached_data = {"timestamp": time.time(), "data": data}

        try:
            with open(cache_file, "w") as f:
                json.dump(cached_data, f)
        except Exception:
            pass  # Fail silently if can't cache

    def clear(self):
        """Clear all cached responses"""
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                cache_file.unlink()
            except Exception:
                pass


# Global cache instance
api_cache = APICache()
