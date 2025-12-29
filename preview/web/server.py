"""
Enhanced preview HTTP server for PinkWeather
Supports live weather APIs (OpenWeatherMap, Open-Meteo) and historical CSV data
Focused on 400x300 display only (removed 250x122 legacy support)
"""

import json
import os
import sys
import time
import traceback
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

# Add paths for imports
current_dir = Path(__file__).parent
preview_dir = current_dir.parent
sys.path.insert(0, str(preview_dir))

from shared.data_loader import CSVWeatherLoader
from shared.image_renderer import WeatherImageRenderer
from shared.weather_history_manager import WeatherHistoryManager
from web.api_cache import api_cache


class WeatherPreviewHandler(BaseHTTPRequestHandler):
    """Enhanced HTTP request handler for weather preview functionality"""

    # Class-level shared resources
    _image_renderer = None
    _csv_loaders = {}  # Cache CSV loaders by file path
    _current_image_bytes = None  # Store current image for GET requests

    def do_GET(self):
        """Handle GET requests"""
        parsed_url = urlparse(self.path)

        if parsed_url.path == "/" or parsed_url.path == "/display":
            self.serve_html_template()
        elif parsed_url.path == "/preview":
            self.serve_current_preview()
        elif parsed_url.path == "/api/data-ranges":
            self.serve_csv_data_ranges()
        elif parsed_url.path == "/api/clear-cache":
            self.clear_api_cache()
        else:
            self.send_error(404, "Not found")

    def do_POST(self):
        """Handle POST requests"""
        if self.path == "/preview":
            self.handle_preview_generation()
        else:
            self.send_error(404, "Not found")

    def serve_html_template(self):
        """Serve the main HTML template"""
        template_path = Path(__file__).parent / "templates" / "display.html"

        try:
            with open(template_path, "r") as f:
                content = f.read()

            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(content.encode())

        except FileNotFoundError:
            self.send_error(404, "Template not found")
        except Exception as e:
            self.send_error(500, f"Error loading template: {e}")

    def serve_current_preview(self):
        """Serve current weather preview image (GET endpoint)"""
        try:
            # Serve the current cached image bytes
            if WeatherPreviewHandler._current_image_bytes:
                self.send_response(200)
                self.send_header("Content-type", "image/png")
                self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
                self.send_header("Pragma", "no-cache")
                self.send_header("Expires", "0")
                self.end_headers()
                self.wfile.write(WeatherPreviewHandler._current_image_bytes)
                return

            # If no cached image, generate one with default settings
            preview_data = self.generate_preview_from_live_api()
            if preview_data and WeatherPreviewHandler._current_image_bytes:
                self.send_response(200)
                self.send_header("Content-type", "image/png")
                self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
                self.send_header("Pragma", "no-cache")
                self.send_header("Expires", "0")
                self.end_headers()
                self.wfile.write(WeatherPreviewHandler._current_image_bytes)
                return

            self.send_error(500, "Failed to generate preview")

        except Exception as e:
            print(f"Error serving preview: {e}")
            traceback.print_exc()
            self.send_error(500, f"Preview generation error: {e}")

    def serve_csv_data_ranges(self):
        """Serve available CSV data ranges for timestamp selection"""
        try:
            ranges = {}

            # Check for common CSV files
            datasets_dir = preview_dir.parent / "datasets"
            if datasets_dir.exists():
                for csv_file in datasets_dir.glob("*.csv"):
                    try:
                        loader = self._get_csv_loader(csv_file)
                        records = loader.get_records(
                            limit=10
                        )  # Get a few records to determine range

                        if records:
                            first_timestamp = int(records[0]["timestamp"])
                            last_record = loader.get_records(
                                limit=1, offset=-1
                            )  # Get last record
                            if last_record:
                                last_timestamp = int(last_record[0]["timestamp"])
                            else:
                                last_timestamp = first_timestamp

                            # Create human readable name
                            name = csv_file.stem
                            if "nyc" in name.lower() or "40.65N73.98W" in name:
                                display_name = "New York City"
                            elif "toronto" in name.lower() or "43.70N79.40W" in name:
                                display_name = "Toronto"
                            else:
                                display_name = name.replace("-", " ").title()

                            ranges[str(csv_file)] = {
                                "name": display_name,
                                "start": first_timestamp,
                                "end": last_timestamp,
                                "start_date": datetime.fromtimestamp(
                                    first_timestamp, tz=timezone.utc
                                ).strftime("%Y-%m-%d %H:%M UTC"),
                                "end_date": datetime.fromtimestamp(
                                    last_timestamp, tz=timezone.utc
                                ).strftime("%Y-%m-%d %H:%M UTC"),
                            }
                    except Exception as e:
                        print(f"Error processing CSV {csv_file}: {e}")
                        continue

            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(ranges).encode())

        except Exception as e:
            print(f"Error serving data ranges: {e}")
            self.send_error(500, f"Data ranges error: {e}")

    def clear_api_cache(self):
        """Clear API response cache"""
        try:
            api_cache.clear()

            response = {"status": "success", "message": "API cache cleared"}

            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())

        except Exception as e:
            print(f"Error clearing cache: {e}")
            self.send_error(500, f"Cache clear error: {e}")

    def handle_preview_generation(self):
        """Handle POST request for preview generation with parameters"""
        try:
            # Parse request data
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = b""
            if content_length > 0:
                post_data = self.rfile.read(content_length)

            # Parse form data
            form_data = parse_qs(post_data.decode("utf-8"))
            print(f"Server received form data: {form_data}")

            # Extract parameters using existing form structure
            use_mock_weather = "use_mock_weather" in form_data
            api_source = form_data.get("api_source", ["openweathermap"])[0]
            mock_scenario = form_data.get("mock_scenario", ["ny_2024"])[0]
            mock_timestamp = form_data.get("mock_timestamp", [""])[0]

            # Generate preview based on use_mock_weather checkbox
            if use_mock_weather and mock_timestamp:
                # Use historical CSV data
                preview_data = self.generate_preview_from_csv_scenario(
                    mock_scenario, mock_timestamp
                )
            else:
                # Use live API data
                preview_data = self.generate_preview_from_live_api(api_source)

            if preview_data:
                # Format response to match expected JavaScript format
                response_data = {
                    "success": True,
                    "image_url": "/preview",  # JavaScript will fetch image from GET /preview
                    "display_type": "400x300",
                    "text_content": preview_data.get("narrative", ""),
                    "weather_desc": preview_data.get("weather_desc", ""),
                    "current_temp": preview_data.get("current_temp"),
                    "data_source": preview_data.get("data_source", "live"),
                    "timestamp": preview_data.get("timestamp", int(time.time())),
                }

                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(response_data).encode())
            else:
                error_response = {
                    "success": False,
                    "error": "Failed to generate preview",
                }
                self.send_response(500)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(error_response).encode())

        except Exception as e:
            print(f"Error handling preview generation: {e}")
            traceback.print_exc()

            error_response = {
                "success": False,
                "error": str(e),
                "timestamp": int(time.time()),
            }

            self.send_response(500)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(error_response).encode())

    def generate_preview_from_live_api(self, api_source="openweathermap"):
        """Generate preview using live weather API"""
        try:
            print(f"Generating preview from live {api_source} API")

            # Get image renderer
            renderer = self._get_image_renderer()

            # Get weather data from live API
            weather_data = self._get_live_weather_data(api_source)

            if not weather_data:
                raise ValueError(f"Failed to fetch weather data from {api_source}")

            # Store today's temperatures for historical comparisons (like hardware does)
            current_timestamp = int(time.time())
            current_temp = weather_data.get("current_temp")
            high_temp = weather_data.get("high_temp", current_temp)
            low_temp = weather_data.get("low_temp", current_temp)

            if current_temp is not None:
                # Import and call hardware storage function
                import sys
                from pathlib import Path

                hardware_path = (
                    Path(__file__).parent.parent.parent / "300x400" / "CIRCUITPY"
                )
                if str(hardware_path) not in sys.path:
                    sys.path.insert(0, str(hardware_path))

                from weather.weather_history import store_today_temperatures

                store_today_temperatures(
                    current_timestamp, current_temp, high_temp, low_temp
                )
                # print(
                #     f"DEBUG: Stored today's temps in live mode: {current_temp}°C (success: {success})"
                # )

            # Render to bytes using shared rendering
            from shared.image_renderer import render_weather_to_bytes

            image_bytes = render_weather_to_bytes(
                weather_data, use_icons=True, indoor_temp_humidity="20°69%"
            )

            if not image_bytes:
                raise ValueError("Failed to render weather image")

            # Store image bytes for GET /preview endpoint
            WeatherPreviewHandler._current_image_bytes = image_bytes

            return {
                "status": "success",
                "timestamp": int(time.time()),
                "weather_desc": weather_data.get("weather_desc", "Unknown"),
                "data_source": "live",
                "api_source": api_source,
                "current_temp": weather_data.get("current_temp"),
                "narrative": self._extract_narrative_from_weather_data(weather_data),
            }

        except Exception as e:
            print(f"Error generating live preview: {e}")
            traceback.print_exc()
            return None

    def generate_preview_from_csv_scenario(self, mock_scenario, timestamp_str):
        """Generate preview from historical CSV data using mock scenario"""
        try:
            print(
                f"Generating preview from scenario: {mock_scenario} at timestamp: {timestamp_str}"
            )

            if not timestamp_str:
                raise ValueError("Timestamp is required for historical data")

            timestamp = int(timestamp_str)

            # Map CSV scenarios to files
            scenario_to_csv = {
                "ny_2024": "open-meteo-40.65N73.98W25m.csv",
                "toronto_2025": "open-meteo-43.70N79.40W165m.csv",
            }

            csv_filename = scenario_to_csv.get(mock_scenario)
            if not csv_filename:
                raise ValueError(f"Unknown CSV scenario: {mock_scenario}")

            # Look for CSV file in datasets directory
            datasets_dir = preview_dir.parent / "datasets"
            csv_path = datasets_dir / csv_filename

            if not csv_path.exists():
                # Try alternative locations
                alt_paths = [
                    preview_dir.parent / csv_filename,
                    preview_dir.parent / "misc" / csv_filename,
                ]
                for alt_path in alt_paths:
                    if alt_path.exists():
                        csv_path = alt_path
                        break
                else:
                    raise FileNotFoundError(f"CSV file not found: {csv_filename}")

            # Get CSV loader
            loader = self._get_csv_loader(csv_path)

            # Find record for timestamp
            record = loader.get_record_by_timestamp(timestamp)
            if not record:
                raise ValueError(f"No data found for timestamp {timestamp}")

            # Transform record to weather data format with historical context
            weather_data = loader.transform_record(record, include_history=True)

            # Add historical context for better narratives
            historical_context = weather_data.get("historical_context", [])

            # Use history manager to enrich data
            history_manager = WeatherHistoryManager(loader)
            history_data = history_manager.get_history_for_csv_record(
                record, timestamp, historical_context
            )
            weather_data.update(history_data)

            # Set up CSV history data source directly in hardware module for historical scenarios
            history_manager.setup_csv_history_data_source()
            # print(
            #     f"DEBUG: Set up CSV history data source in hardware module for timestamp {timestamp}"
            # )

            # Get image renderer
            renderer = self._get_image_renderer()

            # Render to bytes using shared rendering
            from shared.image_renderer import render_weather_to_bytes

            image_bytes = render_weather_to_bytes(
                weather_data, use_icons=True, indoor_temp_humidity="20°69%"
            )

            if not image_bytes:
                raise ValueError("Failed to render weather image")

            # Format human-readable date
            dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
            readable_date = dt.strftime("%Y-%m-%d %H:%M:%S UTC")

            # Store image bytes for GET /preview endpoint
            WeatherPreviewHandler._current_image_bytes = image_bytes

            return {
                "status": "success",
                "timestamp": timestamp,
                "date": readable_date,
                "weather_desc": weather_data.get("weather_desc", "Unknown"),
                "data_source": "csv",
                "mock_scenario": mock_scenario,
                "current_temp": weather_data.get("current_temp"),
                "narrative": self._extract_narrative_from_weather_data(weather_data),
            }

        except Exception as e:
            print(f"Error generating CSV preview: {e}")
            traceback.print_exc()
            return None

    def _get_image_renderer(self):
        """Get or create shared image renderer"""
        if not WeatherPreviewHandler._image_renderer:
            WeatherPreviewHandler._image_renderer = WeatherImageRenderer()
        return WeatherPreviewHandler._image_renderer

    def _get_csv_loader(self, csv_path):
        """Get or create CSV loader with caching"""
        csv_path = Path(csv_path)
        cache_key = str(csv_path.absolute())

        if cache_key not in WeatherPreviewHandler._csv_loaders:
            if not csv_path.exists():
                raise FileNotFoundError(f"CSV file not found: {csv_path}")

            WeatherPreviewHandler._csv_loaders[cache_key] = CSVWeatherLoader(csv_path)

        return WeatherPreviewHandler._csv_loaders[cache_key]

    def _get_live_weather_data(self, api_source="openweathermap"):
        """Get weather data from live API using shared config and hardware modules"""
        try:
            # Use shared config
            import shared.config as preview_config
            from web.caching_http_client import CachingHTTPClient

            # DEBUG: Print config values
            print(
                f"DEBUG: TIMEZONE_OFFSET_HOURS = {preview_config.TIMEZONE_OFFSET_HOURS}"
            )
            print(f"DEBUG: LATITUDE = {preview_config.LATITUDE}")
            print(f"DEBUG: LONGITUDE = {preview_config.LONGITUDE}")

            # Verify we have necessary config
            if (
                api_source == "openweathermap"
                and not preview_config.OPENWEATHER_API_KEY
            ):
                raise ValueError("Missing OPENWEATHER_API_KEY in .env file")

            # Create HTTP client with caching
            http_client = CachingHTTPClient()

            # Convert API source name for hardware compatibility
            hardware_provider = api_source
            if api_source == "open-meteo":
                hardware_provider = "open_meteo"

            # Set provider in config
            preview_config.WEATHER_PROVIDER = hardware_provider

            # Build weather config
            WEATHER_CONFIG = {
                "latitude": preview_config.LATITUDE,
                "longitude": preview_config.LONGITUDE,
                "timezone_offset_hours": preview_config.TIMEZONE_OFFSET_HOURS,
            }

            if api_source == "openweathermap":
                WEATHER_CONFIG.update(
                    {
                        "api_key": preview_config.OPENWEATHER_API_KEY,
                        "units": "metric",
                    }
                )

            # Use hardware weather_api with our HTTP client
            hardware_path = preview_dir.parent / "300x400" / "CIRCUITPY"
            if str(hardware_path) not in sys.path:
                sys.path.insert(0, str(hardware_path))

            # Mock the hardware config module
            sys.modules["config"] = preview_config

            from weather import weather_api

            # Fetch weather data same as hardware
            forecast_data = weather_api.fetch_weather_data(WEATHER_CONFIG, http_client)
            if forecast_data:
                weather_data = weather_api.get_display_variables(forecast_data)

                # DEBUG: Print timestamp info
                if weather_data:
                    current_ts = weather_data.get("current_timestamp")
                    import time

                    current_time = time.time()
                    print(
                        f"DEBUG: Current system time = {current_time} ({time.ctime(current_time)})"
                    )
                    print(f"DEBUG: Weather API returned timestamp = {current_ts}")
                    if current_ts:
                        print(
                            f"DEBUG: Weather timestamp as date = {time.ctime(current_ts)}"
                        )
                        print(
                            f"DEBUG: Date components = {weather_data.get('day_name')} {weather_data.get('day_num')} {weather_data.get('month_name')}"
                        )

                    # DEBUG: Print forecast intervals
                    forecast_items = weather_data.get("forecast_data", [])
                    print(f"DEBUG: Forecast has {len(forecast_items)} items:")
                    for i, item in enumerate(forecast_items[:8]):  # First 8 items
                        dt = item.get("dt", 0)
                        temp = item.get("temp", "?")
                        desc = item.get("description", "")
                        is_now = item.get("is_now", False)
                        is_special = item.get("is_special", False)

                        time_str = time.ctime(dt) if dt else "No timestamp"
                        hour = time.localtime(dt).tm_hour if dt else "?"

                        marker = ""
                        if is_now:
                            marker = " [NOW]"
                        elif is_special:
                            marker = (
                                f" [SPECIAL: {item.get('special_type', 'unknown')}]"
                            )

                        print(
                            f"DEBUG:   [{i}] {hour:02d}:00 - {temp}° {desc}{marker} (ts: {dt})"
                        )

                return weather_data
            else:
                return None

        except Exception as e:
            print(f"Error fetching weather data from {api_source}: {e}")
            traceback.print_exc()
            return None

    def _extract_narrative_from_weather_data(self, weather_data):
        """Extract narrative text from weather data using shared renderer"""
        try:
            # Use the shared renderer to generate narrative
            renderer = self._get_image_renderer()

            # Generate narrative using the same method as batch processing
            hardware_path = preview_dir.parent / "300x400" / "CIRCUITPY"
            if str(hardware_path) not in sys.path:
                sys.path.insert(0, str(hardware_path))

            from display.weather_display import generate_weather_narrative

            narrative = generate_weather_narrative(weather_data)
            return narrative

        except Exception as e:
            print(f"Error extracting narrative: {e}")
            # Fallback to weather description
            return weather_data.get("weather_desc", "Weather information available")

    def log_message(self, format, *args):
        """Override to customize logging"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {format % args}")


def run_server(port=8000, host="127.0.0.1"):
    """Run the preview HTTP server"""
    server_address = (host, port)
    httpd = HTTPServer(server_address, WeatherPreviewHandler)

    print(f"🌐 PinkWeather Preview Server starting on http://{host}:{port}")
    print("📡 Available endpoints:")
    print(f"  http://{host}:{port}/              - Main display interface")
    print(f"  http://{host}:{port}/preview       - Current weather preview image")
    print(f"  http://{host}:{port}/api/data-ranges - CSV data ranges")
    print(f"  http://{host}:{port}/api/clear-cache  - Clear API cache")
    print()
    print("🔧 Supported features:")
    print("  • Live weather from OpenWeatherMap and Open-Meteo APIs")
    print("  • Historical weather from CSV datasets")
    print("  • 400x300 tri-color E-ink display rendering")
    print("  • Weather narrative generation with historical comparisons")
    print()

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down preview server...")
        httpd.shutdown()
    except Exception as e:
        print(f"💥 Server error: {e}")
        traceback.print_exc()


def main():
    """Command line interface for HTTP server"""
    import argparse

    parser = argparse.ArgumentParser(description="PinkWeather preview HTTP server")
    parser.add_argument(
        "--port", type=int, default=8000, help="Port number (default: 8000)"
    )
    parser.add_argument(
        "--host", default="127.0.0.1", help="Host address (default: 127.0.0.1)"
    )

    args = parser.parse_args()

    run_server(args.port, args.host)


if __name__ == "__main__":
    main()
