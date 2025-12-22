"""
Single-line weather header with date and moon phase text
"""

import displayio
import moon_phase
from adafruit_bitmap_font import bitmap_font
from adafruit_display_shapes.rect import Rect
from adafruit_display_text import label
from forecast_row import create_forecast_row, get_forecast_row_height
from text_renderer import BLACK, WHITE
from weather_description import create_weather_description

# Load hyperl15reg.pcf font for header
hyperl15_font = bitmap_font.load_font("hyperl15reg.pcf")


def create_header(
    current_timestamp=None,
    y_position=10,
    icon_loader=None,
    day_name=None,
    day_num=None,
    month_name=None,
):
    """Create single-line header with date and moon phase

    Args:
        current_timestamp: Unix timestamp from weather API (already in local time)
        y_position: Y position for the header line
        icon_loader: Function to load icons (same as forecast icons use)
        day_name: Pre-calculated day name (e.g. 'MON')
        day_num: Pre-calculated day number (e.g. 15)
        month_name: Pre-calculated month name (e.g. 'DEC')

    Returns:
        DisplayIO group containing the header
    """

    # Create display group for header
    header_group = displayio.Group()

    # Use pre-calculated date info (always required now)
    if day_name and day_num and month_name:
        date_str = f"{day_name} {day_num} {month_name}"
    else:
        date_str = "DATE ERROR"  # Should not happen if called correctly

    # Set local_timestamp for moon phase calculation
    # Get moon phase info using current timestamp (already local)
    if current_timestamp:
        moon_info = moon_phase.get_moon_info(current_timestamp)
        if moon_info:
            moon_phase_str = moon_info["name"].upper()
            moon_icon_name = moon_phase.phase_to_icon_name(moon_info["phase"])
        else:
            moon_phase_str = None
            moon_icon_name = None
    else:
        moon_phase_str = None
        moon_icon_name = None

    # Black background rectangle behind header text, leaving space for moon icon
    header_bg = Rect(0, 0, 370, 25, fill=BLACK)
    header_group.append(header_bg)

    # Date label (left aligned)
    date_label = label.Label(hyperl15_font, text=date_str, color=WHITE)
    date_label.x = 10
    date_label.y = y_position - 4
    header_group.append(date_label)

    # Moon phase label (right aligned with space for icon)
    moon_label = label.Label(hyperl15_font, text=moon_phase_str, color=WHITE)
    moon_label.anchor_point = (1.0, 0.0)
    moon_label.anchored_position = (360, y_position - 10)
    header_group.append(moon_label)

    # Moon phase icon positioned at far right
    # Add moon icon if available and moon phase calculation succeeded
    if icon_loader and moon_icon_name:
        moon_icon = icon_loader(f"{moon_icon_name}.bmp")
        if moon_icon:
            moon_icon.x = 375
            moon_icon.y = 0
            header_group.append(moon_icon)

    return header_group


def get_header_height():
    """Get the total height needed for the header"""
    return 25


def create_weather_layout(
    current_timestamp=None,
    forecast_data=None,
    weather_desc=None,
    icon_loader=None,
    day_name=None,
    day_num=None,
    month_name=None,
):
    """Create complete weather layout with single-line header, forecast, and description

    Args:
        current_timestamp: Unix timestamp from weather API (already in local time)
        forecast_data: List of forecast items for the forecast row
        weather_desc: Weather description text
        icon_loader: Function to load icons (same as forecast icons use)
        day_name: Pre-calculated day name (e.g. 'MON')
        day_num: Pre-calculated day number (e.g. 15)
        month_name: Pre-calculated month name (e.g. 'DEC')

    Returns:
        DisplayIO group containing complete weather layout
    """

    # Create main display group
    main_group = displayio.Group()

    # Create header
    header_group = create_header(
        current_timestamp,
        y_position=15,
        icon_loader=icon_loader,
        day_name=day_name,
        day_num=day_num,
        month_name=month_name,
    )
    main_group.append(header_group)

    # Add forecast row below header
    forecast_height = 0
    if forecast_data and len(forecast_data) > 0:
        header_height = get_header_height()
        forecast_y = header_height
        forecast_group, cell_count = create_forecast_row(forecast_data, forecast_y)
        main_group.append(forecast_group)
        forecast_height = get_forecast_row_height()

    # Add weather description below forecast
    if weather_desc:
        header_height = get_header_height()
        desc_y = header_height + 2 + forecast_height + 2
        available_height = 300 - desc_y
        desc_group = create_weather_description(weather_desc, desc_y, available_height)
        main_group.append(desc_group)

    return main_group
