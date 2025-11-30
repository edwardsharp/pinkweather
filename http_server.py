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
from display_renderer import WeatherDisplayRenderer

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
            self.handle_preview_post_inline()
        else:
            self.send_error(404, "File not found")

    def serve_index(self):
        """Serve the main HTML interface from template file."""
        try:
            # Get the directory where this script is located
            script_dir = os.path.dirname(os.path.abspath(__file__))
            template_path = os.path.join(script_dir, 'templates', 'index.html')

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
            # Generate default image if none exists
            renderer = WeatherDisplayRenderer()
            image = renderer.render_text_display("No preview generated yet", title=None)
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

    def handle_preview_post_inline(self):
        """Handle POST request to generate display preview and return JSON."""
        try:
            # Parse URL-encoded form data
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            form_data = urllib.parse.parse_qs(post_data.decode('utf-8'))

            # Debug: print received form data
            print(f"Server received form data: {form_data}")


            # Create renderer
            renderer = WeatherDisplayRenderer()

            # Configure renderer based on form data
            if 'font_size' in form_data and form_data['font_size']:
                try:
                    renderer.font_size = int(form_data['font_size'][0])
                    print(f"Set font size to: {renderer.font_size}")
                except (ValueError, IndexError):
                    print("Error parsing font_size, using default")

            # Get text from form (this is the main text display)
            text = form_data.get('text', ['Enter some text in the form above'])[0]
            print(f"Extracted text: '{text}' (length: {len(text)})")


            # Generate text display image
            image = renderer.render_text_display(text, title=None)

            # Store image data in memory for serving
            img_buffer = io.BytesIO()
            image.save(img_buffer, format='PNG')
            DisplayHandler.current_image_data = img_buffer.getvalue()
            print(f"Image generated and stored, size: {len(DisplayHandler.current_image_data)} bytes")


            # Send JSON response indicating success
            response_data = {
                'success': True,
                'image_url': '/current_image.png'
            }

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Expires', '0')
            self.end_headers()
            self.wfile.write(json.dumps(response_data).encode('utf-8'))

        except Exception as e:
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
