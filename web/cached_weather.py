"""
Cached Weather Fetching for Web Server
Wraps the shared weather_api module with caching functionality
"""

import os
import sys
from api_cache import cached_url_request

def fetch_weather_data_cached(config=None):
    """Fetch weather data with caching for web server - only forecast endpoint needed"""
    # Import weather_api from CIRCUITPY directory
    circuitpy_path = os.path.join(os.path.dirname(__file__), '..', '300x400', 'CIRCUITPY')
    if circuitpy_path not in sys.path:
        sys.path.insert(0, circuitpy_path)

    import weather_api

    # Get URLs from weather_api
    urls = weather_api.get_weather_urls(config)
    if not urls:
        print("Weather API configuration incomplete")
        return None

    forecast_data = None

    try:
        # Use cached requests for forecast only (includes current weather in first item)
        print("Fetching forecast data (with caching)...")
        forecast_data = cached_url_request(urls['forecast'])

    except Exception as e:
        print(f"Error fetching cached weather data: {e}")

    return forecast_data
