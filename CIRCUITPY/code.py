"""
PinkWeather CircuitPython Main Code
Hardware e-ink display with sensor data logging and historical averages
"""
import board
import displayio
import time
import fourwire
import adafruit_ssd1680
import adafruit_hdc302x
import adafruit_sdcard
import storage
import os
import terminalio
from digitalio import DigitalInOut
from adafruit_display_text import label
from adafruit_bitmap_font import bitmap_font
from adafruit_display_shapes.rect import Rect
from adafruit_display_shapes.line import Line

# Import shared display functions
from display import format_time_short, create_complete_display

# Release any previous display
displayio.release_displays()

# --- SPI + Pins ---
spi = board.SPI()
epd_cs = board.D9
epd_dc = board.D10
epd_reset = None
epd_busy = None

display_bus = fourwire.FourWire(
    spi, command=epd_dc, chip_select=epd_cs, reset=epd_reset, baudrate=1000000
)
time.sleep(1)

display = adafruit_ssd1680.SSD1680(
    display_bus,
    width=122,
    height=250,
    busy_pin=epd_busy,
    highlight_color=0xFF0000,
    rotation=0,
)

# Initialize sensor
i2c = board.I2C()
sensor = adafruit_hdc302x.HDC302x(i2c)

# Load fonts
font = bitmap_font.load_font("barlowcond60.pcf")
small_font = bitmap_font.load_font("barlowcond30.pcf")

# Initialize SD card
sd_available = False
try:
    cs_sd = DigitalInOut(board.D5)
    sdcard = adafruit_sdcard.SDCard(spi, cs_sd)
    vfs = storage.VfsFat(sdcard)
    storage.mount(vfs, "/sd")
    sd_available = True
    print("SD card ready")
except Exception as e:
    print(f"SD card failed: {e}")
    sd_available = False

# Colors
BLACK = 0x000000
WHITE = 0xFFFFFF
RED = 0xFF0000

DISPLAY_WIDTH = 122
DISPLAY_HEIGHT = 250

def get_historical_averages():
    """Calculate day, week, month, year averages from CSV data"""
    if not sd_available:
        return {
            'temp': {'day': 0, 'week': 0, 'month': 0, 'year': 0},
            'humidity': {'day': 0, 'week': 0, 'month': 0, 'year': 0}
        }

    current_time = time.monotonic() * 1000

    # Time periods in milliseconds
    day_ms = 24 * 60 * 60 * 1000
    week_ms = 7 * day_ms
    month_ms = 30 * day_ms
    year_ms = 365 * day_ms

    periods = {
        'day': current_time - day_ms,
        'week': current_time - week_ms,
        'month': current_time - month_ms,
        'year': current_time - year_ms
    }

    averages = {
        'temp': {'day': 0, 'week': 0, 'month': 0, 'year': 0},
        'humidity': {'day': 0, 'week': 0, 'month': 0, 'year': 0}
    }

    # Calculate averages from recent.csv
    for period_name, cutoff_time in periods.items():
        temp_sum = humidity_sum = count = 0

        try:
            with open("/sd/recent.csv", "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("uptime_ms"):  # Skip header
                        try:
                            parts = line.split(",")
                            timestamp = int(parts[0])
                            temp = float(parts[1])
                            humidity = float(parts[2])

                            if timestamp >= cutoff_time:
                                temp_sum += temp
                                humidity_sum += humidity
                                count += 1
                        except (ValueError, IndexError):
                            continue
        except OSError:
            pass  # File doesn't exist

        if count > 0:
            averages['temp'][period_name] = int(temp_sum / count)
            averages['humidity'][period_name] = int(humidity_sum / count)

    return averages

def get_graph_data(num_points=60):
    """Get recent temperature and humidity data for line graphs"""
    if not sd_available:
        return [22] * num_points, [45] * num_points  # Fallback dummy data

    temp_data = []
    humidity_data = []

    try:
        with open("/sd/recent.csv", "r") as f:
            lines = []
            for line in f:
                line = line.strip()
                if line and not line.startswith("uptime_ms"):  # Skip header
                    lines.append(line)

            # Get the last num_points entries
            recent_lines = lines[-num_points:] if len(lines) >= num_points else lines

            for line in recent_lines:
                try:
                    parts = line.split(",")
                    temp = float(parts[1])
                    humidity = float(parts[2])
                    temp_data.append(temp)
                    humidity_data.append(humidity)
                except (ValueError, IndexError):
                    continue
    except OSError:
        pass  # File doesn't exist

    # Fill with current values if we don't have enough points
    if len(temp_data) < num_points and temp_data:
        first_temp = temp_data[0]
        first_humidity = humidity_data[0]
        while len(temp_data) < num_points:
            temp_data.insert(0, first_temp)
            humidity_data.insert(0, first_humidity)
    elif len(temp_data) == 0:
        # No data at all, use dummy data
        temp_data = [22] * num_points
        humidity_data = [45] * num_points

    return temp_data[-num_points:], humidity_data[-num_points:]

def get_sd_total_time():
    """Get total time span of data stored on SD card"""
    if not sd_available:
        return "0s"

    try:
        min_time = None
        max_time = None

        with open("/sd/recent.csv", "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("uptime_ms"):
                    try:
                        timestamp = int(line.split(",")[0])
                        if min_time is None or timestamp < min_time:
                            min_time = timestamp
                        if max_time is None or timestamp > max_time:
                            max_time = timestamp
                    except (ValueError, IndexError):
                        continue

        if min_time and max_time:
            total_seconds = (max_time - min_time) / 1000
            return format_time_short(total_seconds)
    except OSError:
        pass

    return "0s"

def update_display(temp_c, humidity):
    """Update display with sensor readings and historical data"""
    # Get data for display
    averages = get_historical_averages()
    temp_data, humidity_data = get_graph_data()

    # Get status information
    sd_status = "SD" if sd_available else "NOD"
    sd_time = get_sd_total_time()
    uptime = format_time_short(time.monotonic())
    power_status = "P"
    battery_status = "B--"

    # Create display using shared function
    g = create_complete_display(
        temp_c, humidity, averages, temp_data, humidity_data,
        sd_status, sd_time, uptime, power_status, battery_status
    )

    # Set as display root and refresh
    display.root_group = g
    display.refresh()

def log_sensor_data(temp_c, humidity):
    """Log sensor data to CSV files"""
    if not sd_available:
        return False

    try:
        uptime_ms = int(time.monotonic() * 1000)
        with open("/sd/recent.csv", "a") as f:
            f.write(f"{uptime_ms},{temp_c:.1f},{humidity:.1f}\n")
        return True
    except Exception as e:
        print(f"Log failed: {e}")
        return False

def initialize_csv_files():
    """Create CSV files with headers if they don't exist"""
    if not sd_available:
        return

    csv_files = [
        ("/sd/recent.csv", "uptime_ms,temp_c,humidity_pct"),
        ("/sd/hourly.csv", "uptime_ms,temp_c,humidity_pct"),
        ("/sd/daily.csv", "uptime_ms,temp_c,humidity_pct")
    ]

    for filepath, header in csv_files:
        try:
            with open(filepath, "r") as f:
                pass
        except OSError:
            try:
                with open(filepath, "w") as f:
                    f.write(header + "\n")
                print(f"Created {filepath}")
            except Exception as e:
                print(f"Failed to create {filepath}: {e}")

# Initialize CSV files
if sd_available:
    initialize_csv_files()

# Initialize with first reading
current_temp = int(round(sensor.temperature))
current_humidity = int(round(sensor.relative_humidity))
update_display(sensor.temperature, sensor.relative_humidity)
print(f"Initial: {current_temp}°C, {current_humidity}% | SD: {'OK' if sd_available else 'FAIL'}")

# Track last values and update time
last_temp = current_temp
last_humidity = current_humidity
last_update_time = time.monotonic()
display_busy_printed = False

# Main loop
while True:
    if display.busy:
        if not display_busy_printed:
            print("Display busy...")
            display_busy_printed = True
        time.sleep(1)
    else:
        display_busy_printed = False
        time.sleep(30)  # Check every 30 seconds

        # Get current readings
        current_temp = int(round(sensor.temperature))
        current_humidity = int(round(sensor.relative_humidity))
        current_time = time.monotonic()

        # Check if values changed and enough time has passed (3 minutes = 180 seconds)
        values_changed = (current_temp != last_temp or current_humidity != last_humidity)
        time_elapsed = (current_time - last_update_time >= 180)

        if values_changed and time_elapsed:
            print(f"Update: {current_temp}°C, {current_humidity}%")
            update_display(sensor.temperature, sensor.relative_humidity)

            # Log sensor data
            if sd_available:
                log_sensor_data(sensor.temperature, sensor.relative_humidity)

            last_temp = current_temp
            last_humidity = current_humidity
            last_update_time = current_time
