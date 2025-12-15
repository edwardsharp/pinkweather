"""
Single-line weather header with date and moon phase text
"""

import displayio
import time
from adafruit_display_text import label
from adafruit_display_shapes.rect import Rect
from adafruit_bitmap_font import bitmap_font
from text_renderer import WHITE, BLACK
import moon_phase
from forecast_row import create_forecast_row, get_forecast_row_height
from weather_description import create_weather_description

# Load hyperl15reg.pcf font for header
hyperl15_font = bitmap_font.load_font("hyperl15reg.pcf")

def create_header(current_timestamp=None, timezone_offset_hours=None, y_position=10, icon_loader=None):
    """Create single-line header with date and moon phase

    Args:
        current_timestamp: Unix timestamp from weather API (for accurate date)
        timezone_offset_hours: Timezone offset for local time
        y_position: Y position for the header line
        icon_loader: Function to load icons (same as forecast icons use)

    Returns:
        DisplayIO group containing the header elements
    """

    if timezone_offset_hours is None:
        timezone_offset_hours = -5  # Default EST offset

    # Create display group for header
    header_group = displayio.Group()

    # Get current date from timestamp
    if current_timestamp:
        local_timestamp = current_timestamp + (timezone_offset_hours * 3600)
        try:
            current_time = time.gmtime(local_timestamp)
        except AttributeError:
            current_time = time.localtime(local_timestamp)
    else:
        current_time = time.localtime()
        local_timestamp = time.time()  # Use current time as fallback

    # Format date string
    day_names = ['SUN', 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT']
    month_names = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN',
                   'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']

    day_name = day_names[current_time[6]]  # tm_wday
    day_num = current_time[2]  # tm_mday
    month_name = month_names[current_time[1] - 1]  # tm_mon

    date_str = f"{day_name} {day_num} {month_name}"

    # Get moon phase info using same local timestamp as date calculation
    moon_info = moon_phase.get_moon_info(local_timestamp)
    moon_phase_str = moon_info['name'].upper()
    moon_icon_name = moon_phase.phase_to_icon_name(moon_info['phase'])

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
    if icon_loader:
        moon_icon = icon_loader(f"{moon_icon_name}.bmp")
        if moon_icon:
            moon_icon.x = 375
            moon_icon.y = 0
            header_group.append(moon_icon)

    return header_group

def get_header_height():
    """Get the total height needed for the header"""
    return 25

def create_weather_layout(current_timestamp=None, timezone_offset_hours=None, forecast_data=None, weather_desc=None, icon_loader=None):
    """Create complete weather layout with single-line header, forecast, and description

    Args:
        current_timestamp: Unix timestamp from weather API
        timezone_offset_hours: Timezone offset
        forecast_data: List of forecast items for the forecast row
        weather_desc: Weather description text
        icon_loader: Function to load icons (same as forecast icons use)

    Returns:
        DisplayIO group containing the complete layout
    """

    # Create main display group
    main_group = displayio.Group()

    # Create header
    header_group = create_header(current_timestamp, timezone_offset_hours, y_position=15, icon_loader=icon_loader)
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
