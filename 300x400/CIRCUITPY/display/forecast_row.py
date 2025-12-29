"""
hourly forecast row with stacked cells (time, icon, temperature)
"""

import displayio
import terminalio
from adafruit_bitmap_font import bitmap_font
from adafruit_display_shapes.line import Line
from adafruit_display_shapes.rect import Rect
from adafruit_display_text import label
from weather.date_utils import format_timestamp_to_hhmm

from display.text_renderer import BLACK, RED, WHITE


def format_temp(temp):
    """Format temperature to avoid negative zero"""
    if temp is None:
        return "?"
    # Round to nearest integer
    rounded = round(temp)
    # If it rounds to zero, explicitly return "0"
    if rounded == 0:
        return "0"
    return f"{rounded:.0f}"


# Removed global icon loading state - now passed as parameter


# Initialize fonts
hyperl15_font = bitmap_font.load_font("fonts/hyperl15reg.pcf")
terminal_font = terminalio.FONT


def get_cell_display_text(forecast_item):
    """Get display text for a forecast cell - timestamps are already in local time"""
    if forecast_item.get("is_now", False):
        return "NOW"

    # Check for special cell types
    if forecast_item.get("is_special", False):
        special_type = forecast_item.get("special_type")
        if special_type == "night":
            return "NIGHT"

    # All timestamps are already in local time, no conversion needed
    local_timestamp = forecast_item["dt"]
    return format_timestamp_to_hhmm(local_timestamp)


def create_forecast_row(forecast_data, y_position=50, icon_loader=None):
    """Create hourly forecast row with stacked cells

    Args:
        forecast_data: List of forecast items with dt, temp, and icon fields
        y_position: Y position for the forecast row
        icon_loader: Optional function to load icon bitmaps
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
        cell_bg = Rect(
            cell_x, y_position, cell_width, row_height, fill=WHITE, outline=None
        )
        forecast_group.append(cell_bg)

        # Cell borders
        # bottom_border = Line(
        #     cell_x,
        #     y_position + row_height - 1,
        #     cell_x + cell_width,
        #     y_position + row_height - 1,
        #     color=BLACK,
        # )
        # forecast_group.append(bottom_border)

        # if i < max_cells - 1:
        #     right_border = Rect(
        #         cell_x + cell_width - 1,
        #         y_position,
        #         3,
        #         row_height,
        #         fill=BLACK,
        #         outline=None,
        #     )
        #     forecast_group.append(right_border)

        # Weather icon
        if icon_loader:
            icon_x = cell_x + (cell_width - 32) // 2 - 9
            icon_y = y_position + 14

            if forecast_item.get("is_special", False):
                icon_code = f"{forecast_item['icon']}"
            else:
                icon_code = f"{forecast_item['icon']}"

            forecast_icon = icon_loader(f"{icon_code}.bmp")
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

        # Temperature with precipitation chance if non-zero
        temp_str = f"{format_temp(forecast_item['temp'])}°"

        # Add precipitation chance if it exists and is non-zero
        pop = forecast_item.get("pop", 0)

        if pop > 0:
            pop_percent = int(pop * 100)  # Convert to percentage
            # Render pop % in bottom right corner of icon with black background and red text
            pop_text = f"{pop_percent}%"

            # Create black background for pop text
            pop_text_width = len(pop_text) * 6
            pop_bg_bitmap = displayio.Bitmap(pop_text_width + 3, 15, 1)
            pop_bg_palette = displayio.Palette(1)
            pop_bg_palette[0] = WHITE

            # Position at bottom right of icon (icon is 32x32, starts at icon_x, icon_y)
            icon_x = cell_x + (cell_width - 32) // 2 - 9
            icon_y = y_position + 14
            pop_bg_x = icon_x + (
                24 if pop_percent == 100 else 28
            )  # 28px from left edge of icon (a bit more right)
            pop_bg_y = icon_y + 34  # 34px from top edge of icon (a bit more down)

            pop_bg_grid = displayio.TileGrid(
                pop_bg_bitmap,
                pixel_shader=pop_bg_palette,
                x=pop_bg_x,
                y=pop_bg_y,
            )
            forecast_group.append(pop_bg_grid)

            # Red text on black background
            pop_label = label.Label(terminal_font, text=pop_text, color=RED)
            pop_label.x = pop_bg_x + 1  # 1px padding from background edge
            pop_label.y = pop_bg_y + 8  # Vertically centered in background
            forecast_group.append(pop_label)

        # TEST temp_str with max chars
        # note: hardware doesn't seem to render ° symbol?
        # temp_str = "30°99%"
        temp_text_width = len(temp_str) * 6

        # temp_bg_bitmap = displayio.Bitmap(temp_text_width + 4, 12, 1)
        # temp_bg_palette = displayio.Palette(1)
        # temp_bg_palette[0] = WHITE
        # temp_bg_grid = displayio.TileGrid(
        #     temp_bg_bitmap,
        #     pixel_shader=temp_bg_palette,
        #     x=cell_x + (cell_width - temp_text_width) // 2 - 2,
        #     y=y_position + 53,
        # )
        # forecast_group.append(temp_bg_grid)

        # Temperature label
        temp_label = label.Label(hyperl15_font, text=temp_str, color=BLACK)
        temp_label.x = (
            cell_x + (cell_width - temp_text_width) // 2
        )  # - 7  # -7 to nudge a bit left
        temp_label.y = y_position + 72
        forecast_group.append(temp_label)
    return forecast_group, max_cells


def get_forecast_row_height():
    """Get the total height needed for the forecast row"""
    return 75
