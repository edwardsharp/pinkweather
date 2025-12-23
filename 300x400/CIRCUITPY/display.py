"""
main display coordinator/wrapper that combines header, forecast, and description modules
"""

from header import create_weather_layout as create_header_layout
from text_renderer import TextRenderer, get_text_capacity

# Display constants
DISPLAY_WIDTH = 400
DISPLAY_HEIGHT = 300

# Export functions for hardware/web renderer use
__all__ = ["create_weather_layout", "create_text_display", "get_text_capacity"]


def create_text_display(text_content):
    """Create a simple text display from marked-up string (mostly for errors/debug)"""
    renderer = TextRenderer()
    return renderer.render_text(text_content)


def create_weather_layout(
    current_timestamp=None,
    forecast_data=None,
    weather_desc=None,
    icon_loader=None,
    day_name=None,
    day_num=None,
    month_name=None,
):
    """Create weather layout with single-line header

    Args:
        current_timestamp: Unix timestamp from weather API for accurate date (already in local time)
        forecast_data: List of forecast items for the forecast row
        weather_desc: Weather description text
        icon_loader: Function to load icons
        day_name: Pre-calculated day name (e.g. 'MON')
        day_num: Pre-calculated day number (e.g. 15)
        month_name: Pre-calculated month name (e.g. 'DEC')

    Returns:
        DisplayIO group containing the complete layout
    """
    return create_header_layout(
        current_timestamp,
        forecast_data,
        weather_desc,
        icon_loader,
        day_name,
        day_num,
        month_name,
    )
