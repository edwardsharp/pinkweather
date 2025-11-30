# Weather Display Development System

A modular weather display system for e-ink displays that works both on microcontrollers (Pi Pico 2W) and as a localhost development server.

## Features

- **Modular Design**: Shared rendering logic between microcontroller and development environments
- **Web Development Interface**: Preview display layouts in a web browser
- **Multiple Layout Types**: Text, weather, and debug display modes
- **E-ink Optimized**: Designed for 250x122 pixel tri-color displays (white, black, red)
- **Font Support**: TTF font support with automatic fallback to system fonts

## Files Overview

- `display_renderer.py` - Core rendering module (shared between environments)
- `http_server.py` - Development web server for layout testing
- `code.py` - Microcontroller implementation (Pi Pico 2W)
- `weather_example.py` - Example weather API integration
- `AndaleMono.ttf` - Font file for consistent text rendering

## Installation

### Dependencies

The project uses different dependencies depending on the environment:

**For Development Server (localhost)**:
- Python 3.8+
- Pillow (PIL) for image processing
- Built-in HTTP server modules

**For Microcontroller (Pi Pico 2W)**:
- CircuitPython firmware
- Adafruit CircuitPython libraries (automatically available)

### Quick Installation

**Option 1: Using pip (recommended for development)**
```bash
# Clone or download the project files
cd pinkweather

# Install dependencies
pip install -r requirements.txt

# For development with additional tools
pip install -r requirements-dev.txt
```

**Option 2: Using make (if you have make installed)**
```bash
cd pinkweather
make install        # Basic installation
make install-dev    # Development installation with extras
make setup          # Full setup with virtual environment
```

**Option 3: Virtual environment (recommended)**
```bash
# Create virtual environment
python -m venv venv

# Activate it
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

## Quick Start

### 1. Development Server

Start the web development server to design and test layouts:

```bash
# Direct execution
python http_server.py

# Or using make
make server

# Or if installed as package
weather-server
```

Then open http://localhost:8000 in your browser.

The web interface provides three layout modes:
- **Text Display**: For general text content with optional titles
- **Weather Layout**: Structured weather information display
- **Debug Info**: System status and diagnostic information

### 2. Microcontroller Usage

**Files needed for Pi Pico 2W:**
- `display_renderer.py` (core rendering module)
- `code.py` (main microcontroller script)  
- `AndaleMono.ttf` (font file)

**Deployment steps:**
1. Install CircuitPython on your Pi Pico 2W
2. Install required Adafruit libraries via CircuitPython bundle
3. Copy the three files above to the CIRCUITPY drive
4. The microcontroller will automatically run `code.py` on boot

**Check deployment readiness:**
```bash
make deploy-check
```

### 3. Weather Integration

Use `weather_example.py` as a starting point for OpenWeatherMap integration:

```python
from weather_example import WeatherStation

# With API key
station = WeatherStation(api_key="your_api_key", location="San Francisco,US")
image = station.create_weather_display()

# Mock data for testing
station = WeatherStation()
image = station.create_weather_display()
```

## Display Renderer API

### WeatherDisplayRenderer Class

```python
from display_renderer import WeatherDisplayRenderer

renderer = WeatherDisplayRenderer(width=250, height=122, font_path="AndaleMono.ttf")
```

#### Configuration Options

- `width`, `height`: Display dimensions (default: 250x122)
- `font_path`: Path to TTF font file
- `border`: Border size in pixels
- `font_size`: Default font size
- `background_color`: Background color (WHITE or BLACK)
- `text_color`: Text color
- `accent_color`: Accent color (typically RED for e-ink)

#### Rendering Methods

**Text Display**
```python
image = renderer.render_text_display(
    text="Your long text content here...",
    title="Optional Title"
)
```

**Weather Layout**
```python
image = renderer.render_weather_layout(
    temperature="72°F",
    condition="Sunny",
    location="San Francisco, CA",
    additional_info="Humidity: 65%\nWind: 5mph NW"
)
```

**Debug Display**
```python
debug_info = {
    "Memory": "45%",
    "CPU": "23%",
    "WiFi": "Connected"
}
image = renderer.render_debug_display(debug_info)
```

## Hardware Requirements

### Pi Pico 2W + E-ink Display

- Raspberry Pi Pico 2W
- Adafruit 2.13" Tri-Color eInk Display (SSD1680)
- CircuitPython firmware

### Pin Connections

```
Pi Pico 2W  ->  E-ink Display
----------      -------------
3.3V        ->  VIN
GND         ->  GND
GP10 (MOSI) ->  DIN
GP11 (MISO) ->  (not used)
GP10 (SCK)  ->  CLK
GP7 (CE0)   ->  CS
GP22        ->  DC
GP27        ->  RST
GP17        ->  BUSY
```

## Development Workflow

1. **Design in Browser**: Use the web interface to experiment with layouts and text
2. **Test Rendering**: Generate and download preview images
3. **Deploy to Hardware**: Copy working configurations to your microcontroller
4. **Integrate APIs**: Add weather data fetching and real-time updates

## Weather API Integration

### OpenWeatherMap Setup

1. Sign up at https://openweathermap.org/api
2. Get your free API key
3. Update `weather_example.py` with your API key:

```python
station = WeatherStation(
    api_key="your_api_key_here",
    location="YourCity,CountryCode"
)
```

### Example API Response Handling

```python
def update_display(station):
    try:
        image = station.create_weather_display()
        display.image(image)
        display.display()
        print("Display updated successfully")
    except Exception as e:
        print(f"Error updating display: {e}")
        # Show error message on display
        error_image = station.create_text_display(f"Error: {e}")
        display.image(error_image)
        display.display()
```

## Customization

### Adding New Layout Types

Extend the `WeatherDisplayRenderer` class:

```python
def render_custom_layout(self, data):
    image = Image.new("RGB", (self.width, self.height), self.background_color)
    draw = ImageDraw.Draw(image)
    
    # Your custom rendering logic here
    
    return image
```

### Font Customization

- Place TTF fonts in the project directory
- Update `font_path` parameter in renderer initialization
- The system falls back to default fonts if TTF files aren't found

### Color Themes

Modify color constants for different themes:

```python
# Dark theme
renderer.background_color = BLACK
renderer.text_color = WHITE
renderer.accent_color = RED

# Light theme (default)
renderer.background_color = WHITE
renderer.text_color = BLACK
renderer.accent_color = RED
```

## Troubleshooting

### Common Issues

**Font not found**: Ensure `AndaleMono.ttf` is in the same directory as your script, or provide the full path.

**Display not updating**: Check hardware connections and ensure proper SPI configuration.

**Text too long**: Use the text wrapping feature or reduce font size for better fit.

**Web server not accessible**: Ensure no firewall blocking and try different port numbers.

### Debug Mode

Enable debug rendering to check system status:

```python
debug_info = {
    "Font": "Loaded" if renderer._get_font() else "Failed",
    "Display": f"{renderer.width}x{renderer.height}",
    "Memory": "Check available"
}
image = renderer.render_debug_display(debug_info)
```

## Package Management

### Available Commands

If you have `make` installed:
```bash
make help           # Show all available commands
make install        # Install basic dependencies  
make install-dev    # Install development dependencies
make server         # Start development server
make preview        # Generate sample images
make clean          # Clean temporary files
make deploy-check   # Verify files for microcontroller
make test          # Run tests (when available)
make format        # Format code
```

### Dependencies Overview

**Core Dependencies:**
- `Pillow>=9.0.0` - Image processing and rendering
- `requests>=2.28.0` - HTTP requests for weather APIs (optional)

**Development Dependencies:**
- `black` - Code formatting
- `flake8` - Code linting  
- `pytest` - Testing framework
- `mypy` - Type checking

**CircuitPython Libraries (microcontroller only):**
- `adafruit-circuitpython-epd` - E-ink display driver
- `adafruit-circuitpython-busio` - SPI communication
- `adafruit-circuitpython-digitalio` - GPIO control

## License

Based on Adafruit example code (MIT License). See individual files for specific license information.

## Contributing

1. Test changes with the web development server
2. Verify compatibility with both environments  
3. Update documentation for any new features
4. Ensure proper error handling for hardware limitations
5. Run `make format` and `make lint` before committing