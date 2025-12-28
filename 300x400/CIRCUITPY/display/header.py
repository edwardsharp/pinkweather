"""
single-line weather header with date and moon phase text
"""

import displayio
from adafruit_bitmap_font import bitmap_font
from adafruit_display_shapes.rect import Rect
from adafruit_display_text import label
from utils import moon_phase
from utils.logger import log

from display.forecast_row import create_forecast_row, get_forecast_row_height
from display.text_renderer import BLACK, RED, WHITE
from display.weather_description import create_weather_description

# Load hyperl15reg.pcf font for header
hyperl15_font = bitmap_font.load_font("fonts/hyperl15reg.pcf")


def create_header(
    current_timestamp=None,
    y_position=10,
    icon_loader=None,
    day_name=None,
    day_num=None,
    month_name=None,
    air_quality=None,
    zodiac_sign=None,
    indoor_temp_humidity=None,
):
    """Create single-line header with date, air quality, and zodiac sign

    Args:
        current_timestamp: Unix timestamp from weather API (already in local time)
        y_position: Y position for the header line
        icon_loader: Function to load icons (same as forecast icons use)
        day_name: Pre-calculated day name (e.g. 'MON')
        day_num: Pre-calculated day number (e.g. 15)
        month_name: Pre-calculated month name (e.g. 'DEC')
        air_quality: Air quality data dict with 'aqi_text' field
        zodiac_sign: Three-letter zodiac sign abbreviation

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

    # Get moon phase info using current timestamp (already local)
    if current_timestamp:
        moon_info = moon_phase.get_moon_info(current_timestamp)
        if moon_info:
            moon_icon_name = moon_phase.phase_to_icon_name(moon_info["phase"])
        else:
            moon_phase_str = None
            moon_icon_name = None
    else:
        moon_phase_str = None
        moon_icon_name = None

    # Prepare air quality and zodiac text separately for justified layout
    # log(f"DEBUG: air_quality data: {air_quality}")
    air_quality_str = None
    air_quality_color = WHITE
    zodiac_str = None

    if air_quality and air_quality.get("aqi_text"):
        aqi_text = air_quality["aqi_text"].upper()
        aqi_value = air_quality.get("aqi", 1)
        air_quality_str = f"AQ: {aqi_text}"
        # Use red color for poor air quality (AQI > 2)
        air_quality_color = RED if aqi_value > 2 else WHITE
        log(
            f"DEBUG: Setting AQ text to: {air_quality_str}, AQI: {aqi_value}, color: {'red' if aqi_value > 2 else 'white'}"
        )
    else:
        log("DEBUG: No air quality data available for header")

    if zodiac_sign:
        zodiac_str = zodiac_sign.upper()
        log(f"DEBUG: Setting zodiac text to: {zodiac_str}")
    else:
        log("DEBUG: No zodiac sign available for header")

    # Black background rectangle behind header text, leaving space for moon icon
    header_bg = Rect(0, 0, 370, 25, fill=BLACK)
    header_group.append(header_bg)

    # manually set for test example in web preview:
    # indoor_temp_humidity = indoor_temp_humidity or "19° 24%"

    # Date label (left aligned)
    date_label = label.Label(hyperl15_font, text=date_str, color=WHITE)
    date_label.x = 90 if indoor_temp_humidity else 5
    date_label.y = y_position - 4
    header_group.append(date_label)

    # indoor temp & humidity
    if indoor_temp_humidity:
        indoor_label = label.Label(
            hyperl15_font, text=indoor_temp_humidity, color=WHITE
        )
        indoor_label.x = 5
        indoor_label.y = y_position - 4
        header_group.append(indoor_label)

    # Air quality label (centered)
    if air_quality_str:
        aq_label = label.Label(
            hyperl15_font, text=air_quality_str, color=air_quality_color
        )
        aq_label.x = 205
        aq_label.y = y_position - 4
        header_group.append(aq_label)

    # Zodiac sign label (right aligned, just before moon icon)
    if zodiac_str:
        zodiac_label = label.Label(hyperl15_font, text=zodiac_str, color=WHITE)
        zodiac_label.anchor_point = (1.0, 0.0)  # Right anchor
        zodiac_label.anchored_position = (
            370,
            y_position - 10,
        )
        header_group.append(zodiac_label)

    # Moon phase icon positioned at far right
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
    air_quality=None,
    zodiac_sign=None,
    indoor_temp_humidity=None,
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
        air_quality: Air quality data dict with 'aqi_text' field
        zodiac_sign: Three-letter zodiac sign abbreviation

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
        air_quality=air_quality,
        zodiac_sign=zodiac_sign,
        indoor_temp_humidity=indoor_temp_humidity,
    )
    main_group.append(header_group)

    # Add weather description first (background layer)
    forecast_height = 0
    if weather_desc:
        header_height = get_header_height()
        # Calculate forecast height even if we don't have forecast data yet
        if forecast_data and len(forecast_data) > 0:
            forecast_height = get_forecast_row_height()
        desc_y = header_height + forecast_height - 10  # Move up 10px to fit more lines
        available_height = 300 - desc_y
        desc_group = create_weather_description(weather_desc, desc_y, available_height)
        main_group.append(desc_group)

    # Add forecast row on top of description
    if forecast_data and len(forecast_data) > 0:
        header_height = get_header_height()
        forecast_y = header_height
        forecast_group, cell_count = create_forecast_row(
            forecast_data, forecast_y, icon_loader
        )
        main_group.append(forecast_group)

    return main_group
