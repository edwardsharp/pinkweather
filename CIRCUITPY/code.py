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

def format_time_short(seconds):
    """Format time in very short format: 30s, 9d, 25m, etc."""
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:  # < 1 hour
        return f"{int(seconds/60)}m"
    elif seconds < 86400:  # < 1 day
        return f"{int(seconds/3600)}h"
    elif seconds < 2592000:  # < 30 days
        return f"{int(seconds/86400)}d"
    elif seconds < 31536000:  # < 365 days
        return f"{int(seconds/2592000)}M"
    else:
        return f"{int(seconds/31536000)}y"

def create_temp_display(temp_c):
    """Create temperature display"""
    temp_int = int(round(temp_c))
    is_negative = temp_int < 0
    temp_str = str(abs(temp_int))

    group = displayio.Group()
    x = 0

    # Minus sign if negative (using small font)
    if is_negative:
        minus = label.Label(small_font, text="-", color=BLACK)
        minus.x = x
        minus.y = 0
        group.append(minus)
        x += 15

    # Number (using large font)
    number = label.Label(font, text=temp_str, color=BLACK)
    number.x = x
    number.y = 0
    group.append(number)
    x += len(temp_str) * 30  # rough width estimate

    # Degree symbol (superscript, using small font)
    degree = label.Label(small_font, text="°", color=BLACK)
    degree.x = x
    degree.y = -10
    group.append(degree)

    return group

def create_humidity_display(humidity):
    """Create humidity display"""
    humidity_str = str(int(round(humidity)))

    group = displayio.Group()

    # Number (using large font)
    number = label.Label(font, text=humidity_str, color=RED)
    number.x = 0
    number.y = 0
    group.append(number)

    # Percent symbol (baseline, using small font)
    percent = label.Label(small_font, text="%", color=RED)
    percent.x = len(humidity_str) * 30  # rough width estimate
    percent.y = 15
    group.append(percent)

    return group

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

def create_line_graph(data_points, color, y_start, height):
    """Create line graph with thick lines and min/max labels"""
    if len(data_points) < 2:
        return displayio.Group()

    group = displayio.Group()
    graph_width = DISPLAY_WIDTH  # Full width
    x_step = graph_width // (len(data_points) - 1) if len(data_points) > 1 else 0

    # Normalize data to fit in height
    min_val = min(data_points)
    max_val = max(data_points)
    val_range = max_val - min_val if max_val != min_val else 1

    for i in range(len(data_points) - 1):
        x1 = 10 + i * x_step
        x2 = 10 + (i + 1) * x_step

        # Scale y values
        y1 = y_start + height - int(((data_points[i] - min_val) / val_range) * height)
        y2 = y_start + height - int(((data_points[i + 1] - min_val) / val_range) * height)

        # Draw thick lines (2px thick)
        line1 = Line(x1, y1, x2, y2, color)
        line2 = Line(x1, y1 + 1, x2, y2 + 1, color)
        group.append(line1)
        group.append(line2)

    # Add min/max labels with colored backgrounds
    # Max label (top left)
    max_bg = Rect(0, y_start - 2, 16, 14, fill=color)
    group.append(max_bg)
    max_label = label.Label(terminalio.FONT, text=f"{int(max_val)}", color=WHITE)
    max_label.x = 2
    max_label.y = y_start + 5
    group.append(max_label)

    # Min label (bottom left)
    min_bg = Rect(0, y_start + height - 12, 16, 14, fill=color)
    group.append(min_bg)
    min_label = label.Label(terminalio.FONT, text=f"{int(min_val)}", color=WHITE)
    min_label.x = 2
    min_label.y = y_start + height - 5
    group.append(min_label)

    return group

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
    # Clear display
    g = displayio.Group()
    display.root_group = g

    # Background
    bg = Rect(0, 0, DISPLAY_WIDTH, DISPLAY_HEIGHT, fill=WHITE)
    g.append(bg)

    # Get historical averages
    averages = get_historical_averages()

    # Current temperature (top)
    temp_group = create_temp_display(temp_c)
    temp_group.x = 20
    temp_group.y = 25
    g.append(temp_group)

    # Temperature averages (using terminalio.FONT)
    temp_avg_text = f"D:{averages['temp']['day']} W:{averages['temp']['week']} M:{averages['temp']['month']} Y:{averages['temp']['year']}"
    temp_avg_label = label.Label(terminalio.FONT, text=temp_avg_text, color=BLACK)
    temp_avg_label.anchor_point = (0.5, 0.5)
    temp_avg_label.anchored_position = (DISPLAY_WIDTH // 2, 75)
    g.append(temp_avg_label)

    # Line graphs with real historical data
    temp_data, humidity_data = get_graph_data()

    # Temperature graph with border
    temp_y_start = 84
    temp_height = 32
    temp_border = Rect(0, temp_y_start - 2, DISPLAY_WIDTH, temp_height + 4, outline=BLACK, stroke=2)
    g.append(temp_border)
    temp_graph = create_line_graph(temp_data, BLACK, temp_y_start, temp_height)
    g.append(temp_graph)

    # Humidity graph with border
    humidity_y_start = 124
    humidity_height = 32
    humidity_border = Rect(0, humidity_y_start - 2, DISPLAY_WIDTH, humidity_height + 4, outline=RED, stroke=2)
    g.append(humidity_border)
    humidity_graph = create_line_graph(humidity_data, RED, humidity_y_start, humidity_height)
    g.append(humidity_graph)

    # Humidity averages (using terminalio.FONT)
    humidity_avg_text = f"D:{averages['humidity']['day']} W:{averages['humidity']['week']} M:{averages['humidity']['month']} Y:{averages['humidity']['year']}"
    humidity_avg_label = label.Label(terminalio.FONT, text=humidity_avg_text, color=RED)
    humidity_avg_label.anchor_point = (0.5, 0.5)
    humidity_avg_label.anchored_position = (DISPLAY_WIDTH // 2, humidity_y_start + humidity_height + 10)
    g.append(humidity_avg_label)

    # Current humidity (bottom area)
    humidity_group = create_humidity_display(humidity)
    humidity_group.x = 20
    humidity_group.y = humidity_y_start + humidity_height + 38
    g.append(humidity_group)

    # Status bar at bottom
    status_bar_height = 12
    status_bar_y = DISPLAY_HEIGHT - status_bar_height
    status_bar = Rect(0, status_bar_y, DISPLAY_WIDTH, status_bar_height, fill=BLACK)
    g.append(status_bar)

    # Status text (using terminalio.FONT)
    sd_status = "SD" if sd_available else "NOD"
    sd_time = get_sd_total_time()
    uptime = format_time_short(time.monotonic())
    power_status = "P"
    battery_status = "B--"

    status_text = f"{sd_status} {sd_time} {uptime} {power_status} {battery_status}"
    status_label = label.Label(terminalio.FONT, text=status_text, color=WHITE)
    status_label.anchor_point = (0.5, 0.5)
    status_label.anchored_position = (DISPLAY_WIDTH // 2, status_bar_y + 6)
    g.append(status_label)

    # Refresh display
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
