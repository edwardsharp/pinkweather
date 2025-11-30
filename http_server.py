"""
Weather Display Development Server

A localhost web server for developing and testing weather display layouts.
Provides a web interface to input text and preview the rendered e-ink display.
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
import base64
import io
from display_renderer import WeatherDisplayRenderer

class DisplayHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle GET requests - serve the main interface."""
        if self.path == '/' or self.path == '/index.html':
            self.serve_index()
        elif self.path.startswith('/preview'):
            self.serve_preview()
        else:
            self.send_error(404, "File not found")

    def do_POST(self):
        """Handle POST requests - process form data and generate preview."""
        if self.path == '/preview':
            self.handle_preview_post()
        else:
            self.send_error(404, "File not found")

    def serve_index(self):
        """Serve the main HTML interface."""
        html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Weather Display Development</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            text-align: center;
        }
        .form-group {
            margin-bottom: 15px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
            color: #555;
        }
        input[type="text"], input[type="number"], textarea, select {
            width: 100%;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
            box-sizing: border-box;
        }
        textarea {
            height: 120px;
            resize: vertical;
        }
        button {
            background-color: #007bff;
            color: white;
            padding: 10px 20px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
        }
        button:hover {
            background-color: #0056b3;
        }
        .preview-section {
            margin-top: 30px;
            text-align: center;
        }
        .display-preview {
            border: 2px solid #333;
            background-color: #fff;
            display: inline-block;
            margin: 10px;
        }
        .two-column {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }
        @media (max-width: 768px) {
            .two-column {
                grid-template-columns: 1fr;
            }
        }
        .layout-tabs {
            margin-bottom: 20px;
        }
        .tab-button {
            background-color: #f8f9fa;
            border: 1px solid #ddd;
            padding: 8px 16px;
            cursor: pointer;
            display: inline-block;
            margin-right: 5px;
        }
        .tab-button.active {
            background-color: #007bff;
            color: white;
        }
        .tab-content {
            display: none;
        }
        .tab-content.active {
            display: block;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Weather Display Development Tool</h1>
        <p>Preview your e-ink display layouts (250x122 pixels, 3-color: white, black, red)</p>

        <div class="layout-tabs">
            <span class="tab-button active" onclick="switchTab('text')">Text Display</span>
            <span class="tab-button" onclick="switchTab('weather')">Weather Layout</span>
            <span class="tab-button" onclick="switchTab('debug')">Debug Info</span>
        </div>

        <!-- Text Display Tab -->
        <div id="text-tab" class="tab-content active">
            <form method="POST" action="/preview">
                <input type="hidden" name="layout" value="text">

                <div class="two-column">
                    <div>
                        <div class="form-group">
                            <label for="title">Title (optional):</label>
                            <input type="text" id="title" name="title" placeholder="Enter title text">
                        </div>

                        <div class="form-group">
                            <label for="text">Main Text:</label>
                            <textarea id="text" name="text" placeholder="Enter your display text here. This text will be wrapped to fit the display dimensions.">Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.</textarea>
                        </div>
                    </div>

                    <div>
                        <div class="form-group">
                            <label for="font_size">Font Size:</label>
                            <input type="number" id="font_size" name="font_size" value="12" min="8" max="24">
                        </div>

                        <div class="form-group">
                            <label for="border">Border:</label>
                            <input type="number" id="border" name="border" value="4" min="0" max="20">
                        </div>

                        <div class="form-group">
                            <label for="background">Background:</label>
                            <select id="background" name="background">
                                <option value="white">White</option>
                                <option value="black">Black</option>
                            </select>
                        </div>
                    </div>
                </div>

                <button type="submit">Generate Preview</button>
            </form>
        </div>

        <!-- Weather Layout Tab -->
        <div id="weather-tab" class="tab-content">
            <form method="POST" action="/preview">
                <input type="hidden" name="layout" value="weather">

                <div class="two-column">
                    <div>
                        <div class="form-group">
                            <label for="temperature">Temperature:</label>
                            <input type="text" id="temperature" name="temperature" value="72°F" placeholder="e.g., 72°F">
                        </div>

                        <div class="form-group">
                            <label for="condition">Weather Condition:</label>
                            <input type="text" id="condition" name="condition" value="Sunny" placeholder="e.g., Sunny, Cloudy, Rainy">
                        </div>

                        <div class="form-group">
                            <label for="location">Location:</label>
                            <input type="text" id="location" name="location" value="San Francisco, CA" placeholder="e.g., San Francisco, CA">
                        </div>
                    </div>

                    <div>
                        <div class="form-group">
                            <label for="additional_info">Additional Info:</label>
                            <textarea id="additional_info" name="additional_info" placeholder="Humidity: 65%, Wind: 5mph NW, UV Index: 6">Humidity: 65%
Wind: 5mph NW
UV Index: 6
Sunrise: 6:42 AM
Sunset: 7:28 PM</textarea>
                        </div>
                    </div>
                </div>

                <button type="submit">Generate Preview</button>
            </form>
        </div>

        <!-- Debug Info Tab -->
        <div id="debug-tab" class="tab-content">
            <form method="POST" action="/preview">
                <input type="hidden" name="layout" value="debug">

                <div class="form-group">
                    <label for="debug_info">Debug Information (key: value pairs):</label>
                    <textarea id="debug_info" name="debug_info" placeholder="Enter debug info, one key: value pair per line">Memory: 45%
CPU: 23%
Temp: 68°F
WiFi: Connected
Signal: -42 dBm
Uptime: 2h 15m
Battery: 87%
Last Update: 14:23:42</textarea>
                </div>

                <button type="submit">Generate Preview</button>
            </form>
        </div>

        <div class="preview-section" id="preview-area">
            <!-- Preview image will be inserted here -->
        </div>
    </div>

    <script>
        function switchTab(tabName) {
            // Hide all tab contents
            const contents = document.querySelectorAll('.tab-content');
            contents.forEach(content => content.classList.remove('active'));

            // Remove active class from all tab buttons
            const buttons = document.querySelectorAll('.tab-button');
            buttons.forEach(button => button.classList.remove('active'));

            // Show selected tab content
            document.getElementById(tabName + '-tab').classList.add('active');

            // Add active class to clicked button
            event.target.classList.add('active');
        }
    </script>
</body>
</html>
        """

        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))

    def handle_preview_post(self):
        """Handle POST request to generate display preview."""
        try:
            # Parse POST data
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            form_data = urllib.parse.parse_qs(post_data.decode('utf-8'))

            # Extract form values
            layout_type = form_data.get('layout', ['text'])[0]

            # Create renderer
            renderer = WeatherDisplayRenderer()

            # Configure renderer based on form data
            if 'font_size' in form_data:
                renderer.font_size = int(form_data['font_size'][0])
            if 'border' in form_data:
                renderer.border = int(form_data['border'][0])
            if 'background' in form_data:
                bg = form_data['background'][0]
                if bg == 'black':
                    renderer.background_color = renderer.__class__.__dict__['BLACK']
                    renderer.text_color = renderer.__class__.__dict__['WHITE']

            # Generate image based on layout type
            if layout_type == 'weather':
                temperature = form_data.get('temperature', ['72°F'])[0]
                condition = form_data.get('condition', ['Sunny'])[0]
                location = form_data.get('location', ['Location'])[0]
                additional_info = form_data.get('additional_info', [''])[0]

                image = renderer.render_weather_layout(
                    temperature, condition, location, additional_info
                )

            elif layout_type == 'debug':
                debug_text = form_data.get('debug_info', [''])[0]
                debug_info = {}

                for line in debug_text.strip().split('\n'):
                    if ':' in line:
                        key, value = line.split(':', 1)
                        debug_info[key.strip()] = value.strip()

                image = renderer.render_debug_display(debug_info)

            else:  # text layout
                text = form_data.get('text', ['Sample text'])[0]
                title = form_data.get('title', [''])[0] or None

                image = renderer.render_text_display(text, title)

            # Convert image to base64 for embedding in HTML
            img_buffer = io.BytesIO()
            image.save(img_buffer, format='PNG')
            img_data = base64.b64encode(img_buffer.getvalue()).decode('utf-8')

            # Send response with embedded image
            html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Display Preview</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            text-align: center;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            display: inline-block;
        }}
        .preview {{
            border: 2px solid #333;
            display: inline-block;
            margin: 20px 0;
        }}
        .info {{
            color: #666;
            font-size: 14px;
            margin: 10px 0;
        }}
        button {{
            background-color: #007bff;
            color: white;
            padding: 10px 20px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
            margin: 10px;
        }}
        button:hover {{
            background-color: #0056b3;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h2>Display Preview</h2>
        <div class="info">250 × 122 pixels | 3-color e-ink display</div>
        <div class="preview">
            <img src="data:image/png;base64,{img_data}" alt="Display Preview" style="max-width: 100%; height: auto;">
        </div>
        <div>
            <button onclick="history.back()">← Back to Editor</button>
            <button onclick="downloadImage()">Download PNG</button>
        </div>
    </div>

    <script>
        function downloadImage() {{
            const link = document.createElement('a');
            link.download = 'weather_display_preview.png';
            link.href = 'data:image/png;base64,{img_data}';
            link.click();
        }}
    </script>
</body>
</html>
            """

            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(html.encode('utf-8'))

        except Exception as e:
            error_html = f"""
<!DOCTYPE html>
<html>
<head><title>Error</title></head>
<body>
    <h1>Error generating preview</h1>
    <p>{str(e)}</p>
    <button onclick="history.back()">← Back</button>
</body>
</html>
            """
            self.send_response(500)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(error_html.encode('utf-8'))

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
