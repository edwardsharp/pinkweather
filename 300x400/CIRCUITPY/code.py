"""
pinkweather CircuitPython code for 400x300 e-ink display

weather forecast text display with markup support and wo-
rd wrapping.
"""

import gc
import time

import adafruit_hdc302x
import adafruit_sdcard
import adafruit_ssd1683
import busio

# Import configuration and shared modules
import config
import digitalio
import displayio
import fourwire
import microcontroller
import socketpool
import storage
import wifi
from digitalio import DigitalInOut
from display.forecast_row import set_icon_loader

# shared display functions
from display.text_renderer import get_text_capacity
from display.weather_display import create_weather_display_layout
from utils.logger import log
from weather import weather_api
from weather.weather_persistence import save_weather_data

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

# Initialize onboard LED
led = DigitalInOut(config.LED_PIN)
led.direction = digitalio.Direction.OUTPUT

# Release any previously used displays
displayio.release_displays()

spi = busio.SPI(
    clock=config.SPI_SCK_PIN, MOSI=config.SPI_MOSI_PIN, MISO=config.SPI_MISO_PIN
)

display_bus = fourwire.FourWire(
    spi,
    command=config.DISPLAY_DC_PIN,
    chip_select=config.DISPLAY_CS_PIN,
    reset=config.DISPLAY_RST_PIN,
    baudrate=1000000,
)

# Wait a moment for the bus to initialize
time.sleep(1)

# Create the display
display = adafruit_ssd1683.SSD1683(
    display_bus,
    width=400,
    height=300,
    highlight_color=0xFF0000,
    busy_pin=config.DISPLAY_BUSY_PIN,
)

display.rotation = config.DISPLAY_ROTATION

# Initialize SD card
sd_available = False
try:
    # Disable SRAM to avoid SPI conflicts (SRCS -> GP22)
    srcs_pin = DigitalInOut(config.SD_SRCS_PIN)
    srcs_pin.direction = digitalio.Direction.OUTPUT
    srcs_pin.value = True  # High = SRAM disabled

    # Initialize SD card
    cs_sd = DigitalInOut(config.SD_CS_PIN)
    sdcard = adafruit_sdcard.SDCard(spi, cs_sd, baudrate=250000)
    vfs = storage.VfsFat(sdcard)
    storage.mount(vfs, "/sd")
    sd_available = True
    log("SD card ready")

except Exception as e:
    log(f"SD card failed: {e}")
    log("Continuing without SD card...")
    sd_available = False

# Initialize temperature/humidity sensor
sensor = None
try:
    i2c = busio.I2C(scl=config.I2C_SCL_PIN, sda=config.I2C_SDA_PIN)
    sensor = adafruit_hdc302x.HDC302x(i2c)
    log("Temperature sensor initialized successfully")
    current_temp = int(round(sensor.temperature))
    current_humidity = int(round(sensor.relative_humidity))
    log(f"Sensor reading - temp: {current_temp}°C, humidity: {current_humidity}%")
except Exception as e:
    log(f"Temperature sensor failed to initialize: {e}")
    log("Continuing without temperature sensor...")
    sensor = None


# Display dimensions and colors
DISPLAY_WIDTH = 400
DISPLAY_HEIGHT = 300
BLACK = 0x000000
WHITE = 0xFFFFFF
RED = 0xFF0000


def get_indoor_temp_humidity():
    """Read current temperature and humidity from sensor and return formatted string"""
    if sensor is None:
        return None

    try:
        current_temp = int(round(sensor.temperature))
        current_humidity = int(round(sensor.relative_humidity))
        log(f"Sensor reading - temp: {current_temp}°C, humidity: {current_humidity}%")
        return f"{current_temp}° {current_humidity}%"
    except Exception as e:
        log(f"Failed to read sensor: {e}")
        return None


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

    # Get fresh indoor temperature and humidity reading
    indoor_temp_humidity = get_indoor_temp_humidity()

    # Use shared display layout function
    main_group = create_weather_display_layout(
        weather_data,
        icon_loader=load_bmp_icon if sd_available else None,
        indoor_temp_humidity=indoor_temp_humidity,
    )

    # Update display
    display.root_group = main_group
    display.refresh()

    # Wait for refresh to complete
    # log(f"display.time_to_refresh: {display.time_to_refresh}")
    # time.sleep(display.time_to_refresh)
    # note: display.time_to_refresh is 180 when i looked, which is like way-too-long
    time.sleep(20)
    log("Refresh complete")


# Function moved to display.weather_display module


# Get text capacity information
capacity = get_text_capacity()
log(
    f"Display: {capacity['chars_per_line']} chars/line, {capacity['lines_per_screen']} lines, {capacity['total_capacity']} total"
)


def connect_wifi():
    """Connect to WiFi network with fresh connection"""
    if config.WIFI_SSID is None or config.WIFI_PASSWORD is None:
        log("WiFi credentials not configured, skipping WiFi connection")
        return False

    log("Connecting to WiFi...")
    try:
        # Ensure clean state - stop any existing station connection
        if wifi.radio.connected:
            wifi.radio.stop_station()

        # Reset radio to ensure fresh state
        wifi.radio.enabled = False
        time.sleep(1)
        wifi.radio.enabled = True
        time.sleep(2)

        wifi.radio.connect(config.WIFI_SSID, config.WIFI_PASSWORD)
        log(f"Connected to {config.WIFI_SSID}")
        log(f"IP address: {wifi.radio.ipv4_address}")

        # Give a moment for network to be ready
        time.sleep(2)
        return True
    except Exception as e:
        log(f"Failed to connect to WiFi: {e}")
        return False


def disconnect_wifi():
    """Disconnect WiFi and disable radio to save power"""
    log("Disconnecting WiFi for power saving...")
    try:
        # Properly disconnect station and disable radio
        if wifi.radio.connected:
            wifi.radio.stop_station()
        wifi.radio.enabled = False
        log("WiFi disconnected and radio disabled")
        return True
    except Exception as e:
        log(f"Error disconnecting WiFi: {e}")
        return False


def deep_sleep(minutes):
    """Enter deep sleep mode for specified minutes"""
    log(f"Entering deep sleep for {minutes} minutes...")

    # Turn off LED before deep sleep
    led.value = False
    log("LED turned off for deep sleep")

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
    """Hardware-specific weather data fetching with WiFi and SD persistence"""

    if WEATHER_CONFIG is None:
        log("Weather API not configured")
        return None

    if not wifi.radio.connected:
        log("WiFi not connected, attempting to reconnect...")
        if not connect_wifi():
            log("WiFi reconnection failed")
            return None

    # Fetch weather data directly like the shared module does
    for attempt in range(3):
        log(f"Fetching fresh weather data from API (attempt {attempt + 1}/3)")
        try:
            forecast_data = weather_api.fetch_weather_data(WEATHER_CONFIG)
            if forecast_data:
                weather_data = weather_api.get_display_variables(forecast_data)
                if weather_data:
                    # Save to SD card for persistence across power cycles
                    if sd_available:
                        current_timestamp = weather_data.get("current_timestamp")
                        save_weather_data(
                            weather_data,
                            weather_data.get("forecast_data", []),
                            current_timestamp,
                        )
                    log("Weather data fetch successful")
                    return weather_data

            log("Weather API returned no data")
            if attempt < 2:
                log("Retrying in 5 seconds...")
                time.sleep(5)
                continue
            return None

        except Exception as e:
            log(f"Weather fetch error (attempt {attempt + 1}): {e}")
            if attempt < 2 and "Name or service not known" in str(e):
                log("DNS error detected, waiting 10 seconds before retry...")
                time.sleep(10)
                continue
            return None

    log("All weather fetch attempts failed")
    return None


# Main execution and loop
def main():
    """Main execution with smart deep sleep polling logic"""
    # Global state for polling
    last_successful_update = 0
    current_weather_data = None

    log("pinkweather starting...")

    # Turn on LED at boot
    led.value = True
    log("LED turned on at boot")

    # Fetch initial weather data on boot
    log("Initial weather data fetch on boot...")
    if connect_wifi():
        try:
            initial_data = get_weather_display_data()
            if initial_data:
                current_weather_data = initial_data
                update_display_with_weather_layout(current_weather_data)
                last_successful_update = time.monotonic()
                log("Initial weather fetch successful")
            else:
                log("Initial weather fetch failed")
        except Exception as e:
            log(f"Error in initial weather fetch: {e}")
    else:
        log("WiFi connection failed on boot")

    log("pinkweather ready! Entering main polling loop...")

    while True:
        current_time = time.monotonic()

        # Check if it's time for an update (hourly)
        needs_update = False
        if last_successful_update == 0:
            # Never succeeded, try now
            needs_update = True
        elif current_time - last_successful_update >= 3600:  # 60 minutes
            # Time for hourly update
            needs_update = True

        if needs_update:
            log("Time to refresh weather data...")

            # Re-establish WiFi connection
            wifi_connected = False
            try:
                wifi_connected = connect_wifi()
                if not wifi_connected:
                    log("WiFi connection failed")
                else:
                    # Attempt weather data fetch
                    fresh_data = get_weather_display_data()
                    if fresh_data:
                        current_weather_data = fresh_data
                        update_display_with_weather_layout(current_weather_data)
                        last_successful_update = current_time
                        log("Weather refresh completed successfully")
                    else:
                        log("Weather fetch failed")
            except Exception as e:
                log(f"Error during weather refresh: {e}")

        # Sleep for 60 minutes, then reboot for fresh network stack
        log("Entering deep sleep for 60 minutes...")
        deep_sleep(60)

        # After waking from deep sleep, soft reboot for fresh network stack
        log("Waking from deep sleep - rebooting for fresh network stack...")
        time.sleep(1)  # Give log time to write
        microcontroller.reset()


# Run main function
main()
