"""
Cached Weather Fetching for Web Server
Wraps the shared weather_api module with caching functionality
"""

import os
import sys

from api_cache import cached_url_request


def fetch_weather_data_cached(config=None):
    """Fetch weather data with caching for web server using OpenWeatherMap"""
    # Import openweathermap from CIRCUITPY directory
    circuitpy_path = os.path.join(
        os.path.dirname(__file__), "..", "300x400", "CIRCUITPY"
    )
    if circuitpy_path not in sys.path:
        sys.path.insert(0, circuitpy_path)

    import openweathermap

    # Get URLs from openweathermap module
    timezone_offset = config.get("timezone_offset_hours", -5)
    urls = openweathermap.get_api_urls(
        config["latitude"],
        config["longitude"],
        config["api_key"],
        config.get("units", "metric"),
    )
    if not urls:
        print("Weather API configuration incomplete")
        return None

    try:
        # Use cached requests for forecast data
        print("Fetching forecast data (with caching)...")
        forecast_response = cached_url_request(urls["forecast"])

        # Fetch air quality data with caching
        air_quality_response = None
        try:
            print("Fetching air quality data (with caching)...")
            air_quality_response = cached_url_request(urls["air_quality"])
        except Exception as e:
            print(f"Error fetching cached air quality data: {e}")

        # Parse through openweathermap module to get proper format
        return openweathermap.parse_full_response(
            forecast_response, air_quality_response, timezone_offset
        )

    except Exception as e:
        print(f"Error fetching cached weather data: {e}")
        return None
