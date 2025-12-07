import board
import displayio
import time
import fourwire
import adafruit_ssd1680
import adafruit_hdc302x
import adafruit_sdcard
import storage

# import os
import terminalio
from digitalio import DigitalInOut
from adafruit_display_text import label
from adafruit_bitmap_font import bitmap_font
from adafruit_display_shapes.rect import Rect
from adafruit_display_shapes.line import Line

# release any previous display
displayio.release_displays()

# --- SPI + Pins ---
spi = board.SPI()
epd_cs = board.D9
epd_dc = board.D10
epd_reset = None # adafruit feather wing doesn't connect this
epd_busy = None # adafruit feather wing doesn't connect this

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
    sd_card = adafruit_sdcard.SDCard(spi, cs_sd)
    vfs = storage.VfsFat(sd_card)
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


def create_temp_display(temp_c):
    """Create temperature display"""
    temp_int = int(round(temp_c))
    is_negative = temp_int < 0
    temp_str = str(abs(temp_int))

    group = displayio.Group()
    x = 0

    # Minus sign if negative
    if is_negative:
        minus = label.Label(small_font, text="-", color=BLACK)
        minus.x = x
        minus.y = 0
        group.append(minus)
        x += 15

    # Number
    number = label.Label(font, text=temp_str, color=BLACK)
    number.x = x
    number.y = 0
    group.append(number)
    x += len(temp_str) * 30  # rough width estimate

    # Degree symbol (superscript)
    degree = label.Label(small_font, text="°", color=BLACK)
    degree.x = x + 5  # nudge +5 right
    degree.y = -10
    group.append(degree)

    return group


def create_humidity_display(humidity):
    """Create humidity display"""
    humidity_str = str(int(round(humidity)))

    group = displayio.Group()

    # Number
    number = label.Label(font, text=humidity_str, color=RED)
    number.x = 0
    number.y = 0
    group.append(number)

    # Percent symbol (baseline)
    percent = label.Label(small_font, text="%", color=RED)
    percent.x = len(humidity_str) * 30 + 5  # rough width estimate, +5 nudge
    percent.y = 15
    group.append(percent)

    return group


def get_historical_averages():
    """Calculate day, week, month, year averages from all CSV data sources"""
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

    averages = {
        'temp': {'day': 0, 'week': 0, 'month': 0, 'year': 0},
        'humidity': {'day': 0, 'week': 0, 'month': 0, 'year': 0}
    }

    # Calculate averages using appropriate data sources for each period
    for period in ['day', 'week', 'month', 'year']:
        temp_sum = humidity_sum = count = 0

        if period == 'day':
            # Use recent.csv for last 24 hours
            cutoff_time = current_time - day_ms
            temp_sum, humidity_sum, count = read_csv_data("/sd/recent.csv", cutoff_time)
        elif period == 'week':
            # Use recent.csv + hourly.csv for last 7 days
            cutoff_time = current_time - week_ms
            temp_sum1, humidity_sum1, count1 = read_csv_data("/sd/recent.csv", cutoff_time)
            temp_sum2, humidity_sum2, count2 = read_csv_data("/sd/hourly.csv", cutoff_time)
            temp_sum, humidity_sum, count = temp_sum1 + temp_sum2, humidity_sum1 + humidity_sum2, count1 + count2
        elif period == 'month':
            # Use hourly.csv + daily.csv for last 30 days
            cutoff_time = current_time - month_ms
            temp_sum1, humidity_sum1, count1 = read_csv_data("/sd/hourly.csv", cutoff_time)
            temp_sum2, humidity_sum2, count2 = read_csv_data("/sd/daily.csv", cutoff_time)
            temp_sum, humidity_sum, count = temp_sum1 + temp_sum2, humidity_sum1 + humidity_sum2, count1 + count2
        else:  # year
            # Use daily.csv for last 365 days
            cutoff_time = current_time - year_ms
            temp_sum, humidity_sum, count = read_csv_data("/sd/daily.csv", cutoff_time)

        if count > 0:
            averages['temp'][period] = int(temp_sum / count)
            averages['humidity'][period] = int(humidity_sum / count)

    return averages

def read_csv_data(filepath, cutoff_time):
    """Helper to read CSV data after cutoff time"""
    temp_sum = humidity_sum = count = 0
    try:
        with open(filepath, "r") as f:
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

    return temp_sum, humidity_sum, count


def create_line_graph(data_points, color, y_start, height):
    """Create a simple line graph from data points with thick lines and min/max labels"""
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

        # Draw multiple parallel lines to make it thicker (2px thick)
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

            # Get the last num_points entries, or all if we have fewer
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

    # Temperature averages (day, week, month, year)
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

    # Humidity averages (right under the graph)
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

    # Refresh display
    display.refresh()


def log_sensor_data(temp_c, humidity):
    """Log sensor data to CSV files with rotation"""
    if not sd_available:
        return False

    try:
        uptime_ms = int(time.monotonic() * 1000)

        # Log to recent.csv (every reading)
        with open("/sd/recent.csv", "a") as f:
            f.write(f"{uptime_ms},{temp_c:.1f},{humidity:.1f}\n")

        # Aggregate data to longer-term files
        aggregate_data_files()

        return True
    except Exception as e:
        print(f"Log failed: {e}")
        return False

def aggregate_data_files():
    """Aggregate data from recent.csv to hourly.csv and daily.csv when needed"""
    try:
        # Check if we should create hourly aggregates (every ~100 recent entries)
        recent_count = count_csv_lines("/sd/recent.csv")
        if recent_count > 0 and recent_count % 100 == 0:
            create_hourly_aggregate()

        # Check if we should create daily aggregates (every ~48 hourly entries)
        hourly_count = count_csv_lines("/sd/hourly.csv")
        if hourly_count > 0 and hourly_count % 48 == 0:
            create_daily_aggregate()

        # Keep recent.csv manageable (last 2000 entries for ~1 week at 3min intervals)
        if recent_count > 2000:
            trim_csv_file("/sd/recent.csv", 2000)

        # Keep hourly.csv manageable (last 1000 entries for ~6 weeks)
        if hourly_count > 1000:
            trim_csv_file("/sd/hourly.csv", 1000)

    except:
        pass  # Ignore errors in aggregation

def count_csv_lines(filepath):
    """Count non-header lines in CSV file"""
    try:
        count = 0
        with open(filepath, "r") as f:
            for line in f:
                if not line.strip().startswith("uptime_ms"):
                    count += 1
        return count
    except:
        return 0

def trim_csv_file(filepath, keep_lines):
    """Keep only the last keep_lines entries in CSV file"""
    try:
        lines = []
        with open(filepath, "r") as f:
            lines = f.readlines()

        if len(lines) > keep_lines + 1:  # +1 for header
            with open(filepath, "w") as f:
                f.write(lines[0])  # Write header
                f.writelines(lines[-(keep_lines):])  # Write last keep_lines entries
    except:
        pass

def create_hourly_aggregate():
    """Create hourly averages from recent data"""
    try:
        current_time = time.monotonic() * 1000
        hour_ago = current_time - (60 * 60 * 1000)  # 1 hour ago

        temp_sum, humidity_sum, count = read_csv_data("/sd/recent.csv", hour_ago)

        if count > 0:
            avg_temp = temp_sum / count
            avg_humidity = humidity_sum / count

            with open("/sd/hourly.csv", "a") as f:
                f.write(f"{int(current_time)},{avg_temp:.1f},{avg_humidity:.1f}\n")
    except:
        pass

def create_daily_aggregate():
    """Create daily averages from hourly data"""
    try:
        current_time = time.monotonic() * 1000
        day_ago = current_time - (24 * 60 * 60 * 1000)  # 1 day ago

        temp_sum, humidity_sum, count = read_csv_data("/sd/hourly.csv", day_ago)

        if count > 0:
            avg_temp = temp_sum / count
            avg_humidity = humidity_sum / count

            with open("/sd/daily.csv", "a") as f:
                f.write(f"{int(current_time)},{avg_temp:.1f},{avg_humidity:.1f}\n")
    except:
        pass


def initialize_csv_files():
    """Create CSV files with headers if they don't exist"""
    if not sd_available:
        return

    csv_files = [
        ("/sd/recent.csv", "uptime_ms,temp_c,humidity_pct"),
        ("/sd/hourly.csv", "uptime_ms,temp_c,humidity_pct"),
        ("/sd/daily.csv", "uptime_ms,temp_c,humidity_pct"),
    ]

    for filepath, header in csv_files:
        try:
            # Check if file exists
            with open(filepath, "r") as f:
                pass
        except OSError:
            # File doesn't exist, create with header
            try:
                with open(filepath, "w") as f:
                    f.write(header + "\n")
                print(f"Created {filepath}")
            except Exception as e:
                print(f"Failed to create {filepath}: {e}")


def test_sd_card():
    """Test basic SD card functionality"""
    if not sd_available:
        return False

    try:
        with open("/sd/test.txt", "w") as f:
            f.write(f"Test: {time.monotonic()}\n")
        return True
    except:
        return False


# Test SD card and initialize CSV files
sd_working = test_sd_card()
if sd_working:
    initialize_csv_files()

# Initialize with first reading
last_temp = None
last_humidity = None

# Initial display update
temp_c = sensor.temperature
humidity = sensor.relative_humidity
update_display(temp_c, humidity)
last_temp = int(round(temp_c))
last_humidity = int(round(humidity))
print(
    f"Initial: {last_temp}°C, {last_humidity}% | SD: {'OK' if sd_working else 'FAIL'}"
)

# Main loop - check every 30 seconds, update display only if changed and at least 3 minutes passed
last_update_time = time.monotonic()
display_busy_printed = False

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
        values_changed = current_temp != last_temp or current_humidity != last_humidity
        time_elapsed = current_time - last_update_time >= 180

        if values_changed and time_elapsed:
            print(f"Update: {current_temp}°C, {current_humidity}%")
            update_display(sensor.temperature, sensor.relative_humidity)

            # Log sensor data
            if sd_working:
                log_sensor_data(sensor.temperature, sensor.relative_humidity)

            last_temp = current_temp
            last_humidity = current_humidity
            last_update_time = current_time
