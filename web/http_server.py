"""
Weather Display Development Server

A localhost web server for developing and testing weather display layouts.
Provides a web interface to input text and preview the rendered e-ink display.
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
import base64
import io
import os
import json
import sys
import time
from pathlib import Path

# Add parent directory to path to import shared modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web_adapter import (
    get_mock_sensor_data, get_mock_csv_data, get_mock_system_status
)
from simple_web_render import render_250x122_display, render_400x300_display, render_400x300_weather_layout
from mock_weather_data import generate_scenario_data, get_predefined_scenarios
from cached_weather import fetch_weather_data_cached
import os

# Load environment variables from .env file
def load_dotenv():
    """Load environment variables from .env file"""
    env_file = Path(__file__).parent / '.env'
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
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
        if self.path == '/' or self.path == '/index.html':
            self.serve_index()
        elif self.path.startswith('/current_image.png'):
            self.serve_current_image()
        else:
            self.send_error(404, "File not found")

    def do_POST(self):
        """Handle POST requests - process form data and generate preview."""
        if self.path == '/preview':
            self.handle_preview_post()
        else:
            self.send_error(404, "File not found")



    def serve_index(self):
        """Serve the main HTML interface from template file."""
        try:
            # Get the directory where this script is located
            script_dir = os.path.dirname(os.path.abspath(__file__))
            template_path = os.path.join(script_dir, 'templates', 'display.html')

            with open(template_path, 'r', encoding='utf-8') as f:
                html = f.read()

            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(html.encode('utf-8'))
        except FileNotFoundError:
            self.send_error(500, "Template file not found")
        except Exception as e:
            self.send_error(500, f"Error loading template: {str(e)}")

    def serve_current_image(self):
        """Serve the current generated image as PNG."""
        if DisplayHandler.current_image_data is None:
            # Generate default display with mock data (250x122)
            sensor_data = get_mock_sensor_data()
            csv_data = get_mock_csv_data('normal')
            system_status = get_mock_system_status('normal')

            image = render_250x122_display(
                sensor_data['temp_c'],
                sensor_data['humidity'],
                csv_data,
                system_status
            )

            img_buffer = io.BytesIO()
            image.save(img_buffer, format='PNG')
            DisplayHandler.current_image_data = img_buffer.getvalue()

        self.send_response(200)
        self.send_header('Content-type', 'image/png')
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        self.end_headers()
        self.wfile.write(DisplayHandler.current_image_data)

    def handle_preview_post(self):
        """Handle POST request to generate weather display preview and return JSON."""
        try:
            # Parse URL-encoded form data
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            form_data = urllib.parse.parse_qs(post_data.decode('utf-8'))

            print(f"Server received form data: {form_data}")

            # Get display type
            display_type = form_data.get('display_type', ['250x122'])[0]

            # Debug checkbox detection
            use_mock_weather = 'use_mock_weather' in form_data
            print(f"Display type: {display_type}, Mock weather checkbox detected: {use_mock_weather}")

            if display_type == '400x300':
                # Handle 400x300 display with full weather layout
                use_mock_weather = 'use_mock_weather' in form_data
                current_weather = None
                forecast_data = None
                weather_desc = None
                current_timestamp = None

                if use_mock_weather:
                    # Use real weather parsing pipeline with mock data
                    mock_scenario = form_data.get('mock_scenario', ['winter_storm'])[0]
                    mock_timestamp = form_data.get('mock_timestamp', [''])[0]

                    print(f"Mock weather enabled: scenario={mock_scenario}, timestamp={mock_timestamp}")

                    try:
                        timestamp = int(mock_timestamp)
                    except ValueError:
                        raise ValueError("Invalid mock timestamp provided")

                    # Generate mock weather data
                    mock_data = generate_scenario_data(mock_scenario, timestamp)
                    print(f"Generated mock data for {mock_data['city']['name']}")

                    # Generate weather narrative using real pipeline
                    try:
                        # Add 300x400/CIRCUITPY to path for weather modules
                        circuitpy_path = os.path.join(os.path.dirname(__file__), '..', '300x400', 'CIRCUITPY')
                        if circuitpy_path not in sys.path:
                            sys.path.insert(0, circuitpy_path)

                        from weather_narrative import get_weather_narrative
                        from weather_api import parse_current_weather_from_forecast, get_display_variables

                        # Parse weather data
                        current_weather = parse_current_weather_from_forecast(mock_data, -5)
                        display_vars = get_display_variables(mock_data, -5)

                        if current_weather and display_vars.get('forecast_data'):
                            narrative = get_weather_narrative(
                                current_weather,
                                display_vars['forecast_data'],
                                current_weather.get('current_timestamp')
                            )
                            # Store data for full layout rendering
                            forecast_data = display_vars['forecast_data']
                            weather_desc = narrative
                            current_timestamp = current_weather.get('current_timestamp')
                            print(f"Generated weather narrative ({len(narrative)} chars): {narrative[:100]}...")
                        else:
                            weather_desc = f"Mock weather scenario: {mock_scenario} (weather parsing failed)"
                            print("Weather parsing returned None - using fallback text")

                    except Exception as e:
                        print(f"Error in weather narrative pipeline: {e}")
                        import traceback
                        traceback.print_exc()
                        weather_desc = f"Mock weather scenario: {mock_scenario} (error: {str(e)})"
                else:
                    # Use real weather API, fall back to mock on any error
                    api_key = os.getenv('OPENWEATHER_API_KEY')
                    if api_key:
                        try:
                            config = {
                                'api_key': api_key,
                                'latitude': float(os.getenv('LATITUDE', 40.7128)),
                                'longitude': float(os.getenv('LONGITUDE', -74.0060)),
                                'timezone_offset_hours': int(os.getenv('TIMEZONE_OFFSET_HOURS', -5)),
                                'units': 'metric'
                            }
                            forecast_data = fetch_weather_data_cached(config)

                            if forecast_data:
                                # Add 300x400/CIRCUITPY to path for weather modules
                                circuitpy_path = os.path.join(os.path.dirname(__file__), '..', '300x400', 'CIRCUITPY')
                                if circuitpy_path not in sys.path:
                                    sys.path.insert(0, circuitpy_path)

                                from weather_narrative import get_weather_narrative
                                from weather_api import parse_current_weather_from_forecast, get_display_variables

                                # Parse real weather data
                                current_weather = parse_current_weather_from_forecast(forecast_data, config['timezone_offset_hours'])
                                display_vars = get_display_variables(forecast_data, config['timezone_offset_hours'])

                                if current_weather and display_vars.get('forecast_data'):
                                    narrative = get_weather_narrative(
                                        current_weather,
                                        display_vars['forecast_data'],
                                        current_weather.get('current_timestamp')
                                    )
                                    # Store data for full layout rendering
                                    forecast_data = display_vars['forecast_data']
                                    weather_desc = narrative
                                    current_timestamp = current_weather.get('current_timestamp')
                                    print(f"Generated real weather narrative ({len(narrative)} chars): {narrative[:100]}...")
                                else:
                                    raise Exception("Real weather parsing returned None")
                            else:
                                raise Exception("Failed to fetch real weather data")
                        except Exception as e:
                            print(f"Real weather failed: {e}")
                            weather_desc = f"Real weather API failed: {str(e)}"
                            forecast_data = None
                            current_timestamp = None
                    else:
                        print("No API key configured")
                        weather_desc = "No API key configured - cannot fetch weather data"
                        forecast_data = None
                        current_timestamp = None

                print(f"Rendering 400x300 weather layout...")
                if weather_desc:
                    # Get date info from display_vars if available
                    day_name = display_vars.get('day_name') if 'display_vars' in locals() else None
                    day_num = display_vars.get('day_num') if 'display_vars' in locals() else None
                    month_name = display_vars.get('month_name') if 'display_vars' in locals() else None

                    image = render_400x300_weather_layout(
                        current_weather=current_weather,
                        forecast_data=forecast_data,
                        weather_desc=weather_desc,
                        current_timestamp=current_timestamp,
                        day_name=day_name,
                        day_num=day_num,
                        month_name=month_name
                    )
                else:
                    # Fallback to text renderer if no weather description
                    image = render_400x300_display("No weather data available")

                response_data = {
                    'success': True,
                    'image_url': '/current_image.png',
                    'display_type': '400x300',
                    'text_content': weather_desc or "No weather data"
                }
            else:
                # Handle 250x122 display (original logic)
                csv_scenario = form_data.get('csv_scenario', ['normal'])[0]
                status_scenario = form_data.get('status_scenario', ['normal'])[0]

                # Override sensor data if provided
                sensor_data = get_mock_sensor_data()
                if 'temp_c' in form_data and form_data['temp_c'][0]:
                    try:
                        sensor_data['temp_c'] = float(form_data['temp_c'][0])
                    except ValueError:
                        pass

                if 'humidity' in form_data and form_data['humidity'][0]:
                    try:
                        sensor_data['humidity'] = float(form_data['humidity'][0])
                    except ValueError:
                        pass

                # Get mock data based on scenarios
                csv_data = get_mock_csv_data(csv_scenario)
                system_status = get_mock_system_status(status_scenario)

                # Generate display using shared renderer (same as hardware)
                image = render_250x122_display(
                    sensor_data['temp_c'],
                    sensor_data['humidity'],
                    csv_data,
                    system_status
                )

                response_data = {
                    'success': True,
                    'image_url': '/current_image.png',
                    'display_type': '250x122',
                    'sensor_data': sensor_data,
                    'system_status': system_status
                }

            # Store image data in memory for serving
            img_buffer = io.BytesIO()
            image.save(img_buffer, format='PNG')
            DisplayHandler.current_image_data = img_buffer.getvalue()

            print(f"Display generated ({display_type}), image size: {len(DisplayHandler.current_image_data)} bytes")

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Expires', '0')
            self.end_headers()
            self.wfile.write(json.dumps(response_data).encode('utf-8'))

        except Exception as e:
            print(f"Error generating preview: {e}")
            response_data = {
                'success': False,
                'error': str(e)
            }
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response_data).encode('utf-8'))

def run_server(port=8000):
    """Start the development server."""
    server_address = ('', port)
    httpd = HTTPServer(server_address, DisplayHandler)

    print(f"PinkWeather Development Server")
    print(f"Server running at http://localhost:{port}")
    print("Press Ctrl+C to stop the server")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        httpd.shutdown()

if __name__ == '__main__':
    run_server()
