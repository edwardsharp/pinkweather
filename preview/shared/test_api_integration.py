#!/usr/bin/env python3
"""
End-to-end API integration test for the preview system.
Tests the complete flow: API -> Weather parsing -> DisplayIO rendering -> PNG output
"""

import os
import sys
import tempfile
from pathlib import Path

import pygame
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add preview directory to path
preview_dir = Path(__file__).parent
sys.path.insert(0, str(preview_dir))

# Import preview components and config
import config as preview_config
from caching_http_client import CachingHTTPClient
from image_renderer import WeatherImageRenderer
from setup_filesystem import setup_preview_filesystem

# Add hardware path and mock config for weather_api
hardware_path = preview_dir.parent / "300x400" / "CIRCUITPY"
sys.path.insert(0, str(hardware_path))

# Mock the hardware config module with our preview config
sys.modules["config"] = preview_config

# Change to hardware directory before importing display modules (for font loading)
import os

original_cwd = os.getcwd()
hardware_path = preview_dir.parent / "300x400" / "CIRCUITPY"
os.chdir(hardware_path)

# Now import weather modules
from weather import weather_api


def test_openweathermap_integration(renderer=None):
    """Test complete OpenWeatherMap integration"""
    print("Testing OpenWeatherMap integration...")

    # Get config from preview config
    if not preview_config.OPENWEATHER_API_KEY:
        print("❌ Missing OPENWEATHER_API_KEY in .env file")
        return False

    print(
        f"   Using coordinates: {preview_config.LATITUDE}, {preview_config.LONGITUDE}"
    )
    print(f"   API key: {preview_config.OPENWEATHER_API_KEY[:8]}...")

    try:
        # Create caching HTTP client
        http_client = CachingHTTPClient()

        # Set provider for this test
        preview_config.WEATHER_PROVIDER = "openweathermap"

        # Use same approach as hardware code
        print("   Making API call...")
        WEATHER_CONFIG = {
            "api_key": preview_config.OPENWEATHER_API_KEY,
            "latitude": preview_config.LATITUDE,
            "longitude": preview_config.LONGITUDE,
            "timezone_offset_hours": preview_config.TIMEZONE_OFFSET_HOURS,
            "units": "metric",
        }

        # Same calls as hardware code
        forecast_data = weather_api.fetch_weather_data(WEATHER_CONFIG, http_client)
        weather_data = weather_api.get_display_variables(forecast_data)

        if weather_data:
            print(f"   ✅ Got weather data")
            print(
                f"   Current: {weather_data.get('current_temp', 0)}°C, {weather_data.get('weather_desc', 'N/A')}"
            )
            print(f"   Forecast entries: {len(weather_data.get('forecast_data', []))}")
        else:
            print(f"   ❌ No weather data returned")
            return False

        # Test rendering to PNG using centralized renderer
        print("   Testing PNG rendering...")
        output_file = Path(__file__).parent / "test_openweathermap.png"
        if renderer is None:
            renderer = WeatherImageRenderer()

        # Render using centralized renderer
        result = renderer.render_weather_data_to_file(
            weather_data,
            output_file,
            use_icons=True,
            indoor_temp_humidity=preview_config.INDOOR_TEMP_HUMIDITY,
        )

        # Check if rendering was successful
        if result and result.exists():
            file_size = result.stat().st_size
            print(f"   ✅ PNG created: {result} ({file_size:,} bytes)")

            # Only shutdown if we created our own renderer
            if renderer is None:
                renderer.shutdown()
            return True
        else:
            print(f"   ❌ PNG file not created")
            if renderer is None:
                renderer.shutdown()
            return False

    except Exception as e:
        print(f"   ❌ Error: {e}")
        # Only shutdown if we created our own renderer
        if renderer is None:
            try:
                renderer.shutdown()
            except:
                pass
        return False


def test_open_meteo_integration(renderer=None):
    """Test complete Open-Meteo integration"""
    print("\nTesting Open-Meteo integration...")

    print(
        f"   Using coordinates: {preview_config.LATITUDE}, {preview_config.LONGITUDE}"
    )
    print(f"   Timezone offset: {preview_config.TIMEZONE_OFFSET_HOURS} hours")

    try:
        # Create caching HTTP client
        http_client = CachingHTTPClient()

        # Set provider for this test
        preview_config.WEATHER_PROVIDER = "open_meteo"

        # Use same approach as hardware code
        print("   Making API call...")
        WEATHER_CONFIG = {
            "latitude": preview_config.LATITUDE,
            "longitude": preview_config.LONGITUDE,
            "timezone_offset_hours": preview_config.TIMEZONE_OFFSET_HOURS,
        }

        # Same calls as hardware code
        forecast_data = weather_api.fetch_weather_data(WEATHER_CONFIG, http_client)
        weather_data = weather_api.get_display_variables(forecast_data)

        if weather_data:
            print(f"   ✅ Got weather data")
            print(
                f"   Current: {weather_data.get('current_temp', 0)}°C, {weather_data.get('weather_desc', 'N/A')}"
            )
            print(f"   Forecast entries: {len(weather_data.get('forecast_data', []))}")
        else:
            print(f"   ❌ No weather data returned")
            return False

        # Test rendering to PNG using centralized renderer
        print("   Testing PNG rendering...")
        output_file = Path(__file__).parent / "test_openmeteo.png"
        if renderer is None:
            renderer = WeatherImageRenderer()

        # Render using centralized renderer
        result = renderer.render_weather_data_to_file(
            weather_data,
            output_file,
            use_icons=True,
            indoor_temp_humidity=preview_config.INDOOR_TEMP_HUMIDITY,
        )

        # Check if rendering was successful
        if result and result.exists():
            file_size = result.stat().st_size
            print(f"   ✅ PNG created: {result} ({file_size:,} bytes)")

            # Only shutdown if we created our own renderer
            if renderer is None:
                renderer.shutdown()
            return True
        else:
            print(f"   ❌ PNG file not created")
            if renderer is None:
                renderer.shutdown()
            return False

    except Exception as e:
        print(f"   ❌ Error: {e}")
        # Only shutdown if we created our own renderer
        if renderer is None:
            try:
                renderer.shutdown()
            except:
                pass
        return False


def test_api_caching():
    """Test that API caching is working"""
    print("\nTesting API caching performance...")

    if not preview_config.OPENWEATHER_API_KEY:
        print("❌ Missing OPENWEATHER_API_KEY for caching test")
        return False

    try:
        import time

        http_client = CachingHTTPClient()

        # Set provider for this test
        preview_config.WEATHER_PROVIDER = "openweathermap"

        WEATHER_CONFIG = {
            "api_key": preview_config.OPENWEATHER_API_KEY,
            "latitude": preview_config.LATITUDE,
            "longitude": preview_config.LONGITUDE,
            "units": "metric",
            "timezone_offset_hours": preview_config.TIMEZONE_OFFSET_HOURS,
        }

        # First call (should hit API)
        print("   First call (should be slow)...")
        start_time = time.time()
        forecast_data1 = weather_api.fetch_weather_data(WEATHER_CONFIG, http_client)
        first_duration = time.time() - start_time

        # Second call (should hit cache)
        print("   Second call (should be fast)...")
        start_time = time.time()
        forecast_data2 = weather_api.fetch_weather_data(WEATHER_CONFIG, http_client)
        second_duration = time.time() - start_time

        print(f"   First call: {first_duration:.2f}s")
        print(f"   Second call: {second_duration:.2f}s")

        if second_duration < first_duration * 0.5:  # Cache should be much faster
            print("   ✅ Caching is working!")
            return True
        else:
            print(
                "   ⚠️  Caching may not be working (second call not significantly faster)"
            )
            return False

    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


def main():
    """Run all integration tests"""
    print("🌤️  PinkWeather API Integration Test")
    print("=====================================")

    # Verify environment
    # Verify required config is loaded
    if not preview_config.OPENWEATHER_API_KEY:
        print("❌ Missing OPENWEATHER_API_KEY in .env file")
        return False
    if not preview_config.LATITUDE or not preview_config.LONGITUDE:
        print("❌ Missing LATITUDE or LONGITUDE in .env file")
        return False

    # Create single renderer to reuse across tests
    renderer = WeatherImageRenderer()

    # Run tests with shared renderer
    tests = [
        lambda: test_openweathermap_integration(renderer),
        lambda: test_open_meteo_integration(renderer),
        test_api_caching,
    ]

    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
            results.append(False)

    # Clean up renderer
    try:
        renderer.shutdown()
    except:
        pass

    # Summary
    passed = sum(results)
    total = len(results)

    print(f"\n📊 Test Results: {passed}/{total} passed")

    if all(results):
        print("🎉 All tests passed! The preview system is ready for use.")
        return True
    else:
        print("❌ Some tests failed. Please check the errors above.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
