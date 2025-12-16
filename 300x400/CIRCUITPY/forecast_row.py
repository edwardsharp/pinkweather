"""
Hourly forecast row with stacked cells (time, icon, temperature)
"""

import displayio
import terminalio
import config
from adafruit_display_text import label
from adafruit_bitmap_font import bitmap_font
from adafruit_display_shapes.rect import Rect
from adafruit_display_shapes.line import Line
from date_utils import format_timestamp_to_hhmm
from text_renderer import BLACK, WHITE

# Global configuration for icon loading
sd_available = False
load_bmp_icon_func = None

def set_icon_loader(sd_available_flag, icon_loader_func):
    """Configure icon loading functionality"""
    global sd_available, load_bmp_icon_func
    sd_available = sd_available_flag
    load_bmp_icon_func = icon_loader_func

# Initialize fonts
hyperl15_font = bitmap_font.load_font("hyperl15reg.pcf")
terminal_font = terminalio.FONT



def get_cell_display_text(forecast_item):
    """Get display text for a forecast cell - timestamps are already in local time"""
    if forecast_item.get('is_now', False):
        return "NOW"

    # All timestamps are already in local time, no conversion needed
    local_timestamp = forecast_item['dt']
    return format_timestamp_to_hhmm(local_timestamp)

def create_forecast_row(forecast_data, y_position=50):
    """Create hourly forecast row with stacked cells

    Args:
        forecast_data: List of forecast items with dt, temp, and icon fields
        y_position: Y position for the forecast row
    """
    forecast_group = displayio.Group()

    cell_width = 50
    row_height = 75
    max_cells = min(len(forecast_data), 8)

    for i in range(max_cells):
        forecast_item = forecast_data[i]
        cell_x = i * cell_width

        time_str = get_cell_display_text(forecast_item)

        # Cell background
        cell_bg = Rect(cell_x, y_position, cell_width, row_height, fill=WHITE, outline=None)
        forecast_group.append(cell_bg)

        # Cell borders
        bottom_border = Line(
            cell_x, y_position + row_height - 1,
            cell_x + cell_width, y_position + row_height - 1,
            color=BLACK
        )
        forecast_group.append(bottom_border)

        if i < max_cells - 1:
            right_border = Rect(
                cell_x + cell_width - 1, y_position,
                1, row_height,
                fill=BLACK, outline=None
            )
            forecast_group.append(right_border)

        # Weather icon
        if sd_available and load_bmp_icon_func:
            icon_x = cell_x + (cell_width - 32) // 2 - 9
            icon_y = y_position + 14

            if forecast_item.get('is_special', False):
                icon_code = f"{forecast_item['icon']}"
            else:
                icon_code = f"{forecast_item['icon']}"

            forecast_icon = load_bmp_icon_func(f"{icon_code}.bmp")
            if forecast_icon:
                forecast_icon.x = icon_x
                forecast_icon.y = icon_y
                forecast_group.append(forecast_icon)

        # Time label
        time_label = label.Label(terminal_font, text=time_str, color=BLACK)
        text_width = len(time_str) * 6
        time_label.x = cell_x + (cell_width - text_width) // 2
        time_label.y = y_position + 8
        forecast_group.append(time_label)

        # Temperature with background
        temp_str = f"{forecast_item['temp']}°C"
        temp_text_width = len(temp_str) * 6

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

        # Temperature label
        temp_label = label.Label(terminal_font, text=temp_str, color=BLACK)
        temp_label.x = cell_x + (cell_width - temp_text_width) // 2
        temp_label.y = y_position + 65
        forecast_group.append(temp_label)
    return forecast_group, max_cells

def get_forecast_row_height():
    """Get the total height needed for the forecast row"""
    return 75
