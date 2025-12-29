"""
API response caching to avoid burning API credits
Cache responses for 1 hour
"""

import json
import time
from pathlib import Path


class APICache:
    """Simple file-based cache for API responses"""

    def __init__(self, cache_dir=".cache"):
        self.cache_dir = Path(__file__).parent.parent / cache_dir
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
            print(f"DEBUG CACHE: No cache file for {cache_key}")
            return None

        try:
            with open(cache_file) as f:
                cached_data = json.load(f)

            # Check if cache is still valid
            cached_time = cached_data.get("timestamp", 0)
            age_seconds = time.time() - cached_time
            print(
                f"DEBUG CACHE: Found cache for {cache_key}, age: {age_seconds:.1f}s (max: {self.cache_duration}s)"
            )
            if age_seconds < self.cache_duration:
                print(f"DEBUG CACHE: Cache still valid, returning cached data")
                return cached_data.get("data")
            else:
                # Cache expired
                print(f"DEBUG CACHE: Cache expired, deleting file")
                cache_file.unlink()
                return None

        except Exception:
            return None

    def set(self, provider, lat, lon, data):
        """Cache API response"""
        cache_key = self.get_cache_key(provider, lat, lon)
        cache_file = self.cache_dir / f"{cache_key}.json"

        cache_timestamp = time.time()
        cached_data = {"timestamp": cache_timestamp, "data": data}
        print(
            f"DEBUG CACHE: Caching data for {cache_key} at timestamp {cache_timestamp}"
        )

        try:
            with open(cache_file, "w") as f:
                json.dump(cached_data, f)
        except Exception:
            pass  # Fail silently if can't cache

    def clear(self):
        """Clear HTTP API cached responses (preserve weather_history.json)"""
        for cache_file in self.cache_dir.glob("*.json"):
            # Skip weather history file
            if cache_file.name == "weather_history.json":
                continue
            try:
                cache_file.unlink()
                print(f"DEBUG CACHE: Cleared cache file {cache_file.name}")
            except Exception:
                pass


# Global cache instance
api_cache = APICache()
