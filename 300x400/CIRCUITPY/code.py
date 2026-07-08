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
import terminalio
import wifi
from adafruit_display_text import label, wrap_text_to_pixels
from digitalio import DigitalInOut

# shared display functions
from display.weather_display import create_weather_display_layout
from filesystem.filesystem import FileSystem
from utils.logger import log, log_error, set_log_level
from utils.logger import set_filesystem as set_logger_filesystem
from weather.date_utils import format_timestamp_to_date
from weather import weather_api
from weather.weather_history import set_filesystem as set_weather_history_filesystem
from weather.weather_persistence import load_weather_data, save_weather_data
from weather.weather_persistence import (
    set_filesystem as set_weather_persistence_filesystem,
)

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

    # Create and inject filesystem dependencies
    filesystem = FileSystem()
    set_logger_filesystem(filesystem)
    set_weather_persistence_filesystem(filesystem)
    set_weather_history_filesystem(filesystem)

    # Remove any .tmp files from a previously interrupted write before doing
    # anything else on the SD card.
    _cleaned = filesystem.cleanup_tmp_files()

    log("SD card ready and filesystem dependencies injected")
    if _cleaned:
        log(f"Cleaned up {_cleaned} leftover .tmp file(s) from interrupted write")

except Exception as e:
    log_error(f"SD card failed: {e}")
    log("Continuing without SD card...")
    sd_available = False

# Initialize logging level from config
set_log_level(getattr(config, "LOG_LEVEL", "INFO"))

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
    log_error(f"Temperature sensor failed to initialize: {e}")
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
        return f"{current_temp}°{current_humidity}%"
    except Exception as e:
        log_error(f"Failed to read sensor: {e}")
        return None


def check_memory():
    """Check available memory and force collection if low"""
    gc.collect()
    free_mem = gc.mem_free()
    if free_mem < 2048:  # If less than 2KB free
        log(f"LOW MEMORY: {free_mem} bytes free")
        gc.collect()
    return free_mem


def read_failure_state():
    """Read WiFi failure state from SD card"""
    if not sd_available:
        return {"failures": 0, "ever_succeeded": False}

    try:
        with open("/sd/wifi_state.txt", "r") as f:
            lines = f.read().strip().split("\n")
            failures = int(lines[0]) if len(lines) > 0 else 0
            ever_succeeded = lines[1] == "True" if len(lines) > 1 else False
            return {"failures": failures, "ever_succeeded": ever_succeeded}
    except:
        return {"failures": 0, "ever_succeeded": False}


def write_failure_state(failures, ever_succeeded):
    """Write WiFi failure state to SD card"""
    if not sd_available:
        return

    try:
        with open("/sd/wifi_state.txt", "w") as f:
            f.write(f"{failures}\n{ever_succeeded}\n")
    except Exception as e:
        log_error(f"Failed to write failure state: {e}")


def show_error_screen(message):
    """Display error screen with sad cloud icon and message"""
    log(f"Showing error screen: {message}")

    # Create display group
    error_group = displayio.Group()

    # Load sad cloud background if available
    sad_cloud = load_bmp_icon("sadcloud.bmp")
    if sad_cloud:
        sad_cloud.y = 5
        error_group.append(sad_cloud)

    error_group.append(
        label.Label(
            terminalio.FONT,
            text="onoz! error! don't panic ucanfix!",
            color=WHITE,
            background_color=RED,
            x=5,
            y=10,
            scale=2,
        )
    )

    message = message or "an unexpected error occurred."

    text_area = label.Label(
        terminalio.FONT,
        text="\n".join(wrap_text_to_pixels(message, 380, terminalio.FONT)),
        color=BLACK,
        background_color=WHITE,
        x=10,
        y=205,
    )
    error_group.append(text_area)

    # Update display
    display.root_group = error_group
    display.refresh()
    time.sleep(20)


def load_bmp_icon(filename):
    """Load BMP icon from SD card with error handling"""
    if not sd_available:
        return None

    try:
        file_path = f"/sd/bmp/{filename}"
        pic = displayio.OnDiskBitmap(file_path)
        return displayio.TileGrid(pic, pixel_shader=pic.pixel_shader)
    except Exception as e:
        log_error(f"Failed to load {filename}: {e}")
        return None


def update_display_with_weather_layout(weather_data):
    """Create weather layout with single-line header using provided weather data"""
    check_memory()

    if not weather_data:
        log("No weather data available - cannot create display")
        return

    log("Creating weather layout...")

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


def connect_wifi():
    """Connect to WiFi with detailed diagnostics, optional static IP, and channel hint"""
    if config.WIFI_SSID is None or config.WIFI_PASSWORD is None:
        log("WiFi credentials not configured")
        show_error_screen("WiFi Not Configured\nCheck config.py file")
        return False

    channel = getattr(config, "WIFI_CHANNEL", 0)
    timeout = getattr(config, "WIFI_CONNECT_TIMEOUT", 20)
    static_ip = getattr(config, "WIFI_STATIC_IP", None)
    log(
        f"Connecting to '{config.WIFI_SSID}' "
        f"(channel={'auto' if channel == 0 else channel}, "
        f"timeout={timeout}s, "
        f"ip={'static' if static_ip else 'dhcp'})"
    )

    try:
        # Ensure clean state
        if wifi.radio.connected:
            log("Stopping existing station connection...")
            wifi.radio.stop_station()

        wifi.radio.enabled = False
        time.sleep(1)
        wifi.radio.enabled = True
        time.sleep(2)

        # Configure static IP *before* connecting to skip DHCP negotiation entirely.
        # This is the most reliable fix for DHCP pool exhaustion or slow DHCP servers.
        if static_ip:
            try:
                import ipaddress
                netmask = getattr(config, "WIFI_STATIC_NETMASK", "255.255.255.0")
                gateway = getattr(config, "WIFI_STATIC_GATEWAY", None)
                dns = getattr(config, "WIFI_STATIC_DNS", None)
                log(f"Static IP: {static_ip} / {netmask} gw {gateway} dns {dns}")
                wifi.radio.set_ipv4_address(
                    ipv4=ipaddress.IPv4Address(static_ip),
                    netmask=ipaddress.IPv4Address(netmask),
                    gateway=ipaddress.IPv4Address(gateway) if gateway else None,
                    ipv4_dns=ipaddress.IPv4Address(dns) if dns else None,
                )
                log("Static IP configured")
            except Exception as ip_err:
                log_error(f"Static IP config failed ({type(ip_err).__name__}): {ip_err}")
                log("Falling back to DHCP")

        # Connect — channel hint skips a full 13-channel scan when set
        wifi.radio.connect(
            config.WIFI_SSID,
            config.WIFI_PASSWORD,
            channel=channel,
            timeout=timeout,
        )

        # Log connection details
        log(f"Connected! IPv4: {wifi.radio.ipv4_address}")

        # Log AP info: signal strength, actual channel, BSSID
        try:
            ap = wifi.radio.ap_info
            if ap:
                bssid_str = ":".join("{:02x}".format(b) for b in ap.bssid)
                log(
                    f"AP info: rssi={ap.rssi}dBm  "
                    f"channel={ap.channel}  "
                    f"bssid={bssid_str}"
                )
        except Exception as ap_err:
            log(f"AP info unavailable: {ap_err}")

        # Success — reset failure counter
        write_failure_state(0, True)
        time.sleep(2)
        return True

    except Exception as e:
        error_type = type(e).__name__
        log_error(f"WiFi connect failed [{error_type}]: {e}")
        log_error(
            f"  ssid={config.WIFI_SSID}  channel={channel}  "
            f"timeout={timeout}s  ip={'static' if static_ip else 'dhcp'}"
        )

        # Classify error and build a brief, human-readable display message
        err_lower = str(e).lower()
        if "timeout" in err_lower or "timed out" in err_lower:
            diagnosis_log = (
                "  Diagnosis: connection timed out. "
                "Possible causes: DHCP pool exhausted, router busy, or weak signal. "
                "Try: set WIFI_STATIC_IP to skip DHCP, increase WIFI_CONNECT_TIMEOUT, "
                "or set WIFI_CHANNEL to your router's channel."
            )
            diagnosis_display = (
                f"wifi timed out connecting to {config.WIFI_SSID}. "
                "your router's dhcp pool may be full or signal is weak. "
                "try setting wifi_static_ip in config.py, "
                "or increase wifi_connect_timeout."
            )
        elif any(w in err_lower for w in ("auth", "password", "denied", "handshake")):
            diagnosis_log = (
                "  Diagnosis: authentication failed. "
                "Check WIFI_SSID and WIFI_PASSWORD in config.py."
            )
            diagnosis_display = (
                "wifi password was rejected. "
                "check wifi_ssid and wifi_password in config.py."
            )
        elif any(w in err_lower for w in ("no ssid", "not found", "no ap")):
            diagnosis_log = (
                "  Diagnosis: network not found. "
                "Check WIFI_SSID spelling, or try WIFI_CHANNEL=0 for a full scan."
            )
            diagnosis_display = (
                f"wifi network '{config.WIFI_SSID}' not found. "
                "check wifi_ssid in config.py, "
                "or try moving closer to your router."
            )
        else:
            diagnosis_log = (
                "  Diagnosis: unknown error — try rebooting or checking router logs."
            )
            diagnosis_display = (
                f"wifi failed ({error_type}). "
                "check your router is on and config.py looks right."
            )
        log_error(diagnosis_log)

        # Update failure state
        state = read_failure_state()
        new_failures = state["failures"] + 1
        ever_succeeded = state["ever_succeeded"]
        write_failure_state(new_failures, ever_succeeded)

        # Only show the sad-cloud error screen when:
        # - device has never connected before (setup issue), OR
        # - failures have exceeded the cache window (truly stuck)
        cache_max = getattr(config, "WEATHER_CACHE_MAX_CYCLES", 6)
        if not ever_succeeded or new_failures > cache_max:
            if not ever_succeeded:
                # First-time setup: give generic config guidance
                display_msg = (
                    f"can't connect to {config.WIFI_SSID}. "
                    "check wifi_ssid and wifi_password in config.py "
                    "(connect via usb to edit it)."
                )
            else:
                display_msg = diagnosis_display
            show_error_screen(display_msg)

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
        log_error(f"Error disconnecting WiFi: {e}")
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


def get_cached_weather_data():
    """Load cached weather data from SD card if it is within the configured staleness window.

    Staleness is measured in *consecutive failed update cycles* rather than wall-clock time
    (we have no RTC). Each cycle is ~1 hour, so WEATHER_CACHE_MAX_CYCLES=6 means the cache
    is trusted for up to ~6 consecutive hours of WiFi/API failures.

    Returns the weather_data dict if the cache is valid, or None if unavailable/too old.
    """
    if not sd_available:
        return None

    cache_max = getattr(config, "WEATHER_CACHE_MAX_CYCLES", 6)
    if cache_max <= 0:
        log("Weather cache disabled (WEATHER_CACHE_MAX_CYCLES=0)")
        return None

    # Read how many consecutive failures we've accumulated
    state = read_failure_state()
    failures = state["failures"]

    if failures > cache_max:
        log(
            f"Cache expired: {failures} consecutive failures "
            f"exceeds limit of {cache_max} cycles"
        )
        return None

    saved = load_weather_data()
    if not saved:
        log("No cached weather data on SD card")
        return None

    weather_data = saved.get("weather_data")
    if not weather_data:
        log("Cached data missing weather_data key")
        return None

    log(
        f"Using cached weather data "
        f"(failure cycle {failures}/{cache_max}, "
        f"saved timestamp={saved.get('timestamp')})"
    )

    # Best-effort current time estimate.
    # We have no RTC, but: saved_timestamp + (failed cycles * ~1hr) + seconds-since-boot
    # gives a rough local unix time. This keeps the date header and moon phase
    # approximately correct during WiFi outages.
    try:
        saved_ts = saved.get("timestamp")
        if saved_ts:
            estimated_ts = int(saved_ts) + (failures * 3600) + int(time.monotonic())
            weather_data = dict(weather_data)  # shallow copy — don't mutate cached dict
            weather_data["current_timestamp"] = estimated_ts
            date_info = format_timestamp_to_date(estimated_ts)
            weather_data["day_name"] = date_info["day_name"]
            weather_data["day_num"] = date_info["day_num"]
            weather_data["month_name"] = date_info["month_name"]
            log(
                f"Estimated time: {date_info['day_name']} "
                f"{date_info['day_num']} {date_info['month_name']} "
                f"(ts={estimated_ts})"
            )
    except Exception as te:
        log(f"Could not estimate current time from cache: {te}")

    return weather_data


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
            log_error(f"Weather fetch error (attempt {attempt + 1}): {e}")
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

    print("hello pinkweather!")

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
                log("Initial weather fetch failed, checking cache...")
                cached = get_cached_weather_data()
                if cached:
                    current_weather_data = cached
                    update_display_with_weather_layout(current_weather_data)
                    log("Showing cached weather data (initial boot)")
                else:
                    log("No cache available on boot")
        except Exception as e:
            log_error(f"Error in initial weather fetch: {e}")
    else:
        log("WiFi connection failed on boot, checking cache...")
        cached = get_cached_weather_data()
        if cached:
            current_weather_data = cached
            update_display_with_weather_layout(current_weather_data)
            log("Showing cached weather data (WiFi failed on boot)")
        else:
            log("No cache available and WiFi failed on boot")

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
                    log("WiFi connection failed, checking cache...")
                    cached = get_cached_weather_data()
                    if cached:
                        current_weather_data = cached
                        update_display_with_weather_layout(current_weather_data)
                        log("Showing cached weather data (WiFi unavailable)")
                else:
                    # Attempt weather data fetch
                    fresh_data = get_weather_display_data()
                    if fresh_data:
                        current_weather_data = fresh_data
                        update_display_with_weather_layout(current_weather_data)
                        last_successful_update = current_time
                        log("Weather refresh completed successfully")
                    else:
                        log("Weather fetch failed, checking cache...")
                        cached = get_cached_weather_data()
                        if cached:
                            current_weather_data = cached
                            update_display_with_weather_layout(current_weather_data)
                            log("Showing cached weather data (API unavailable)")
                        else:
                            log("Weather fetch failed and no cache available")
            except Exception as e:
                log_error(f"Error during weather refresh: {e}")

        # Sleep for 60 minutes, then reboot for fresh network stack
        log("Entering deep sleep for 60 minutes...")
        print("done! gonna take a 60 minute nap zZz...")
        deep_sleep(60)

        # After waking from deep sleep, soft reboot for fresh network stack
        log("Waking from deep sleep - rebooting for fresh network stack...")
        time.sleep(1)  # Give log time to write
        microcontroller.reset()


# Run main function
main()
