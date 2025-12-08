"""
Shared display rendering functions for PinkWeather
Used by both hardware (CircuitPython) and web preview

This contains all the display layout and positioning logic.
Changes here affect both hardware and web rendering.
"""

import displayio
import terminalio
from adafruit_display_text import label
from adafruit_bitmap_font import bitmap_font
from adafruit_display_shapes.rect import Rect
from adafruit_display_shapes.line import Line

# Hardware constants
DISPLAY_WIDTH = 122
DISPLAY_HEIGHT = 250
BLACK = 0x000000
WHITE = 0xFFFFFF
RED = 0xFF0000

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

def create_temp_display(temp_c, font, small_font):
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
    degree.x = x + 6  # Add 6px spacing (was 4px, adjusted for web compatibility)
    degree.y = -10
    group.append(degree)

    return group

def create_humidity_display(humidity, font, small_font):
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
    percent.x = len(humidity_str) * 30 + 4  # rough width estimate + 4px spacing
    percent.y = 15
    group.append(percent)

    return group

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

def create_complete_display(temp_c, humidity, averages, temp_data, humidity_data, sd_status, sd_time, uptime, power_status, battery_status):
    """Create complete display layout - shared between hardware and web"""

    # Load fonts
    font = bitmap_font.load_font("barlowcond60.pcf")
    small_font = bitmap_font.load_font("barlowcond30.pcf")

    # Create main group
    g = displayio.Group()

    # Background
    bg = Rect(0, 0, DISPLAY_WIDTH, DISPLAY_HEIGHT, fill=WHITE)
    g.append(bg)

    # Current temperature (top)
    temp_group = create_temp_display(temp_c, font, small_font)
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
    humidity_group = create_humidity_display(humidity, font, small_font)
    humidity_group.x = 20
    humidity_group.y = humidity_y_start + humidity_height + 38
    g.append(humidity_group)

    # Status bar at bottom
    status_bar_height = 12
    status_bar_y = DISPLAY_HEIGHT - status_bar_height
    status_bar = Rect(0, status_bar_y, DISPLAY_WIDTH, status_bar_height, fill=BLACK)
    g.append(status_bar)

    # Status text (using terminalio.FONT)
    status_text = f"{sd_status} {sd_time} {uptime} {power_status} {battery_status}"
    status_label = label.Label(terminalio.FONT, text=status_text, color=WHITE)
    status_label.anchor_point = (0.5, 0.5)
    status_label.anchored_position = (DISPLAY_WIDTH // 2, status_bar_y + 6)
    g.append(status_label)

    return g
