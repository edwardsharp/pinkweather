"""
Alternative single-line weather header with date and moon phase text
"""

import displayio
import time
from adafruit_display_text import label
from text_renderer import BLACK
import moon_phase

# Use terminalio as primary font for hardware compatibility
import terminalio
hyperl15_font = terminalio.FONT
print("Using terminalio.FONT for alt header")

def create_alt_header(current_timestamp=None, timezone_offset_hours=None, y_position=10):
    """Create alternative single-line header with date and moon phase

    Args:
        current_timestamp: Unix timestamp from weather API (for accurate date)
        timezone_offset_hours: Timezone offset for local time
        y_position: Y position for the header line

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

    # Format date string
    day_names = ['SUN', 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT']
    month_names = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN',
                   'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']

    day_name = day_names[current_time[6]]  # tm_wday
    day_num = current_time[2]  # tm_mday
    month_name = month_names[current_time[1] - 1]  # tm_mon

    date_str = f"{day_name}, {day_num} {month_name}"

    # Get moon phase info
    print(f"Calculating moon phase for timestamp: {current_timestamp}")
    moon_info = moon_phase.get_moon_info(current_timestamp)
    moon_phase_str = moon_info['name'].upper()
    print(f"Moon phase calculated: {moon_phase_str}")

    # Add smaller black background rectangle behind header text
    from adafruit_display_shapes.rect import Rect
    from text_renderer import WHITE, BLACK

    header_bg = Rect(0, 0, 400, 25, fill=BLACK)  # Full width, from top, taller height
    header_group.append(header_bg)

    # Create date label (left aligned)
    print(f"Creating date label: '{date_str}' at position ({10}, {y_position})")
    date_label = label.Label(hyperl15_font, text=date_str, color=WHITE)
    date_label.x = 10  # Left margin
    date_label.y = y_position - 4  # Move up 4px to align with moon phase
    header_group.append(date_label)
    print(f"Date label created with font: {hyperl15_font}")

    # Create moon phase label (right aligned using proper anchor point)
    print(f"Creating moon phase label: '{moon_phase_str}' at anchored position (390, {y_position - 8})")
    moon_label = label.Label(hyperl15_font, text=moon_phase_str, color=WHITE)
    # Use anchor point for true right alignment that works with any text length
    moon_label.anchor_point = (1.0, 0.0)  # Right anchor, top baseline
    moon_label.anchored_position = (390, y_position - 8)  # 10px from right edge, fine-tuned alignment with date
    header_group.append(moon_label)
    print(f"Moon phase label created")

    return header_group

def get_alt_header_height():
    """Get the total height needed for the alternative header"""
    return 25  # Single line with some padding

def create_alt_weather_layout(current_timestamp=None, timezone_offset_hours=None, forecast_data=None, weather_desc=None):
    """Create complete alternative weather layout with single-line header, forecast, and description

    Args:
        current_timestamp: Unix timestamp from weather API
        timezone_offset_hours: Timezone offset
        forecast_data: List of forecast items for the forecast row
        weather_desc: Weather description text

    Returns:
        DisplayIO group containing the complete layout
    """

    # Create main display group
    main_group = displayio.Group()

    # Create alternative header
    header_group = create_alt_header(current_timestamp, timezone_offset_hours, y_position=15)
    main_group.append(header_group)

    # Add forecast row below header
    forecast_height = 0
    if forecast_data and len(forecast_data) > 0:
        from forecast_row import create_forecast_row, get_forecast_row_height

        header_height = get_alt_header_height()
        forecast_y = header_height + 2  # Move forecast cells up 3px closer to header

        forecast_group, cell_count = create_forecast_row(forecast_data, forecast_y)
        main_group.append(forecast_group)
        forecast_height = get_forecast_row_height()

    # Add weather description below forecast
    if weather_desc:
        from weather_description import create_weather_description

        header_height = get_alt_header_height()
        desc_y = header_height + 2 + forecast_height + 2  # Header + spacing + forecast + minimal spacing

        # Calculate available height for description (from desc_y to bottom of display)
        available_height = 300 - desc_y  # Use full remaining height
        desc_group = create_weather_description(weather_desc, desc_y, available_height)
        main_group.append(desc_group)

    return main_group
