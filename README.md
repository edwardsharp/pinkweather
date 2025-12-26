# pinkweather

yet another weather display for e-ink; does indoor and outdoor via openweathermap.org

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

## font stuff

convert some `.ttf` font file to `.bdf` like:

```sh
otf2bdf googz/Barlow_Condensed/BarlowCondensed-Regular.ttf -p 30 -o barlowcond30.bdf

otf2bdf googz/Barlow_Condensed/BarlowCondensed-Regular.ttf -p 60 -o barlowcond60.bdf
```

then use https://adafruit.github.io/web-bdftopcf/ to convert this `.bdf` to a `.pcf` file

## generate static dataset (for some broad analysis)

```sh
make generate-dataset

# or if in a hurry
make generate-dataset csv-only

# or if only like 100
make generate-dataset 100

# or if only like 100 in csv
make generate-dataset csv-only 100
```

then see output in:

web/static/narratives.csv
web/static/viewer.html

## HARDWARE

- Raspberry Pi Pico 2W
- Adafruit 2.13" Tri-Color eInk Display (SSD1680)
- CircuitPython firmware


## Weather API Integration

### OpenWeatherMap Setup

1. Sign up at https://openweathermap.org/api
2. Get API key
3. Update `weather_example.py` with API key:

```python
station = WeatherStation(
    api_key="your_api_key_here",
    location="YourCity,CountryCode"
)
```

## Package Management

### Available Commands

need `make` installed, then:

```bash
make install      # Install basic dependencies
make install-dev  # Install development dependencies
make clean        # Clean up temporary files
make test         # Run tests
make lint         # Run code linting
make format       # Format code with black
make server       # Start development web server
make preview      # Generate weather display preview
make deploy-check # Check files ready for microcontroller 
make deployment
make generate-dataset [csv-only] [COUNT] # Generate dataset make (csv-only for fast iteration)
make generate-images [COUNT] # Generate images for existing make narratives.csv (backup option)
make venv         # Create virtual environment
make activate     # Show how to activate virtual environment
```
