"""
API Response Caching Module for PinkWeather Web Server
Caches OpenWeather API responses for up to 1 hour to avoid burning API credits during development
"""

import json
import os
import time
from pathlib import Path

# Cache settings
CACHE_DURATION = 3600  # 1 hour in seconds
CACHE_DIR = Path(__file__).parent / '.cache'

def ensure_cache_dir():
    """Ensure cache directory exists"""
    CACHE_DIR.mkdir(exist_ok=True)

def get_cache_filename(url):
    """Generate cache filename from URL"""
    # Create a simple hash-like filename from URL
    import hashlib
    url_hash = hashlib.md5(url.encode()).hexdigest()[:16]
    return f"weather_cache_{url_hash}.json"

def is_cache_valid(cache_file):
    """Check if cache file exists and is within cache duration"""
    if not cache_file.exists():
        return False

    file_age = time.time() - cache_file.stat().st_mtime
    return file_age < CACHE_DURATION

def load_from_cache(url):
    """Load API response from cache if valid"""
    ensure_cache_dir()
    cache_file = CACHE_DIR / get_cache_filename(url)

    if is_cache_valid(cache_file):
        try:
            with open(cache_file, 'r') as f:
                cached_data = json.load(f)
                print(f"Using cached response for {url[:60]}...")
                return cached_data
        except (json.JSONDecodeError, IOError):
            # Cache file corrupted, delete it
            cache_file.unlink(missing_ok=True)

    return None

def save_to_cache(url, response_data):
    """Save API response to cache"""
    ensure_cache_dir()
    cache_file = CACHE_DIR / get_cache_filename(url)

    try:
        with open(cache_file, 'w') as f:
            json.dump(response_data, f, indent=2)
        print(f"Cached response for {url[:60]}...")
    except IOError as e:
        print(f"Failed to cache response: {e}")

def clear_cache():
    """Clear all cached responses"""
    ensure_cache_dir()
    cache_files = list(CACHE_DIR.glob("weather_cache_*.json"))

    for cache_file in cache_files:
        try:
            cache_file.unlink()
            print(f"Deleted cache file: {cache_file.name}")
        except IOError:
            pass

    print(f"Cleared {len(cache_files)} cache files")

def get_cache_info():
    """Get information about current cache"""
    ensure_cache_dir()
    cache_files = list(CACHE_DIR.glob("weather_cache_*.json"))

    if not cache_files:
        return "No cached responses"

    info = []
    current_time = time.time()

    for cache_file in cache_files:
        file_age = current_time - cache_file.stat().st_mtime
        file_size = cache_file.stat().st_size

        if file_age < CACHE_DURATION:
            status = f"Valid ({int((CACHE_DURATION - file_age) / 60)} min remaining)"
        else:
            status = "Expired"

        info.append(f"  {cache_file.name}: {file_size} bytes, {status}")

    return f"Cache directory: {CACHE_DIR}\n" + "\n".join(info)

def cached_url_request(url):
    """Make HTTP request with caching"""
    # Try to load from cache first
    cached_response = load_from_cache(url)
    if cached_response is not None:
        return cached_response

    # Make actual HTTP request
    try:
        import urllib.request
        with urllib.request.urlopen(url) as response:
            if response.getcode() == 200:
                response_data = json.loads(response.read().decode())
                # Save to cache
                save_to_cache(url, response_data)
                print(f"Fetched fresh response for {url[:60]}...")
                return response_data
            else:
                print(f"HTTP error {response.getcode()} for {url}")
                return None
    except Exception as e:
        print(f"Request failed for {url}: {e}")
        return None

if __name__ == "__main__":
    # Command line interface for cache management
    import sys

    if len(sys.argv) > 1:
        if sys.argv[1] == "clear":
            clear_cache()
        elif sys.argv[1] == "info":
            print(get_cache_info())
        else:
            print("Usage: python api_cache.py [clear|info]")
    else:
        print("API Cache Module")
        print("================")
        print(get_cache_info())
