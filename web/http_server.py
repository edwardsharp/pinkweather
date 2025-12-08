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

# Add parent directory to path to import shared modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web_adapter import (
    get_mock_sensor_data, get_mock_csv_data, get_mock_system_status
)
from simple_web_render import render_web_display

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
            # Generate default display with mock data
            sensor_data = get_mock_sensor_data()
            csv_data = get_mock_csv_data('normal')
            system_status = get_mock_system_status('normal')

            image = render_web_display(
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

            # Get scenario from form data
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
            image = render_web_display(
                sensor_data['temp_c'],
                sensor_data['humidity'],
                csv_data,
                system_status
            )

            # Store image data in memory for serving
            img_buffer = io.BytesIO()
            image.save(img_buffer, format='PNG')
            DisplayHandler.current_image_data = img_buffer.getvalue()

            print(f"Weather display generated, size: {len(DisplayHandler.current_image_data)} bytes")

            # Send JSON response indicating success
            response_data = {
                'success': True,
                'image_url': '/current_image.png',
                'sensor_data': sensor_data,
                'system_status': system_status
            }

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

    print(f"Weather Display Development Server")
    print(f"Server running at http://localhost:{port}")
    print("Press Ctrl+C to stop the server")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        httpd.shutdown()

if __name__ == '__main__':
    run_server()
