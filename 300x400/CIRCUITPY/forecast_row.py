"""
Hourly forecast row with stacked cells (time, icon, temperature)
"""

import displayio
import time
from adafruit_display_text import label
from text_renderer import BLACK, WHITE

# Import display shapes for borders
from adafruit_display_shapes.rect import Rect

# Import terminalio with fallback
try:
    import terminalio
except ImportError:
    # Fallback for web environment - will use bitmap font instead
    terminalio = None

# Load fonts with proper fallbacks
hyperl15_font = None
terminal_font = None

try:
    from adafruit_bitmap_font import bitmap_font
    hyperl15_font = bitmap_font.load_font("/hyperl15reg.pcf")
except (ImportError, OSError):
    try:
        # Try relative path for web environment
        hyperl15_font = bitmap_font.load_font("hyperl15reg.pcf")
    except (ImportError, OSError):
        print("Warning: hyperl15reg.pcf not found")

# Set up terminal font
if terminalio is not None:
    terminal_font = terminalio.FONT
else:
    # Use hyperlegible as fallback if terminalio not available
    terminal_font = hyperl15_font
    print("Warning: terminalio not available, using hyperlegible font for forecast cells")

def format_time_hhmm(timestamp, timezone_offset_hours=None):
    """Format timestamp to HH:MM format with timezone offset"""
    if timezone_offset_hours is None:
        timezone_offset_hours = -5  # Default EST offset

    local_timestamp = timestamp + (timezone_offset_hours * 3600)

    # Convert timestamp to time components manually without gmtime
    hours_since_epoch = local_timestamp // 3600
    hour = hours_since_epoch % 24
    minute = (local_timestamp % 3600) // 60
    return f"{hour:02d}:{minute:02d}"

def get_cell_display_text(forecast_item, timezone_offset_hours=None):
    """Get display text for a forecast cell (time or special label)"""
    # Check if this is the "NOW" cell
    if forecast_item.get('is_now', False):
        return "NOW"

    # Check if this is a special event (sunrise/sunset)
    if forecast_item.get('is_special', False):
        # For sunrise/sunset, don't apply additional timezone conversion since already local
        hours_since_epoch = forecast_item['dt'] // 3600
        hour = hours_since_epoch % 24
        minute = (forecast_item['dt'] % 3600) // 60
        return f"{hour:02d}:{minute:02d}"

    # Regular time display
    return format_time_hhmm(forecast_item['dt'], timezone_offset_hours)

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
    row_height = 75  # Increased 5px more to prevent temperature text cutoff

    # Calculate how many cells fit (8 cells at 50px each = 400px)
    max_cells = min(len(forecast_data), 8)
    total_row_width = max_cells * cell_width



    for i in range(max_cells):
        forecast_item = forecast_data[i]

        # Calculate cell x position within the bordered area
        cell_x = i * cell_width  # No offset, start from edge



        # Get timezone offset from config or use default
        try:
            import config
            timezone_offset = config.TIMEZONE_OFFSET_HOURS
        except (ImportError, AttributeError):
            timezone_offset = -5  # Default EST offset

        # Get display text (time, "NOW", or special event)
        time_str = get_cell_display_text(forecast_item, timezone_offset)

        # Create cell border using adafruit_display_shapes
        cell_border = Rect(
            cell_x, y_position,
            cell_width - 1, row_height,
            fill=WHITE,
            outline=BLACK,
            stroke=1
        )
        forecast_group.append(cell_border)

        # Create time label using terminal font - move up for better spacing
        time_label = label.Label(terminal_font, text=time_str, color=BLACK)
        # Better centering calculation for terminal font
        text_width = len(time_str) * 6  # Approximate terminal font width
        time_label.x = cell_x + (cell_width - text_width) // 2
        time_label.y = y_position + 8  # Moved down 3px
        forecast_group.append(time_label)

        # Icon will be positioned at cell_x + (cell_width - icon_size) // 2, y_position + 20
        # Note: Icons will be added by calling code since they require SD card access

        # Create white background behind temperature text to prevent icon cutoff
        temp_str = f"{forecast_item['temp']}°C"
        temp_text_width = len(temp_str) * 6  # Approximate terminal font width

        # Create white background using bitmap to avoid border issues
        temp_bg_bitmap = displayio.Bitmap(temp_text_width + 4, 12, 1)
        temp_bg_palette = displayio.Palette(1)
        temp_bg_palette[0] = WHITE
        temp_bg_grid = displayio.TileGrid(
            temp_bg_bitmap,
            pixel_shader=temp_bg_palette,
            x=cell_x + (cell_width - temp_text_width) // 2 - 2,
            y=y_position + 53
        )
        forecast_group.append(temp_bg_grid)

        # Create temperature label using terminal font - move down to avoid overlap with icons
        temp_label = label.Label(terminal_font, text=temp_str, color=BLACK)
        # Better centering calculation for terminal font
        temp_label.x = cell_x + (cell_width - temp_text_width) // 2
        temp_label.y = y_position + 65  # Moved down 3px more
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

        icon_x = cell_x + (cell_width - icon_size) // 2 - 9  # Center in 50px cell, shift left 9px (5px more)
        icon_y = y_position + 14  # Moved down 3px

        # Handle special icons (sunrise/sunset don't need -small suffix)
        if forecast_item.get('is_special', False):
            icon_code = f"{forecast_item['icon']}-small"  # sunrise-small or sunset-small
        else:
            icon_code = f"{forecast_item['icon']}-small"  # Regular weather icons with -small

        positions.append((icon_x, icon_y, icon_code))

    return positions


def get_forecast_row_height():
    """Get the total height needed for the forecast row"""
    return 75  # Row height (75px) to prevent temperature text cutoff
