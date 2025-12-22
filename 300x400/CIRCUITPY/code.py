"""
PinkWeather CircuitPython Code for 400x300 E-ink Display
Text display with markup support and hard word wrapping
"""

import gc
import time

import adafruit_sdcard
import adafruit_ssd1683
import board
import busio

# Import configuration and shared modules
import config
import digitalio
import displayio
import fourwire
import storage
import weather_api
import wifi
from digitalio import DigitalInOut

# shared display functions
from display import create_weather_layout, get_text_capacity
from forecast_row import set_icon_loader
from weather_narrative import get_weather_narrative
from weather_persistence import save_weather_data, should_refresh_weather

# Create weather config from imported settings
WEATHER_CONFIG = (
    {
        "api_key": config.OPENWEATHER_API_KEY,
        "latitude": config.LATITUDE,
        "longitude": config.LONGITUDE,
        "timezone_offset_hours": config.TIMEZONE_OFFSET_HOURS,
        "units": "metric",
    }
    if config.OPENWEATHER_API_KEY and config.LATITUDE and config.LONGITUDE
    else None
)

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
    spi, command=dc_pin, chip_select=cs_pin, reset=rst_pin, baudrate=1000000
)

# Wait a moment for the bus to initialize
time.sleep(1)

# Create the display
display = adafruit_ssd1683.SSD1683(
    display_bus, width=400, height=300, highlight_color=0xFF0000, busy_pin=busy_pin
)

# rotate the display 0 so the bottom is the side with the 20pin cable
display.rotation = 0

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


def update_display_with_weather_layout(weather_data):
    """Create weather layout with single-line header using provided weather data"""
    check_memory()

    if not weather_data:
        print("No weather data available - cannot create display")
        return

    print("Creating weather layout...")

    # Set up icon loader for forecast rows
    set_icon_loader(sd_available, load_bmp_icon)

    # Generate rich weather narrative
    weather_narrative = generate_weather_narrative(weather_data)

    main_group = create_weather_layout(
        current_timestamp=weather_data.get("current_timestamp"),
        forecast_data=weather_data["forecast_data"],
        weather_desc=weather_narrative,
        icon_loader=load_bmp_icon if sd_available else None,
        day_name=weather_data.get("day_name"),
        day_num=weather_data.get("day_num"),
        month_name=weather_data.get("month_name"),
    )

    # Update display
    display.root_group = main_group
    display.refresh()

    # Wait for refresh to complete
    time.sleep(display.time_to_refresh)
    print("Refresh complete")


def generate_weather_narrative(weather_data):
    """Generate rich weather narrative from weather data"""
    try:
        # Extract current weather info for narrative generation
        current_weather = {
            "current_temp": weather_data.get("current_temp", 0),
            "feels_like": weather_data.get("feels_like", 0),
            "high_temp": weather_data.get("high_temp", 0),
            "low_temp": weather_data.get("low_temp", 0),
            "weather_desc": weather_data.get("weather_desc", ""),
            "sunrise_time": weather_data.get("sunrise_time", "7:00a"),
            "sunset_time": weather_data.get("sunset_time", "5:00p"),
            "humidity": weather_data.get("humidity", 0),
            "wind_speed": weather_data.get("wind_speed", 0),
            "wind_gust": weather_data.get("wind_gust", 0),
        }

        forecast_data = weather_data.get("forecast_data", [])
        current_timestamp = weather_data.get("current_timestamp")

        # Generate the rich narrative
        narrative = get_weather_narrative(
            current_weather, forecast_data, current_timestamp
        )

        print(f"Generated weather narrative: {narrative[:50]}...")
        return narrative

    except Exception as e:
        print(f"Error generating weather narrative: {e}")
        # Use basic description instead
        return weather_data.get("weather_desc", "Weather information unavailable")


# Get text capacity information
capacity = get_text_capacity()
print(
    f"Display: {capacity['chars_per_line']} chars/line, {capacity['lines_per_screen']} lines, {capacity['total_capacity']} total"
)


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
    """Get weather data for display - always fetch fresh data"""
    timezone_offset = getattr(config, "TIMEZONE_OFFSET_HOURS", -5)

    if WEATHER_CONFIG is None:
        print("Weather API not configured")
        return None

    if not wifi.radio.connected:
        print("WiFi not connected")
        return None

    # Always fetch fresh weather data (since we need current time anyway)
    print("Fetching fresh weather data from API")
    forecast_data = weather_api.fetch_weather_data(WEATHER_CONFIG)
    if forecast_data:
        display_vars = weather_api.get_display_variables(forecast_data, timezone_offset)

        # Save to SD card for persistence across power cycles
        if sd_available and display_vars:
            current_timestamp = display_vars.get("current_timestamp")
            save_weather_data(
                display_vars, display_vars.get("forecast_data", []), current_timestamp
            )

        return display_vars
    else:
        print("Failed to fetch weather data")
        return None


# Main execution and loop
def main():
    """Main execution with simplified weather refresh logic"""
    # Global state
    last_successful_update = 0
    current_weather_data = None

    # Connect to WiFi
    if connect_wifi():
        print("WiFi connected, will fetch real weather data")
    else:
        print("WiFi connection failed or skipped")

    print("pinkweather ready!")

    while True:
        current_time = time.monotonic()

        # Check if we need to update (every hour or on first boot)
        needs_update = (current_time - last_successful_update) >= 3600  # 1 hour

        if needs_update:
            print("Time to refresh weather data...")
            try:
                # Attempt to fetch fresh weather data
                fresh_data = get_weather_display_data()
                if fresh_data:
                    current_weather_data = fresh_data
                    update_display_with_weather_layout(current_weather_data)
                    last_successful_update = current_time
                    print("Weather refresh completed successfully")
                else:
                    print("Weather fetch failed - will retry in 15 minutes")
            except Exception as e:
                print(f"Error fetching weather: {e} - will retry in 15 minutes")

        # Check for error condition (no updates for 12+ hours)
        hours_since_update = (current_time - last_successful_update) / 3600
        if hours_since_update >= 12:
            print(f"WARNING: No weather updates for {hours_since_update:.1f} hours")
            # Could display error message here if needed

        # Sleep for 15 minutes before next check
        print("Sleeping for 15 minutes...")
        time.sleep(15 * 60)


# Run main function
main()
