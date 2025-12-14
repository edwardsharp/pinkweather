"""
Main display coordinator that combines header, forecast, and description modules
"""

import displayio
from weather_header import create_weather_header, get_header_height, WEATHER_ICON_X, WEATHER_ICON_Y, MOON_ICON_X, MOON_ICON_Y
from forecast_row import create_forecast_row, get_forecast_row_height
from weather_description import create_weather_description
from text_renderer import get_text_capacity, WHITE

# Display constants
DISPLAY_WIDTH = 400
DISPLAY_HEIGHT = 300

# Export icon positions for hardware/web renderer use
__all__ = ['create_weather_layout', 'create_alt_weather_layout', 'create_text_display', 'get_text_capacity',
           'WEATHER_ICON_X', 'WEATHER_ICON_Y', 'MOON_ICON_X', 'MOON_ICON_Y']


def create_text_display(text_content):
    """Create a simple text display from marked-up string (for backwards compatibility)"""
    from text_renderer import TextRenderer
    renderer = TextRenderer()
    return renderer.render_text(text_content)


def create_weather_layout(day_name="Thu", day_num=11, month_name="Dec",
                         current_temp=-1, feels_like=-7, high_temp=-4, low_temp=-10,
                         sunrise_time="7:31a", sunset_time="4:28p",
                         weather_desc="Cloudy. 40 percent chance of flurries this evening. Periods of snow beginning near midnight. Amount 2 to 4 cm. Wind up to 15 km/h. Low minus 5. Wind chill near -9.",
                         weather_icon_name="01n.bmp", moon_icon_name="moon-waning-crescent-5.bmp",
                         forecast_data=None):
    """Create complete weather layout with header, forecast row, and description

    Args:
        day_name, day_num, month_name: Date information
        current_temp, feels_like: Current temperature info (currently unused in new layout)
        high_temp, low_temp: Daily high/low temperatures
        sunrise_time, sunset_time: Sun times
        weather_desc: Long weather description text
        weather_icon_name, moon_icon_name: Icon filenames
        forecast_data: List of forecast items with dt, temp, icon fields
    """

    # Create main display group
    main_group = displayio.Group()

    # Create white background
    background_bitmap = displayio.Bitmap(DISPLAY_WIDTH, DISPLAY_HEIGHT, 1)
    background_palette = displayio.Palette(1)
    background_palette[0] = WHITE
    background_sprite = displayio.TileGrid(background_bitmap, pixel_shader=background_palette)
    main_group.append(background_sprite)

    # Create header section
    header_group = create_weather_header(
        day_name=day_name,
        day_num=day_num,
        month_name=month_name,
        high_temp=high_temp,
        low_temp=low_temp,
        sunrise_time=sunrise_time,
        sunset_time=sunset_time
    )
    main_group.append(header_group)

    # Calculate positions for forecast and description
    header_height = get_header_height()
    forecast_y = header_height + 15  # Larger margin to shift forecast row down

    # Create forecast row if data provided
    forecast_height = 0
    if forecast_data and len(forecast_data) > 0:
        forecast_group, cell_count = create_forecast_row(forecast_data, forecast_y)
        main_group.append(forecast_group)
        forecast_height = get_forecast_row_height()

    # Create weather description
    description_y = forecast_y + forecast_height - 20  # Move up 10px more (was -10, now -20)
    available_height = DISPLAY_HEIGHT - description_y - 10  # Reserve bottom margin

    description_group = create_weather_description(
        weather_desc=weather_desc,
        y_position=description_y,
        available_height=available_height
    )
    main_group.append(description_group)

    # Note: Forecast icon positions need to be handled by calling code
    # since CircuitPython doesn't support setting custom attributes on displayio groups

    # Note: Icons will be added by calling code since they require SD card access
    # Weather icon at (WEATHER_ICON_X, WEATHER_ICON_Y)
    # Moon icon at (MOON_ICON_X, MOON_ICON_Y)
    # Forecast icons at positions in main_group._forecast_icon_positions

    return main_group

def create_alt_weather_layout(current_timestamp=None, timezone_offset_hours=None, forecast_data=None, weather_desc=None, icon_loader=None):
    """Create weather layout with alternative single-line header

    Args:
        current_timestamp: Unix timestamp from weather API for accurate date
        timezone_offset_hours: Timezone offset for local time
        forecast_data: List of forecast items for the forecast row
        weather_desc: Weather description text
        icon_loader: Function to load icons (same as forecast icons use)

    Returns:
        DisplayIO group containing the complete layout
    """
    from alt_weather_header import create_alt_weather_layout
    return create_alt_weather_layout(current_timestamp, timezone_offset_hours, forecast_data, weather_desc, icon_loader)

# get_forecast_icon_positions_from_layout function removed - icons are now handled directly in forecast_row.py
