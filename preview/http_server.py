"""
Minimal HTTP server replacement for preview system
Serves preview/templates/display.html and handles /preview endpoint
"""

import json
import os
import sys
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from api_cache import api_cache
from pygame_manager import PersistentPygameDisplay


class SimplePreviewHandler(BaseHTTPRequestHandler):
    """Simple HTTP request handler for preview functionality"""

    def __init__(self, *args, **kwargs):
        # Initialize pygame display for preview generation
        self.pygame_display = None
        super().__init__(*args, **kwargs)

    def do_GET(self):
        """Handle GET requests"""
        parsed_url = urlparse(self.path)

        if parsed_url.path == "/" or parsed_url.path == "/display":
            self.serve_html_template()
        elif parsed_url.path == "/preview":
            self.serve_current_preview()
        elif parsed_url.path == "/clear-cache":
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
        """Serve current weather preview image"""
        try:
            # Generate fresh preview
            preview_data = self.generate_live_preview()

            if preview_data and preview_data.get("image_path"):
                image_path = Path(preview_data["image_path"])
                if image_path.exists():
                    with open(image_path, "rb") as f:
                        image_data = f.read()

                    self.send_response(200)
                    self.send_header("Content-type", "image/png")
                    self.send_header("Cache-Control", "no-cache")
                    self.end_headers()
                    self.wfile.write(image_data)

                    # Clean up temp file
                    image_path.unlink()
                    return

            self.send_error(500, "Failed to generate preview")

        except Exception as e:
            print(f"Error serving preview: {e}")
            self.send_error(500, f"Preview generation error: {e}")

    def handle_preview_generation(self):
        """Handle POST request for preview generation"""
        try:
            # Parse request data
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length > 0:
                post_data = self.rfile.read(content_length)
                # Could handle custom parameters here

            # Generate preview
            preview_data = self.generate_live_preview()

            if preview_data:
                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(preview_data).encode())
            else:
                self.send_error(500, "Failed to generate preview")

        except Exception as e:
            print(f"Error handling preview generation: {e}")
            self.send_error(500, f"Preview generation error: {e}")

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

    def generate_live_preview(self):
        """Generate live preview using current weather API"""
        try:
            # Initialize pygame display if needed
            if not self.pygame_display:
                self.pygame_display = PersistentPygameDisplay()
                self.pygame_display.start()

            # Get weather data using hardware API with caching
            weather_data = self.get_cached_weather_data()

            if not weather_data:
                return None

            # Generate temporary preview file
            temp_path = Path(__file__).parent / f"temp_preview_{int(time.time())}.png"

            # Render weather data
            self.pygame_display.render_weather_data(weather_data, temp_path)

            return {
                "status": "success",
                "image_path": str(temp_path),
                "timestamp": int(time.time()),
                "weather_desc": weather_data.get("weather_desc", "Unknown"),
            }

        except Exception as e:
            print(f"Error generating live preview: {e}")
            return None

    def get_cached_weather_data(self):
        """Get weather data with API caching"""
        # Mock config for preview (replace with actual config loading)
        config = {
            "api_key": "demo_key",
            "latitude": 40.7128,
            "longitude": -74.0060,
            "timezone_offset_hours": -5,
        }

        # Check cache first
        cached_data = api_cache.get(
            "openweathermap", config["latitude"], config["longitude"]
        )

        if cached_data:
            print("Using cached weather data")
            return cached_data

        try:
            # Import hardware weather API
            sys.path.insert(
                0, str(Path(__file__).parent.parent / "300x400" / "CIRCUITPY")
            )
            from weather import weather_api

            # Fetch fresh data (this would call real API)
            # For now, return mock data
            mock_data = {
                "current_timestamp": int(time.time()),
                "forecast_data": [
                    {"dt": int(time.time()), "temp": 22, "pop": 0.0, "icon": "01d"},
                    {
                        "dt": int(time.time()) + 86400,
                        "temp": 18,
                        "pop": 0.2,
                        "icon": "02d",
                    },
                    {
                        "dt": int(time.time()) + 172800,
                        "temp": 15,
                        "pop": 0.8,
                        "icon": "10d",
                    },
                ],
                "weather_desc": "Clear sky with light winds from the preview server",
                "day_name": "MON",
                "day_num": 15,
                "month_name": "DEC",
                "air_quality": {"aqi_text": "GOOD"},
                "zodiac_sign": "CAP",
                "indoor_temp_humidity": "21° 65%",
            }

            # Cache the result
            api_cache.set(
                "openweathermap", config["latitude"], config["longitude"], mock_data
            )

            return mock_data

        except Exception as e:
            print(f"Error fetching weather data: {e}")
            return None

    def log_message(self, format, *args):
        """Override to customize logging"""
        print(f"[{self.date_time_string()}] {format % args}")


def run_server(port=8080, host="localhost"):
    """Run the preview HTTP server"""
    server_address = (host, port)
    httpd = HTTPServer(server_address, SimplePreviewHandler)

    print(f"Preview server starting on http://{host}:{port}")
    print("Available endpoints:")
    print(f"  http://{host}:{port}/           - Main display page")
    print(f"  http://{host}:{port}/preview    - Current weather preview image")
    print(f"  http://{host}:{port}/clear-cache - Clear API cache")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down preview server...")
        httpd.shutdown()


def main():
    """Command line interface for HTTP server"""
    import argparse

    parser = argparse.ArgumentParser(description="PinkWeather preview HTTP server")
    parser.add_argument(
        "--port", type=int, default=8080, help="Port number (default: 8080)"
    )
    parser.add_argument(
        "--host", default="localhost", help="Host address (default: localhost)"
    )

    args = parser.parse_args()

    run_server(args.port, args.host)


if __name__ == "__main__":
    main()
