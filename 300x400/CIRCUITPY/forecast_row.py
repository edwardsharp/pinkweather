"""
Hourly forecast row with stacked cells (time, icon, temperature)
"""

import displayio
import terminalio
import time
from adafruit_display_text import label
from text_renderer import BLACK

def format_time_hhmm(timestamp):
    """Format timestamp to HH:MM format for CircuitPython compatibility"""
    time_struct = time.localtime(timestamp)
    hour = time_struct[3]  # tm_hour
    minute = time_struct[4]  # tm_min
    return f"{hour:02d}:{minute:02d}"

def create_forecast_row(forecast_data, y_position=50):
    """Create hourly forecast row with stacked cells

    Args:
        forecast_data: List of forecast items, each with:
            - dt: Unix timestamp
            - temp: Temperature value
            - icon: Weather icon code (like "01n")
        y_position: Y position to place the forecast row
    """

    # Create display group for forecast row
    forecast_group = displayio.Group()

    # Cell dimensions
    cell_width = 50  # 400px / 8 cells = 50px each
    icon_size = 50  # Updated for 50x50 small icons
    row_height = 70  # Increased from 65 to 70 for more height

    # Calculate how many cells fit (8 cells at 50px each = 400px)
    max_cells = min(len(forecast_data), 8)
    total_row_width = max_cells * cell_width



    for i in range(max_cells):
        forecast_item = forecast_data[i]

        # Calculate cell x position within the bordered area
        cell_x = i * cell_width  # No offset, start from edge



        # Convert timestamp to time string
        dt = forecast_item['dt']
        time_str = format_time_hhmm(dt)

        # Create time label (moved down 10px from top)
        time_label = label.Label(terminalio.FONT, text=time_str, color=BLACK)
        # Better centering calculation
        text_width = len(time_str) * 6  # Approximate terminalio font width
        time_label.x = cell_x + (cell_width - text_width) // 2
        time_label.y = y_position + 4  # Moved down 1px more (was 3)
        forecast_group.append(time_label)

        # Icon will be positioned at cell_x + (cell_width - icon_size) // 2, y_position + 25
        # Note: Icons will be added by calling code since they require SD card access

        # Create temperature label (moved down 10px)
        temp_str = f"{forecast_item['temp']}°C"
        temp_label = label.Label(terminalio.FONT, text=temp_str, color=BLACK)
        # Better centering calculation
        temp_text_width = len(temp_str) * 6  # Approximate terminalio font width
        temp_label.x = cell_x + (cell_width - temp_text_width) // 2
        temp_label.y = y_position + 63  # Moved down 2px more (was 61)
        forecast_group.append(temp_label)

    return forecast_group, max_cells


def get_forecast_icon_positions(forecast_data, y_position=50):
    """Get icon positions for forecast cells

    Returns list of (x, y, icon_code) tuples for positioning icons
    """
    positions = []
    cell_width = 50
    icon_size = 32
    max_cells = min(len(forecast_data), 8)

    for i in range(max_cells):
        forecast_item = forecast_data[i]
        cell_x = i * cell_width

        icon_x = cell_x + (cell_width - icon_size) // 2 - 4  # Center in 50px cell, shift left 4px
        icon_y = y_position + 8  # Move down 1px more (was 7)
        icon_code = f"{forecast_item['icon']}-small"  # Use small version

        positions.append((icon_x, icon_y, icon_code))

    return positions


def get_forecast_row_height():
    """Get the total height needed for the forecast row"""
    return 70  # Row height (70px) no border padding
