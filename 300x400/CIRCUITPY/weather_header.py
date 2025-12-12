"""
Weather header layout with day/date, icons, temperatures, and sunrise/sunset times
"""

import displayio
from adafruit_display_text import label
from text_renderer import TextRenderer, BLACK

# Icon positions (shared between hardware and web renderer)
WEATHER_ICON_X = 85
WEATHER_ICON_Y = -5
MOON_ICON_X = 250
MOON_ICON_Y = -5


def create_weather_header(day_name="Thu", day_num=11, month_name="Dec",
                         high_temp=-4, low_temp=-10,
                         sunrise_time="7:31a", sunset_time="4:28p"):
    """Create weather header section with day/date, temperatures, and times"""

    # Create display group for header
    header_group = displayio.Group()

    # Create renderer for font access
    renderer = TextRenderer()

    # Header line height (1.5x font size for better spacing)
    header_line_height = int(renderer.char_height * 1.5)

    # Day name - centered in left section (0-80px)
    day_label = label.Label(renderer.header_font_regular, text=day_name, color=BLACK)
    day_label.x = 40 - (day_label.bounding_box[2] // 2) if day_label.bounding_box else 30
    day_label.y = 7
    header_group.append(day_label)

    # Date - centered in left section below day
    date_text = f"{day_num} {month_name}"
    date_label = label.Label(renderer.header_font_regular, text=date_text, color=BLACK)
    date_label.x = 40 - (date_label.bounding_box[2] // 2) if date_label.bounding_box else 20
    date_label.y = 10 + header_line_height
    header_group.append(date_label)

    # High temp - positioned after weather icon space with bold H
    high_text = f"<hb>H</hb><h>{high_temp}°C</h>"
    high_segments = renderer.parse_markup(high_text)
    x_pos = WEATHER_ICON_X + 64 + 5
    for text_content, style, color in high_segments:
        font = renderer.get_font_for_style(style)
        high_label = label.Label(font, text=text_content, color=color)
        high_label.x = x_pos
        high_label.y = 7
        header_group.append(high_label)
        if high_label.bounding_box:
            x_pos += high_label.bounding_box[2]

    # Low temp - positioned below high temp with bold L
    low_text = f"<hb>L</hb><h>{low_temp}°C</h>"
    low_segments = renderer.parse_markup(low_text)
    x_pos = WEATHER_ICON_X + 64 + 5
    for text_content, style, color in low_segments:
        font = renderer.get_font_for_style(style)
        low_label = label.Label(font, text=text_content, color=color)
        low_label.x = x_pos
        low_label.y = 10 + header_line_height
        header_group.append(low_label)
        if low_label.bounding_box:
            x_pos += low_label.bounding_box[2]

    # Sunrise time - positioned after moon icon
    sunrise_label = label.Label(renderer.header_font_regular, text=sunrise_time, color=BLACK)
    sunrise_label.x = MOON_ICON_X + 64 + 10  # After moon icon + width + margin
    sunrise_label.y = 7
    header_group.append(sunrise_label)

    # Sunset time - positioned below sunrise
    sunset_label = label.Label(renderer.header_font_regular, text=sunset_time, color=BLACK)
    sunset_label.x = MOON_ICON_X + 64 + 10
    sunset_label.y = 10 + header_line_height
    header_group.append(sunset_label)

    return header_group


def get_header_height():
    """Get the total height of the header section"""
    renderer = TextRenderer()
    header_line_height = int(renderer.char_height * 1.5)
    return 10 + header_line_height + 5  # Base y + line height + margin
