"""
Main display coordinator that combines header, forecast, and description modules
"""

from text_renderer import get_text_capacity

# Display constants
DISPLAY_WIDTH = 400
DISPLAY_HEIGHT = 300

# Export functions for hardware/web renderer use
__all__ = ['create_weather_layout', 'create_text_display', 'get_text_capacity']


def create_text_display(text_content):
    """Create a simple text display from marked-up string (for backwards compatibility)"""
    from text_renderer import TextRenderer
    renderer = TextRenderer()
    return renderer.render_text(text_content)




def create_weather_layout(current_timestamp=None, timezone_offset_hours=None, forecast_data=None, weather_desc=None, icon_loader=None):
    """Create weather layout with single-line header

    Args:
        current_timestamp: Unix timestamp from weather API for accurate date
        timezone_offset_hours: Timezone offset for local time
        forecast_data: List of forecast items for the forecast row
        weather_desc: Weather description text
        icon_loader: Function to load icons

    Returns:
        DisplayIO group containing the complete layout
    """
    from header import create_weather_layout as create_header_layout
    return create_header_layout(current_timestamp, timezone_offset_hours, forecast_data, weather_desc, icon_loader)
