# Dependencies and Installation Guide

This document provides a complete overview of all dependencies, installation methods, and setup procedures for the PinkWeather weather display system.

## Overview

PinkWeather is designed to work in two environments:
1. **Development Environment**: Python-based web server for layout testing
2. **Production Environment**: CircuitPython on Raspberry Pi Pico 2W with e-ink display

## Quick Start

### Automated Installation (Recommended)

**Linux/macOS:**
```bash
./install.sh --venv
```

**Windows:**
```cmd
install.bat
```

**Manual Installation:**
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Verify installation
python check_install.py
```

## Dependency Categories

### Core Dependencies (Required for Development)

#### Python Version
- **Minimum**: Python 3.8
- **Recommended**: Python 3.9+
- **Tested with**: Python 3.13

#### Essential Packages

| Package | Version | Purpose | Import |
|---------|---------|---------|--------|
| Pillow | >=9.0.0 | Image processing, rendering | `from PIL import Image, ImageDraw, ImageFont` |

#### Standard Library (Included with Python)

| Module | Purpose |
|--------|---------|
| `http.server` | Development web server |
| `urllib.parse` | URL/form data parsing |
| `base64` | Image encoding for web display |
| `io` | In-memory file operations |
| `json` | Data serialization |
| `time` | Time/date formatting |
| `os` | File system operations |
| `textwrap` | Text wrapping utilities |

### Optional Dependencies

#### Weather API Integration
| Package | Version | Purpose |
|---------|---------|---------|
| requests | >=2.28.0 | HTTP requests to weather APIs |

#### Development Tools
| Package | Version | Purpose |
|---------|---------|---------|
| black | >=22.0.0 | Code formatting |
| flake8 | >=4.0.0 | Code linting |
| isort | >=5.10.0 | Import sorting |
| mypy | >=0.950 | Type checking |
| pytest | >=7.0.0 | Testing framework |
| pytest-cov | >=3.0.0 | Test coverage |

### CircuitPython Dependencies (Microcontroller Only)

These are **NOT** installable via pip. They come with CircuitPython firmware and Adafruit libraries.

#### Core CircuitPython Modules
- `board` - Hardware pin definitions
- `busio` - SPI/I2C communication
- `digitalio` - GPIO control

#### Adafruit Libraries
- `adafruit_epd.ssd1680` - E-ink display driver

#### Installation on Microcontroller
1. Flash CircuitPython firmware on Pi Pico 2W
2. Download Adafruit CircuitPython Library Bundle
3. Copy required libraries to `/lib` folder on CIRCUITPY drive

## Installation Methods

### Method 1: Virtual Environment (Recommended)

**Benefits:**
- Isolated environment
- No conflicts with system Python
- Easy cleanup
- Reproducible setup

**Steps:**
```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate.bat  # Windows

# Install dependencies
pip install -r requirements.txt

# Verify installation
python check_install.py

# Start development server
python http_server.py
```

### Method 2: System-wide Installation

**Warning:** May affect other Python projects

```bash
# Install globally (not recommended)
pip install -r requirements.txt

# Or install for current user only
pip install --user -r requirements.txt
```

### Method 3: Using Package Manager

**Install as editable package:**
```bash
pip install -e .
```

**Using specific requirements file:**
```bash
pip install -r requirements-dev.txt  # Includes development tools
```

## Platform-Specific Instructions

### Linux (Ubuntu/Debian)

**System dependencies:**
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv
```

**Additional packages for enhanced functionality:**
```bash
sudo apt install python3-dev libjpeg-dev zlib1g-dev
```

### Linux (CentOS/RHEL/Fedora)

```bash
sudo yum install python3 python3-pip
# or
sudo dnf install python3 python3-pip
```

### macOS

**Using Homebrew:**
```bash
brew install python3
```

**Using MacPorts:**
```bash
sudo port install python39 py39-pip
```

### Windows

1. Download Python from https://python.org/downloads/
2. **Important:** Check "Add Python to PATH" during installation
3. Open Command Prompt and verify: `python --version`

## Hardware Dependencies (Microcontroller)

### Required Hardware
- Raspberry Pi Pico 2W
- Adafruit 2.13" Tri-Color eInk Display (SSD1680)
- MicroUSB cable
- Breadboard and jumper wires (for prototyping)

### Pin Connections
```
Pi Pico 2W    E-ink Display
----------    -------------
3.3V      ->  VIN
GND       ->  GND
GP10(MOSI)->  DIN
GP11(SCK) ->  CLK
GP7(CE0)  ->  CS
GP22      ->  DC
GP27      ->  RST
GP17      ->  BUSY
```

### CircuitPython Setup
1. Download CircuitPython UF2 for Pi Pico 2W
2. Hold BOOTSEL button while connecting USB
3. Copy UF2 file to RPI-RP2 drive
4. Download Adafruit CircuitPython Library Bundle
5. Extract and copy required libraries to `/lib`

## Troubleshooting Dependencies

### Common Issues and Solutions

#### "No module named 'PIL'"
```bash
# Solution 1: Install Pillow
pip install Pillow

# Solution 2: Upgrade pip first
pip install --upgrade pip
pip install Pillow

# Solution 3: Use specific Python version
python3 -m pip install Pillow
```

#### "externally-managed-environment" Error
```bash
# Solution: Use virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### Font-related Issues
- **Missing font file**: System will fallback to default font
- **Font loading errors**: Check font file permissions and path
- **Text rendering issues**: Verify PIL font support

#### Permission Errors
```bash
# Linux/Mac: Add user to appropriate groups
sudo usermod -a -G dialout $USER  # For serial access

# Windows: Run as administrator if needed
```

### Dependency Verification

**Check individual packages:**
```python
python -c "import PIL; print(f'Pillow {PIL.__version__}')"
python -c "import requests; print(f'requests {requests.__version__}')"
```

**Full system check:**
```bash
python check_install.py
```

**Package information:**
```bash
pip list | grep -i pillow
pip show Pillow
```

## Development Workflow Dependencies

### Code Quality Tools
```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Format code
black *.py
isort *.py

# Check code quality
flake8 *.py
mypy *.py --ignore-missing-imports

# Run tests
pytest tests/
```

### Build Tools
```bash
# Build package
pip install build
python -m build

# Install in development mode
pip install -e .
```

## Minimal Installation

**For basic functionality only:**
```bash
pip install Pillow>=9.0.0
```

**Files needed:**
- `display_renderer.py`
- `http_server.py` (for web development)
- `code.py` (for microcontroller)
- `AndaleMono.ttf` (font file)

## Environment Variables

### Optional Configuration
```bash
# Custom font path
export WEATHER_FONT_PATH="/path/to/font.ttf"

# Development server port
export WEATHER_SERVER_PORT=8080

# Weather API key
export OPENWEATHER_API_KEY="your_api_key"
```

## Compatibility Matrix

| Environment | Python | Pillow | requests | CircuitPython |
|-------------|--------|--------|----------|---------------|
| Development | 3.8+   | ✓      | ✓        | ✗             |
| Microcontroller | N/A | ✗     | ✗        | ✓             |

## Performance Considerations

### Memory Usage
- **Development**: ~50MB Python + libraries
- **Microcontroller**: ~2MB CircuitPython + libraries

### Startup Time
- **Development server**: ~2 seconds
- **Microcontroller boot**: ~3-5 seconds
- **Image generation**: ~100-500ms

## Security Considerations

### Development Environment
- Use virtual environments to isolate dependencies
- Keep dependencies updated: `pip install --upgrade -r requirements.txt`
- Scan for vulnerabilities: `pip audit`

### API Keys
- Store API keys in environment variables
- Never commit API keys to version control
- Use `.env` files for local development

## License Information

### Dependency Licenses
- **Pillow**: HPND License (PIL Software License)
- **requests**: Apache License 2.0
- **Python Standard Library**: Python Software Foundation License

### Project License
- Based on Adafruit example code (MIT License)
- See individual files for specific license information

## Support and Resources

### Official Documentation
- [Pillow Documentation](https://pillow.readthedocs.io/)
- [CircuitPython Documentation](https://docs.circuitpython.org/)
- [Adafruit Learning System](https://learn.adafruit.com/)

### Community Resources
- [CircuitPython Discord](https://discord.gg/circuitpython)
- [Adafruit Forums](https://forums.adafruit.com/)
- [Python Package Index (PyPI)](https://pypi.org/)

### Getting Help
1. Check this documentation
2. Run `python check_install.py` for diagnostics
3. Check GitHub issues for known problems
4. Ask on CircuitPython Discord for hardware issues
5. Create issue with full error output and system info