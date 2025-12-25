"""
Weather Display Development Server

A localhost web server for developing and testing weather display layouts.
Provides a web interface to input text and preview the rendered e-ink display.
"""

import base64
import io
import json
import os
import sys
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

# Add parent directory to path to import shared modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import os

from cached_weather import fetch_weather_data_cached
from mock_history import compute_mock_history, store_real_weather_history
from mock_weather_data import generate_scenario_data, get_predefined_scenarios
from open_meteo_converter import get_historical_data_range
from simple_web_render import (
    render_250x122_display,
    render_400x300_display,
    render_400x300_weather_layout,
)

# Weather API functions are imported locally where needed
from web_adapter import get_mock_csv_data, get_mock_sensor_data, get_mock_system_status


# Load environment variables from .env file
def load_dotenv():
    """Load environment variables from .env file"""
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key] = value
        print(f"Loaded environment variables from {env_file}")
    else:
        print(f"No .env file found at {env_file}")


# Load .env on module import
load_dotenv()


class DisplayHandler(BaseHTTPRequestHandler):
    # Store current image data in memory
    current_image_data = None

    def do_GET(self):
        """Handle GET requests - serve the main interface."""
        if self.path == "/" or self.path == "/index.html":
            self.serve_index()
        elif self.path.startswith("/current_image.png"):
            self.serve_current_image()
        elif self.path == "/api/data-ranges":
            self.serve_data_ranges()
        elif self.path == "/api/clear-cache":
            self.clear_cache()
        else:
            self.send_error(404, "File not found")

    def do_POST(self):
        """Handle POST requests - process form data and generate preview."""
        if self.path == "/preview":
            self.handle_preview_post()
        else:
            self.send_error(404, "File not found")

    def serve_index(self):
        """Serve the main HTML interface from template file."""
        try:
            # Get the directory where this script is located
            script_dir = os.path.dirname(os.path.abspath(__file__))
            template_path = os.path.join(script_dir, "templates", "display.html")

            with open(template_path, "r", encoding="utf-8") as f:
                html = f.read()

            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(html.encode("utf-8"))
        except FileNotFoundError:
            self.send_error(500, "Template file not found")
        except Exception as e:
            self.send_error(500, f"Error loading template: {str(e)}")

    def serve_current_image(self):
        """Serve the current generated image as PNG."""
        if DisplayHandler.current_image_data is None:
            # Generate default display with mock data (250x122)
            sensor_data = get_mock_sensor_data()
            csv_data = get_mock_csv_data("normal")
            system_status = get_mock_system_status("normal")

            image = render_250x122_display(
                sensor_data["temp_c"], sensor_data["humidity"], csv_data, system_status
            )

            img_buffer = io.BytesIO()
            image.save(img_buffer, format="PNG")
            DisplayHandler.current_image_data = img_buffer.getvalue()

        self.send_response(200)
        self.send_header("Content-type", "image/png")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.end_headers()
        self.wfile.write(DisplayHandler.current_image_data)

    def serve_data_ranges(self):
        """Serve data ranges for historical datasets as JSON."""
        try:
            ranges = {}

            # Get New York 2024 data range
            try:
                ny_start, ny_end = get_historical_data_range("ny_2024")
                if ny_start and ny_end:
                    ranges["ny_2024"] = {
                        "start": ny_start,
                        "end": ny_end,
                        "name": "New York 2024",
                    }
            except Exception as e:
                print(f"Error getting NY data range: {e}")

            # Get Toronto 2025 data range
            try:
                toronto_start, toronto_end = get_historical_data_range("toronto_2025")
                if toronto_start and toronto_end:
                    ranges["toronto_2025"] = {
                        "start": toronto_start,
                        "end": toronto_end,
                        "name": "Toronto 2025",
                    }
            except Exception as e:
                print(f"Error getting Toronto data range: {e}")

            response = {"success": True, "ranges": ranges}

            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode("utf-8"))

        except Exception as e:
            self.send_response(500)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            error_response = {"success": False, "error": str(e)}
            self.wfile.write(json.dumps(error_response).encode("utf-8"))

    def clear_cache(self):
        """Clear weather history cache for testing."""
        try:
            cache_dir = "web/.cache"
            history_file = os.path.join(cache_dir, "weather_history.json")

            if os.path.exists(history_file):
                os.remove(history_file)
                message = "Weather history cache cleared"
            else:
                message = "No cache file found"

            response = {"success": True, "message": message}
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode("utf-8"))

        except Exception as e:
            self.send_response(500)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            error_response = {"success": False, "error": str(e)}
            self.wfile.write(json.dumps(error_response).encode("utf-8"))

    def handle_preview_post(self):
        """Handle POST request to generate weather display preview and return JSON."""
        try:
            # Parse URL-encoded form data
            content_length = int(self.headers["Content-Length"])
            post_data = self.rfile.read(content_length)
            form_data = urllib.parse.parse_qs(post_data.decode("utf-8"))

            print(f"Server received form data: {form_data}")

            # Get display type
            display_type = form_data.get("display_type", ["250x122"])[0]

            # Debug checkbox detection
            use_mock_weather = "use_mock_weather" in form_data
            print(
                f"Display type: {display_type}, Mock weather checkbox detected: {use_mock_weather}"
            )

            if display_type == "400x300":
                # Handle 400x300 display with full weather layout
                use_mock_weather = "use_mock_weather" in form_data
                current_weather = None
                forecast_data = None
                weather_desc = None
                current_timestamp = None

                if use_mock_weather:
                    # Use shared weather engine for mock weather
                    mock_scenario = form_data.get("mock_scenario", ["winter_storm"])[0]
                    mock_timestamp = form_data.get("mock_timestamp", [""])[0]

                    print(
                        f"Mock weather enabled: scenario={mock_scenario}, timestamp={mock_timestamp}"
                    )

                    try:
                        timestamp = int(mock_timestamp)
                    except ValueError:
                        raise ValueError("Invalid mock timestamp provided")

                    # Use shared weather engine (reusing working logic)
                    from shared_weather_engine import (
                        generate_weather_display_for_timestamp,
                    )

                    csv_path = os.path.join(
                        os.path.dirname(__file__),
                        "..",
                        "misc",
                        "open-meteo-40.65N73.98W25m.csv",
                    )

                    try:
                        parsed_mock_data, narrative, display_vars, current_weather = (
                            generate_weather_display_for_timestamp(csv_path, timestamp)
                        )

                        # Store data for full layout rendering
                        forecast_data = display_vars["forecast_data"]
                        weather_desc = (
                            narrative if narrative else "Weather data unavailable"
                        )
                        current_timestamp = current_weather.get("current_timestamp")

                        print(
                            f"Generated weather narrative ({len(narrative)} chars): {narrative[:100]}..."
                        )

                    except Exception as e:
                        print(f"Error in shared weather engine: {e}")
                        import traceback

                        traceback.print_exc()
                        weather_desc = (
                            f"Mock weather scenario: {mock_scenario} (error: {str(e)})"
                        )
                else:
                    # Use real weather API, fall back to mock on any error
                    api_key = os.getenv("OPENWEATHER_API_KEY")
                    if api_key:
                        try:
                            config = {
                                "api_key": api_key,
                                "latitude": float(os.getenv("LATITUDE", 40.7128)),
                                "longitude": float(os.getenv("LONGITUDE", -74.0060)),
                                "timezone_offset_hours": int(
                                    os.getenv("TIMEZONE_OFFSET_HOURS", -5)
                                ),
                                "units": "metric",
                            }
                            forecast_data = fetch_weather_data_cached(config)

                            if forecast_data:
                                # Add 300x400/CIRCUITPY to path for weather modules
                                circuitpy_path = os.path.join(
                                    os.path.dirname(__file__),
                                    "..",
                                    "300x400",
                                    "CIRCUITPY",
                                )
                                if circuitpy_path not in sys.path:
                                    sys.path.insert(0, circuitpy_path)

                                # Parse real weather data
                                from weather_api import (
                                    get_display_variables,
                                    parse_current_weather_from_forecast,
                                )
                                from weather_narrative import get_weather_narrative

                                # Extract forecast data if new format
                                actual_forecast_data = forecast_data
                                air_quality_data = None
                                if (
                                    isinstance(forecast_data, dict)
                                    and "forecast" in forecast_data
                                ):
                                    actual_forecast_data = forecast_data["forecast"]
                                    air_quality_data = forecast_data.get("air_quality")

                                current_weather = parse_current_weather_from_forecast(
                                    forecast_data
                                )
                                display_vars = get_display_variables(forecast_data)

                                # Store today's temperatures in history for tomorrow's comparison
                                if current_weather:
                                    try:
                                        store_real_weather_history(
                                            current_weather.get("current_timestamp"),
                                            current_weather.get("current_temp"),
                                            current_weather.get("high_temp"),
                                            current_weather.get("low_temp"),
                                        )
                                    except Exception as e:
                                        print(f"Failed to store weather history: {e}")

                                # For real weather data, monkey-patch weather_narrative directly
                                import weather_narrative
                                from mock_history import compare_with_yesterday_web

                                print(
                                    "DEBUG: About to override compare_with_yesterday in weather_narrative for real weather"
                                )
                                # Override the imported function in weather_narrative module
                                original_compare = (
                                    weather_narrative.compare_with_yesterday
                                )
                                weather_narrative.compare_with_yesterday = (
                                    lambda ct, ht, lt, ts: compare_with_yesterday_web(
                                        ct, ht, lt, ts, use_mock=False
                                    )
                                )

                                try:
                                    print(
                                        "DEBUG: About to call get_weather_narrative for REAL weather"
                                    )
                                    print(
                                        f"DEBUG: current_temp = {current_weather.get('current_temp')}"
                                    )
                                    print(
                                        f"DEBUG: timestamp = {current_weather.get('current_timestamp')}"
                                    )
                                    narrative = get_weather_narrative(
                                        current_weather,
                                        display_vars["forecast_data"],
                                        current_weather.get("current_timestamp"),
                                    )
                                finally:
                                    # Restore original function
                                    weather_narrative.compare_with_yesterday = (
                                        original_compare
                                    )

                                if current_weather and display_vars.get(
                                    "forecast_data"
                                ):
                                    # Store data for full layout rendering
                                    forecast_data = display_vars["forecast_data"]
                                    weather_desc = (
                                        narrative
                                        if narrative is not None
                                        else "Weather data unavailable"
                                    )
                                    current_timestamp = current_weather.get(
                                        "current_timestamp"
                                    )
                                    print(
                                        f"Generated real weather narrative ({len(narrative)} chars):"
                                    )
                                    print("Raw narrative with tags:")
                                    print(repr(narrative))
                                    print("Display narrative:")
                                    print(narrative)

                                    # Also show what the text looks like after tag processing
                                    try:
                                        from text_renderer import TextRenderer

                                        renderer = TextRenderer()
                                        segments = renderer.parse_markup(narrative)
                                        parsed_text = "".join(
                                            [seg[0] for seg in segments]
                                        )
                                        print("After tag parsing:")
                                        print(repr(parsed_text))
                                        print("Visible text:")
                                        print(parsed_text)

                                        # Font metrics debugging
                                        try:
                                            from adafruit_bitmap_font import bitmap_font
                                            from adafruit_display_text import label

                                            vollkorn_font = bitmap_font.load_font(
                                                "vollkorn20reg.pcf"
                                            )
                                            hyperl_font = bitmap_font.load_font(
                                                "hyperl20reg.pcf"
                                            )

                                            print("Font metrics comparison:")

                                            # Test degree symbol specifically
                                            v_degree = label.Label(
                                                vollkorn_font, text="°", color=0x000000
                                            )
                                            h_degree = label.Label(
                                                hyperl_font, text="°", color=0x000000
                                            )

                                            print(
                                                f"Vollkorn '°' bounding box: {v_degree.bounding_box}"
                                            )
                                            print(
                                                f"Hyperlegible '°' bounding box: {h_degree.bounding_box}"
                                            )

                                            # Test number with degree
                                            v_temp = label.Label(
                                                vollkorn_font, text="3°", color=0x000000
                                            )
                                            h_temp = label.Label(
                                                hyperl_font, text="3°", color=0x000000
                                            )

                                            print(
                                                f"Vollkorn '3°' bounding box: {v_temp.bounding_box}"
                                            )
                                            print(
                                                f"Hyperlegible '3°' bounding box: {h_temp.bounding_box}"
                                            )

                                        except Exception as e:
                                            print(f"Font metrics debug failed: {e}")

                                        # Check for extra spaces around degree symbols
                                        # if "°" in parsed_text:
                                        #     print("Degree symbol analysis:")
                                        #     for i, char in enumerate(parsed_text):
                                        #         if char == "°":
                                        #             before = (
                                        #                 parsed_text[i - 2 : i]
                                        #                 if i >= 2
                                        #                 else parsed_text[:i]
                                        #             )
                                        #             after = (
                                        #                 parsed_text[i + 1 : i + 3]
                                        #                 if i < len(parsed_text) - 2
                                        #                 else parsed_text[i + 1 :]
                                        #             )
                                        #             print(
                                        #                 f"  Position {i}: '{before}°{after}'"
                                        #             )
                                    except Exception as e:
                                        print(f"Tag parsing debug failed: {e}")
                                else:
                                    raise Exception(
                                        "Real weather parsing returned None"
                                    )
                            else:
                                raise Exception("Failed to fetch real weather data")
                        except Exception as e:
                            print(f"Real weather failed: {e}")
                            weather_desc = f"Real weather API failed: {str(e)}"
                            # Try to preserve air quality data even if weather parsing failed
                            preserved_air_quality = None
                            if isinstance(forecast_data, dict) and forecast_data.get(
                                "air_quality"
                            ):
                                try:
                                    from weather_api import parse_air_quality

                                    preserved_air_quality = parse_air_quality(
                                        forecast_data["air_quality"]
                                    )
                                except:
                                    pass
                            forecast_data = None
                            current_timestamp = None
                    else:
                        print("No API key configured")
                        weather_desc = (
                            "No API key configured - cannot fetch weather data"
                        )
                        forecast_data = None
                        current_timestamp = None

                print(f"Rendering 400x300 weather layout...")
                if weather_desc:
                    # Get date info from display_vars if available
                    day_name = (
                        display_vars.get("day_name")
                        if "display_vars" in locals()
                        else None
                    )
                    day_num = (
                        display_vars.get("day_num")
                        if "display_vars" in locals()
                        else None
                    )
                    month_name = (
                        display_vars.get("month_name")
                        if "display_vars" in locals()
                        else None
                    )

                    # Debug air quality data flow
                    air_quality_data = None
                    zodiac_data = None
                    if "display_vars" in locals():
                        air_quality_data = display_vars.get("air_quality")
                        zodiac_data = display_vars.get("zodiac_sign")
                        print(
                            f"DEBUG HTTP: display_vars has air_quality: {air_quality_data}"
                        )
                        print(f"DEBUG HTTP: display_vars has zodiac: {zodiac_data}")
                    elif "preserved_air_quality" in locals():
                        air_quality_data = preserved_air_quality
                        print(
                            f"DEBUG HTTP: using preserved air_quality: {air_quality_data}"
                        )
                    else:
                        print("DEBUG HTTP: No air quality data available")

                    image = render_400x300_weather_layout(
                        current_weather=current_weather,
                        forecast_data=forecast_data,
                        weather_desc=weather_desc,
                        current_timestamp=current_timestamp,
                        day_name=day_name,
                        day_num=day_num,
                        month_name=month_name,
                        air_quality=air_quality_data,
                        zodiac_sign=zodiac_data,
                    )
                else:
                    # Fallback to text renderer if no weather description
                    image = render_400x300_display("No weather data available")

                response_data = {
                    "success": True,
                    "image_url": "/current_image.png",
                    "display_type": "400x300",
                    "text_content": weather_desc or "No weather data",
                }
            else:
                # Handle 250x122 display (original logic)
                csv_scenario = form_data.get("csv_scenario", ["normal"])[0]
                status_scenario = form_data.get("status_scenario", ["normal"])[0]

                # Override sensor data if provided
                sensor_data = get_mock_sensor_data()
                if "temp_c" in form_data and form_data["temp_c"][0]:
                    try:
                        sensor_data["temp_c"] = float(form_data["temp_c"][0])
                    except ValueError:
                        pass

                if "humidity" in form_data and form_data["humidity"][0]:
                    try:
                        sensor_data["humidity"] = float(form_data["humidity"][0])
                    except ValueError:
                        pass

                # Get mock data based on scenarios
                csv_data = get_mock_csv_data(csv_scenario)
                system_status = get_mock_system_status(status_scenario)

                # Generate display using shared renderer (same as hardware)
                image = render_250x122_display(
                    sensor_data["temp_c"],
                    sensor_data["humidity"],
                    csv_data,
                    system_status,
                )

                response_data = {
                    "success": True,
                    "image_url": "/current_image.png",
                    "display_type": "250x122",
                    "sensor_data": sensor_data,
                    "system_status": system_status,
                }

            # Store image data in memory for serving
            img_buffer = io.BytesIO()
            image.save(img_buffer, format="PNG")
            DisplayHandler.current_image_data = img_buffer.getvalue()

            print(
                f"Display generated ({display_type}), image size: {len(DisplayHandler.current_image_data)} bytes"
            )

            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
            self.end_headers()
            self.wfile.write(json.dumps(response_data).encode("utf-8"))

        except Exception as e:
            print(f"Error generating preview: {e}")
            response_data = {"success": False, "error": str(e)}
            self.send_response(500)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response_data).encode("utf-8"))


def run_server(port=8000):
    """Start the development server."""
    server_address = ("", port)
    httpd = HTTPServer(server_address, DisplayHandler)

    print(f"PinkWeather Development Server")
    print(f"Server running at http://localhost:{port}")
    print("Press Ctrl+C to stop the server")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        httpd.shutdown()


if __name__ == "__main__":
    run_server()
