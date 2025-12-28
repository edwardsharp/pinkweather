#!/usr/bin/env python3
"""
End-to-end API integration test for the preview system.
Tests the complete flow: API -> Weather parsing -> DisplayIO rendering -> PNG output
"""

import os
import sys
import tempfile
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add preview directory to path
preview_dir = Path(__file__).parent
sys.path.insert(0, str(preview_dir))

# Import preview components
from caching_http_client import CachingHTTPClient
from pygame_manager import PersistentPygameDisplay

# Import weather providers
hardware_path = preview_dir.parent / "300x400" / "CIRCUITPY"
sys.path.insert(0, str(hardware_path))

from weather.open_meteo import fetch_open_meteo_data
from weather.openweathermap import fetch_openweathermap_data


def test_openweathermap_integration():
    """Test complete OpenWeatherMap integration"""
    print("Testing OpenWeatherMap integration...")

    # Get config from environment
    api_key = os.getenv("OPENWEATHER_API_KEY")
    latitude = float(os.getenv("LATITUDE", 40.655786))
    longitude = float(os.getenv("LONGITUDE", -73.9585369))

    if not api_key:
        print("❌ Missing OPENWEATHER_API_KEY in .env file")
        return False

    print(f"   Using coordinates: {latitude}, {longitude}")
    print(f"   API key: {api_key[:8]}...")

    try:
        # Create caching HTTP client
        http_client = CachingHTTPClient()

        # Test API call (this will test caching too on second run)
        print("   Making API call...")
        config = {
            "api_key": api_key,
            "latitude": latitude,
            "longitude": longitude,
            "units": "metric",
        }
        timezone_offset = int(os.getenv("TIMEZONE_OFFSET_HOURS", -5))

        weather_data = fetch_openweathermap_data(
            http_client=http_client,
            config=config,
            timezone_offset_hours=timezone_offset,
        )

        if weather_data and weather_data.get("city"):
            print(f"   ✅ Got weather data for {weather_data['city']['name']}")
            print(
                f"   Current: {weather_data['current']['current_temp']}°F, {weather_data['current']['weather_desc']}"
            )
            print(f"   Forecast entries: {len(weather_data['forecast'])}")
        else:
            print(f"   ❌ Invalid weather data structure: {type(weather_data)}")
            return False

        # Test rendering to PNG
        print("   Testing PNG rendering...")
        output_file = "test_openweathermap.png"
        pygame_manager = PersistentPygameDisplay()

        # Convert OpenWeatherMap format to display format
        display_data = {
            "current_timestamp": weather_data["current"]["current_timestamp"],
            "forecast_data": weather_data["forecast"],
            "weather_desc": weather_data["current"]["weather_desc"],
            "day_name": "FRI",  # TODO: calculate from timestamp
            "day_num": 27,  # TODO: calculate from timestamp
            "month_name": "DEC",  # TODO: calculate from timestamp
            "air_quality": weather_data.get("air_quality", {"description": "Good"}),
            "zodiac_sign": "CAP",
            "indoor_temp_humidity": f"{weather_data['current']['current_temp']}° {weather_data['current']['humidity']}%",
        }

        output_file = pygame_manager.render_weather_data(display_data, output_file)

        # Check file was created and has reasonable size
        if Path(output_file).exists():
            file_size = Path(output_file).stat().st_size
            print(f"   ✅ PNG created: {output_file} ({file_size:,} bytes)")

            # Clean up
            pygame_manager.shutdown()
            return True
        else:
            print(f"   ❌ PNG file not created")
            pygame_manager.shutdown()
            return False

    except Exception as e:
        print(f"   ❌ Error: {e}")
        # Ensure cleanup on error
        try:
            pygame_manager.shutdown()
        except:
            pass
        return False


def test_open_meteo_integration():
    """Test complete Open-Meteo integration"""
    print("\nTesting Open-Meteo integration...")

    # Get config from environment
    latitude = float(os.getenv("LATITUDE", 40.655786))
    longitude = float(os.getenv("LONGITUDE", -73.9585369))
    timezone_offset = int(os.getenv("TIMEZONE_OFFSET_HOURS", -5))

    print(f"   Using coordinates: {latitude}, {longitude}")
    print(f"   Timezone offset: {timezone_offset} hours")

    try:
        # Create caching HTTP client
        http_client = CachingHTTPClient()

        # Test API call
        print("   Making API call...")
        weather_data = fetch_open_meteo_data(
            http_client=http_client, lat=latitude, lon=longitude
        )

        print(f"   ✅ Got weather data (Open-Meteo)")
        print(
            f"   Current: {weather_data.current_temp}°F, {weather_data.current_description}"
        )
        print(f"   Forecast entries: {len(weather_data.forecast)}")

        # Test rendering to PNG
        print("   Testing PNG rendering...")
        output_file = "test_openmeteo.png"
        pygame_manager = PersistentPygameDisplay()
        # Convert WeatherData object to dictionary format for rendering
        weather_dict = weather_data.to_display_format()
        output_file = pygame_manager.render_weather_data(weather_dict, output_file)

        # Check file was created
        if Path(output_file).exists():
            file_size = Path(output_file).stat().st_size
            print(f"   ✅ PNG created: {output_file} ({file_size:,} bytes)")

            # Clean up
            pygame_manager.shutdown()
            return True
        else:
            print(f"   ❌ PNG file not created")
            pygame_manager.shutdown()
            return False

    except Exception as e:
        print(f"   ❌ Error: {e}")
        # Ensure cleanup on error
        try:
            pygame_manager.shutdown()
        except:
            pass
        return False


def test_api_caching():
    """Test that API caching is working"""
    print("\nTesting API caching performance...")

    api_key = os.getenv("OPENWEATHER_API_KEY")
    latitude = float(os.getenv("LATITUDE", 40.655786))
    longitude = float(os.getenv("LONGITUDE", -73.9585369))

    if not api_key:
        print("❌ Missing OPENWEATHER_API_KEY for caching test")
        return False

    try:
        import time

        http_client = CachingHTTPClient()

        config = {
            "api_key": api_key,
            "latitude": latitude,
            "longitude": longitude,
            "units": "metric",
        }
        timezone_offset = int(os.getenv("TIMEZONE_OFFSET_HOURS", -5))

        # First call (should hit API)
        print("   First call (should be slow)...")
        start_time = time.time()
        weather_data1 = fetch_openweathermap_data(
            http_client=http_client,
            config=config,
            timezone_offset_hours=timezone_offset,
        )
        first_duration = time.time() - start_time

        # Second call (should hit cache)
        print("   Second call (should be fast)...")
        start_time = time.time()
        weather_data2 = fetch_openweathermap_data(
            http_client=http_client,
            config=config,
            timezone_offset_hours=timezone_offset,
        )
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
    required_vars = ["OPENWEATHER_API_KEY", "LATITUDE", "LONGITUDE"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        print("   Please check your .env file")
        return False

    # Run tests
    tests = [
        test_openweathermap_integration,
        test_open_meteo_integration,
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
