"""
weather description text rendering for long text content
"""

from display.text_renderer import TextRenderer


def create_weather_description(weather_desc, y_position=100, available_height=200):
    """Create weather description text display

    Args:
        weather_desc: Long weather description text
        y_position: Y position to start the description
        available_height: Available height for text rendering
    """

    # Create text renderer with available dimensions
    desc_renderer = TextRenderer(width=400, height=available_height)

    # Render the description text with regular method
    desc_group = desc_renderer.render_text(weather_desc)

    # Position the text group
    desc_group.y = y_position

    return desc_group


def get_text_capacity_for_description(available_height=180):
    """Get text capacity for description area"""
    renderer = TextRenderer(width=400, height=available_height)
    return {
        "chars_per_line": renderer.chars_per_line,
        "lines_available": available_height // renderer.line_height,
        "total_capacity": renderer.chars_per_line
        * (available_height // renderer.line_height),
        "line_height": renderer.line_height,
    }
