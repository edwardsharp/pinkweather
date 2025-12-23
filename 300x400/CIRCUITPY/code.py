"""
pinkweather CircuitPython code for 400x300 e-ink display

weather forecast text display with markup support and wo-
rd wrapping.
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
from logger import log
from weather_narrative import get_weather_narrative
from weather_persistence import save_weather_data

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
    log("SD card ready")

except Exception as e:
    log(f"SD card failed: {e}")
    log("Continuing without SD card...")
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
        log(f"LOW MEMORY: {free_mem} bytes free")
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
        log(f"Failed to load {filename}: {e}")
        return None


def update_display_with_weather_layout(weather_data):
    """Create weather layout with single-line header using provided weather data"""
    check_memory()

    if not weather_data:
        log("No weather data available - cannot create display")
        return

    log("Creating weather layout...")

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
    log("Refresh complete")


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

        log(f"Generated weather narrative: {narrative[:50]}...")
        return narrative

    except Exception as e:
        log(f"Error generating weather narrative: {e}")
        # Use basic description instead
        return weather_data.get("weather_desc", "Weather information unavailable")


# Get text capacity information
capacity = get_text_capacity()
log(
    f"Display: {capacity['chars_per_line']} chars/line, {capacity['lines_per_screen']} lines, {capacity['total_capacity']} total"
)


def connect_wifi():
    """Connect to WiFi network"""
    if config.WIFI_SSID is None or config.WIFI_PASSWORD is None:
        log("WiFi credentials not configured, skipping WiFi connection")
        return False

    log("Connecting to WiFi...")
    try:
        # Enable WiFi radio if needed
        if not wifi.radio.enabled:
            wifi.radio.enabled = True

        # Wait a moment for radio to initialize
        time.sleep(1)

        wifi.radio.connect(config.WIFI_SSID, config.WIFI_PASSWORD)
        log(f"Connected to {config.WIFI_SSID}")
        log(f"IP address: {wifi.radio.ipv4_address}")
        return True
    except Exception as e:
        log(f"Failed to connect to WiFi: {e}")
        return False


def disconnect_wifi():
    """Disconnect WiFi and disable radio to save power"""
    log("Disconnecting WiFi for power saving...")
    try:
        # Disconnect from network
        wifi.radio.stop_ap()
        wifi.radio.enabled = False
        log("WiFi disconnected and radio disabled")
        return True
    except Exception as e:
        log(f"Error disconnecting WiFi: {e}")
        return False


def deep_sleep(minutes):
    """Enter deep sleep mode for specified minutes"""
    log(f"Entering deep sleep for {minutes} minutes...")

    # Disconnect WiFi to save power
    disconnect_wifi()

    # Sleep in smaller chunks to allow for monitoring
    total_seconds = minutes * 60
    chunk_size = 300  # 5 minute chunks
    chunks = total_seconds // chunk_size
    remaining = total_seconds % chunk_size

    for i in range(chunks):
        if i == 0:
            log(f"Deep sleep started, will wake in {minutes} minutes")
        time.sleep(chunk_size)

    if remaining > 0:
        time.sleep(remaining)

    log("Waking up from deep sleep...")
    return True


def get_weather_display_data():
    """Get weather data for display - always fetch fresh data"""
    timezone_offset = getattr(config, "TIMEZONE_OFFSET_HOURS", -5)

    if WEATHER_CONFIG is None:
        log("Weather API not configured")
        return None

    if not wifi.radio.connected:
        log("WiFi not connected, attempting to reconnect...")
        if not connect_wifi():
            log("WiFi reconnection failed")
            return None

    # Always fetch fresh weather data (since current time is needed anyway)
    log("Fetching fresh weather data from API")
    try:
        forecast_data = weather_api.fetch_weather_data(WEATHER_CONFIG)
        if forecast_data:
            display_vars = weather_api.get_display_variables(
                forecast_data, timezone_offset
            )

            # Save to SD card for persistence across power cycles
            if sd_available and display_vars:
                current_timestamp = display_vars.get("current_timestamp")
                save_weather_data(
                    display_vars,
                    display_vars.get("forecast_data", []),
                    current_timestamp,
                )

            log("Weather data fetch successful")
            return display_vars
        else:
            log("Weather API returned no data")
            return None
    except Exception as e:
        log(f"Weather fetch error: {e}")
        return None


# Main execution and loop
def main():
    """Main execution with smart deep sleep polling logic"""
    # Global state for polling
    last_successful_update = 0
    current_weather_data = None
    consecutive_failures = 0

    log("pinkweather starting...")

    # Fetch initial weather data on boot
    log("Initial weather data fetch on boot...")
    if connect_wifi():
        try:
            initial_data = get_weather_display_data()
            if initial_data:
                current_weather_data = initial_data
                update_display_with_weather_layout(current_weather_data)
                last_successful_update = time.monotonic()
                consecutive_failures = 0
                log("Initial weather fetch successful")
            else:
                log("Initial weather fetch failed")
                consecutive_failures = 1
        except Exception as e:
            log(f"Error in initial weather fetch: {e}")
            consecutive_failures = 1
    else:
        log("WiFi connection failed on boot")
        consecutive_failures = 1

    log("pinkweather ready! Entering main polling loop...")

    while True:
        current_time = time.monotonic()
        hours_since_update = (current_time - last_successful_update) / 3600

        # Smart sleep intervals based on failure count and last success
        if consecutive_failures == 0:
            # Success case: sleep for full hour
            sleep_minutes = 60
        elif consecutive_failures == 1:
            # First failure: retry after 5 minutes
            sleep_minutes = 5
        elif consecutive_failures <= 4:
            # Multiple failures: 15 minute intervals
            sleep_minutes = 15
        else:
            # Many failures: back to hourly attempts
            sleep_minutes = 60

        # Check if it's time for an update
        needs_update = False
        if last_successful_update == 0:
            # Never successfully updated
            needs_update = True
        elif consecutive_failures == 0 and hours_since_update >= 1.0:
            # Normal hourly update
            needs_update = True
        elif consecutive_failures > 0:
            # Failed recently, time for retry
            needs_update = True

        if needs_update:
            log(f"Time to refresh weather data... (failures: {consecutive_failures})")

            # Re-establish WiFi connection
            wifi_connected = False
            try:
                wifi_connected = connect_wifi()
                if not wifi_connected:
                    log("WiFi connection failed")
                    consecutive_failures += 1
                else:
                    # Attempt weather data fetch
                    fresh_data = get_weather_display_data()
                    if fresh_data:
                        current_weather_data = fresh_data
                        update_display_with_weather_layout(current_weather_data)
                        last_successful_update = current_time
                        consecutive_failures = 0
                        log("Weather refresh completed successfully")
                        sleep_minutes = 60  # Sleep full hour after success
                    else:
                        log("Weather fetch failed")
                        consecutive_failures += 1
            except Exception as e:
                log(f"Error during weather refresh: {e}")
                consecutive_failures += 1

        # Check for extended error condition
        if hours_since_update >= 12:
            log(f"WARNING: No weather updates for {hours_since_update:.1f} hours")
            # Could display error message on screen here if needed

        # Enter deep sleep with WiFi power saving
        log(
            f"Next update attempt in {sleep_minutes} minutes (consecutive failures: {consecutive_failures})"
        )
        deep_sleep(sleep_minutes)


# Run main function
main()
