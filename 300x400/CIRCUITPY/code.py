"""
PinkWeather CircuitPython Code for 400x300 E-ink Display
Text display with markup support and hard word wrapping
"""

import time
import board
import busio
import digitalio
import displayio
import fourwire
import adafruit_ssd1683
import adafruit_sdcard
import storage
import gc
import json
import wifi
import socketpool
import ssl
import adafruit_requests
from digitalio import DigitalInOut

# shared display functions
from display import create_text_display, get_text_capacity, create_weather_layout, create_alt_weather_layout, WEATHER_ICON_X, WEATHER_ICON_Y, MOON_ICON_X, MOON_ICON_Y
from alt_weather_header import get_alt_header_height
# get_forecast_icon_positions import removed - icons now handled directly in forecast_row.py
from forecast_row import set_icon_loader
from weather_header import get_header_height

# Import configuration and shared modules
import config
import weather_api
from moon_phase import calculate_moon_phase, phase_to_icon_name

# Configuration flag for alternative header
USE_ALTERNATIVE_HEADER = True  # Set to False to use original header

# Create weather config from imported settings
WEATHER_CONFIG = {
    'api_key': config.OPENWEATHER_API_KEY,
    'latitude': config.LATITUDE,
    'longitude': config.LONGITUDE,
    'units': 'metric'
} if config.OPENWEATHER_API_KEY and config.LATITUDE and config.LONGITUDE else None

# Release any previously used displays
displayio.release_displays()

# Pin assignments for Pico 2W
# SPI pins: SCK=GP18, MOSI=GP19, MISO=GP16
# CS pin: GP17, DC pin: GP20
spi = busio.SPI(clock=board.GP18, MOSI=board.GP19, MISO=board.GP16)

# Pin assignments for FourWire (use Pin objects directly)
cs_pin = board.GP17
dc_pin = board.GP20  # You'll need to wire this DC pin!

# Reset and Busy pins (optional but recommended)
rst_pin = None  # board.GP21
busy_pin = None  # digitalio.DigitalInOut(board.GP22) if you wire it

# Create the display bus
display_bus = fourwire.FourWire(
    spi,
    command=dc_pin,
    chip_select=cs_pin,
    reset=rst_pin,
    baudrate=1000000
)

# Wait a moment for the bus to initialize
time.sleep(1)

# Create the display
display = adafruit_ssd1683.SSD1683(
    display_bus,
    width=400,
    height=300,
    highlight_color=0x000000,  # Black instead of red to prevent artifacts
    busy_pin=busy_pin
)

# Rotate display 180 degrees
display.rotation = 180

# Initialize SD card
sd_available = False
try:
    # Disable SRAM to avoid SPI conflicts (SRCS -> GP22)
    srcs_pin = DigitalInOut(board.GP22)
    srcs_pin.direction = digitalio.Direction.OUTPUT
    srcs_pin.value = True  # High = SRAM disabled

    # Initialize SD card
    cs_sd = DigitalInOut(board.GP21)
    sdcard = adafruit_sdcard.SDCard(spi, cs_sd, baudrate=250000)
    vfs = storage.VfsFat(sdcard)
    storage.mount(vfs, "/sd")
    sd_available = True
    print("SD card ready")

except Exception as e:
    print(f"SD card failed: {e}")
    print("Continuing without SD card...")
    sd_available = False

# Display dimensions and colors
DISPLAY_WIDTH = 400
DISPLAY_HEIGHT = 300
BLACK = 0x000000
WHITE = 0xFFFFFF
RED = 0xFF0000

def format_time(unix_timestamp=None):
    """Format time as '9:36p' (12-hour format with am/p suffix)"""
    if unix_timestamp is None:
        time_struct = time.localtime()
    else:
        time_struct = time.localtime(unix_timestamp)

    hour = time_struct.tm_hour
    minute = time_struct.tm_min

    # Convert to 12-hour format
    if hour == 0:
        hour_12 = 12
        suffix = 'a'
    elif hour < 12:
        hour_12 = hour
        suffix = 'a'
    elif hour == 12:
        hour_12 = 12
        suffix = 'p'
    else:
        hour_12 = hour - 12
        suffix = 'p'

    return f"{hour_12}:{minute:02d}{suffix}"

def check_memory():
    """Check available memory and force collection if low"""
    gc.collect()
    free_mem = gc.mem_free()
    if free_mem < 2048:  # If less than 2KB free
        print(f"LOW MEMORY: {free_mem} bytes free")
        gc.collect()
    return free_mem

def load_bmp_icon(filename):
    """Load BMP icon from SD card with error handling"""
    if not sd_available:
        return None

    try:
        file_path = f"/sd/bmp/{filename}"
        pic = displayio.OnDiskBitmap(file_path)
        return displayio.TileGrid(pic, pixel_shader=pic.pixel_shader)
    except Exception as e:
        print(f"Failed to load {filename}: {e}")
        return None

def update_display_with_weather_layout():
    """Create structured weather layout with icons using display.py"""
    check_memory()

    # Get parsed weather data (real or fallback)
    weather_data = get_weather_display_data()

    print("Creating weather layout...")

    if USE_ALTERNATIVE_HEADER:
        # Use alternative single-line header with date and moon phase text
        print("Using alternative header layout")

        # Set up icon loader for forecast rows before creating layout
        set_icon_loader(sd_available, load_bmp_icon)

        main_group = create_alt_weather_layout(
            current_timestamp=weather_data.get('current_timestamp'),
            timezone_offset_hours=getattr(config, 'TIMEZONE_OFFSET_HOURS', -5),
            forecast_data=weather_data['forecast_data'],
            weather_desc=weather_data['weather_desc'],
            icon_loader=load_bmp_icon if sd_available else None
        )
    else:
        # Use original header layout
        print("Using original header layout")
        # Get moon phase using API timestamp for consistency with alternative header
        moon_phase = calculate_moon_phase(weather_data.get('current_timestamp'))
        moon_icon_name = phase_to_icon_name(moon_phase)

        # Set up icon loader for forecast rows before creating layout
        set_icon_loader(sd_available, load_bmp_icon)

        main_group = create_weather_layout(
            day_name=weather_data['day_name'],
            day_num=weather_data['day_num'],
            month_name=weather_data['month_name'],
            current_temp=weather_data['current_temp'],
            feels_like=weather_data['feels_like'],
            high_temp=weather_data['high_temp'],
            low_temp=weather_data['low_temp'],
            sunrise_time=weather_data['sunrise_time'],
            sunset_time=weather_data['sunset_time'],
            weather_desc=weather_data['weather_desc'],
            weather_icon_name=weather_data['weather_icon_name'],
            moon_icon_name=f"{moon_icon_name}.bmp",
            forecast_data=weather_data['forecast_data']
        )

    # Load and position icons if SD card is available
    if sd_available:
        if USE_ALTERNATIVE_HEADER:
            # Icons are now handled directly in forecast_row.py for proper layering
            print("Forecast icons integrated into forecast cells")
        else:
            # Original header layout with weather and moon icons
            # Weather icon from weather data
            weather_icon = load_bmp_icon(weather_data['weather_icon_name'])
            if weather_icon:
                weather_icon.x = WEATHER_ICON_X
                weather_icon.y = WEATHER_ICON_Y
                main_group.append(weather_icon)

            # Moon phase icon
            moon_icon = load_bmp_icon(f"{moon_icon_name}.bmp")
            if moon_icon:
                moon_icon.x = MOON_ICON_X
                moon_icon.y = MOON_ICON_Y
                main_group.append(moon_icon)

            # Forecast icons are now handled directly in forecast_row.py for proper layering
            print("Forecast icons integrated into forecast cells for original header too")

        print("Display updated successfully")
    # Update display
    display.root_group = main_group
    display.refresh()

    print("Weather layout displayed!")
    check_memory()

    # Wait for refresh to complete
    time.sleep(display.time_to_refresh + 2)
    print("Refresh complete")

# Get text capacity information
capacity = get_text_capacity()
print(f"Display: {capacity['chars_per_line']} chars/line, {capacity['lines_per_screen']} lines, {capacity['total_capacity']} total")

def connect_wifi():
    """Connect to WiFi network"""
    if config.WIFI_SSID is None or config.WIFI_PASSWORD is None:
        print("WiFi credentials not configured, skipping WiFi connection")
        return False

    print("Connecting to WiFi...")
    try:
        wifi.radio.connect(config.WIFI_SSID, config.WIFI_PASSWORD)
        print(f"Connected to {config.WIFI_SSID}")
        print(f"IP address: {wifi.radio.ipv4_address}")
        return True
    except Exception as e:
        print(f"Failed to connect to WiFi: {e}")
        return False

def get_weather_display_data():
    """Get parsed weather data ready for display"""
    # Get timezone offset from config
    timezone_offset = getattr(config, 'TIMEZONE_OFFSET_HOURS', -5)

    if WEATHER_CONFIG is None:
        print("Weather API not configured, using fallback data")
        return weather_api.get_display_variables(None, None, timezone_offset)
    elif wifi.radio.connected:
        # Fetch real weather data (forecast API only)
        forecast_data = weather_api.fetch_weather_data(WEATHER_CONFIG)
        return weather_api.get_display_variables(forecast_data, timezone_offset)
    else:
        # Use fallback data
        print("WiFi not connected, using fallback data")
        return weather_api.get_display_variables(None, None, timezone_offset)

# Main execution
def main():
    """Main execution loop"""
    # Connect to WiFi
    if connect_wifi():
        print("WiFi connected, will fetch real weather data")
    else:
        print("WiFi connection failed or skipped, will use fallback data")

    # Update display (will automatically use real or fallback data based on WiFi)
    update_display_with_weather_layout()

# Run main function
main()

# Main loop
print("PinkWeather ready!")
while True:
    # Add your main program logic here
    # For example:
    # - Fetch weather data from API
    # - Update display with new information
    # - Handle sensor readings
    # - etc.

    time.sleep(60)  # Sleep for 1 minute
