"""
Shared testing functions for preview system
"""

import sys
from pathlib import Path

# Add preview directory to path
preview_dir = Path(__file__).parent.parent
if str(preview_dir) not in sys.path:
    sys.path.insert(0, str(preview_dir))


def test_api_integration():
    """Run API integration tests"""
    try:
        from shared.test_api_integration import main

        return main()
    except Exception as e:
        print(f"API integration test failed: {e}")
        return False


def test_single_render(weather_source="live", output_file=None):
    """Test single weather render"""
    try:
        from shared.data_loader import CSVWeatherLoader
        from shared.image_renderer import WeatherImageRenderer

        if weather_source == "live":
            # Test with live API data
            import shared.config as preview_config
            from web.caching_http_client import CachingHTTPClient

            # Add hardware path for weather modules
            hardware_path = preview_dir.parent / "300x400" / "CIRCUITPY"
            if str(hardware_path) not in sys.path:
                sys.path.insert(0, str(hardware_path))

            from weather import weather_api

            if not preview_config.OPENWEATHER_API_KEY:
                print("❌ Missing OPENWEATHER_API_KEY for live test")
                return False

            # Fetch live weather data
            http_client = CachingHTTPClient()
            weather_config = {
                "api_key": preview_config.OPENWEATHER_API_KEY,
                "latitude": preview_config.LATITUDE,
                "longitude": preview_config.LONGITUDE,
                "timezone_offset_hours": preview_config.TIMEZONE_OFFSET_HOURS,
                "units": "metric",
            }

            forecast_data = weather_api.fetch_weather_data(weather_config, http_client)
            weather_data = weather_api.get_display_variables(forecast_data)

            if not weather_data:
                print("❌ Failed to fetch live weather data")
                return False

        elif weather_source.endswith(".csv"):
            # Test with CSV data
            loader = CSVWeatherLoader(weather_source)
            records = loader.get_records(limit=1)

            if not records:
                print("❌ No CSV records found")
                return False

            weather_data = loader.transform_record(records[0])

        else:
            print("❌ Invalid weather source. Use 'live' or path to CSV file")
            return False

        # Render the image
        if output_file is None:
            output_file = (
                preview_dir
                / "static"
                / f"test_render_{weather_source.replace('.csv', '').replace('/', '_')}.png"
            )

        with WeatherImageRenderer() as renderer:
            result = renderer.render_weather_data_to_file(
                weather_data,
                output_file,
                use_icons=True,
                indoor_temp_humidity="20° 45%",
            )

            if result and result.exists():
                file_size = result.stat().st_size
                print(f"✅ Rendered: {result} ({file_size:,} bytes)")
                return True
            else:
                print(f"❌ Failed to render {output_file}")
                return False

    except Exception as e:
        print(f"❌ Render test failed: {e}")
        import traceback

        traceback.print_exc()
        return False
