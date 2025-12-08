"""
Web renderer for PinkWeather - uses shared display module from CIRCUITPY
This imports the same display functions used by hardware for identical rendering
"""

import sys
import os
from PIL import Image, ImageDraw

# Add CIRCUITPY to path so we can import the shared display module
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'CIRCUITPY'))

from display import create_complete_display, format_time_short
import displayio
from adafruit_display_text.label import Label
from adafruit_display_shapes.rect import Rect
from adafruit_display_shapes.line import Line

def get_historical_averages_web(csv_data=None):
    """Web version of historical averages calculation"""
    if not csv_data:
        return {
            'temp': {'day': 22, 'week': 21, 'month': 20, 'year': 19},
            'humidity': {'day': 45, 'week': 46, 'month': 47, 'year': 48}
        }

    # Simple dummy calculation for web - could be enhanced
    return {
        'temp': {'day': 22, 'week': 21, 'month': 20, 'year': 19},
        'humidity': {'day': 45, 'week': 46, 'month': 47, 'year': 48}
    }

def get_graph_data_web(csv_data=None):
    """Web version of graph data"""
    if not csv_data:
        return [22] * 60, [45] * 60

    # Simple dummy data for web - could be enhanced
    return [22] * 60, [45] * 60

def render_web_display(temp_c, humidity, csv_data=None, system_status=None):
    """
    Render display for web using shared display module
    Returns PIL Image
    """

    # Get data in same format as hardware
    averages = get_historical_averages_web(csv_data)
    temp_data, humidity_data = get_graph_data_web(csv_data)

    # Get status info
    if system_status:
        sd_status = "SD" if system_status.get('sd_available', False) else "NOD"
        sd_time = system_status.get('sd_total_time', '0s')
        uptime = system_status.get('uptime', '0s')
        power_status = system_status.get('power_status', 'P')
        battery_status = system_status.get('battery_status', 'B--')
    else:
        sd_status = "SD"
        sd_time = "2d"
        uptime = "1h"
        power_status = "P"
        battery_status = "B--"

    # Change to CIRCUITPY directory to load fonts
    current_dir = os.getcwd()
    try:
        circuitpy_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'CIRCUITPY')
        os.chdir(circuitpy_dir)

        # Create display using EXACT same function as hardware
        display_group = create_complete_display(
            temp_c, humidity, averages, temp_data, humidity_data,
            sd_status, sd_time, uptime, power_status, battery_status
        )

    finally:
        os.chdir(current_dir)

    # Convert displayio group to PIL Image
    return displayio_group_to_pil_image(display_group)

def displayio_group_to_pil_image(group, width=122, height=250):
    """Convert displayio.Group to PIL Image"""
    image = Image.new('RGB', (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(image)

    render_group_recursive(draw, group, 0, 0)

    return image

def render_group_recursive(draw, group, offset_x, offset_y):
    """Recursively render displayio group to PIL"""

    group_x = getattr(group, 'x', 0) + offset_x
    group_y = getattr(group, 'y', 0) + offset_y

    if getattr(group, 'hidden', False):
        return

    for item in group:
        if isinstance(item, displayio.Group):
            render_group_recursive(draw, item, group_x, group_y)

        elif isinstance(item, Rect):
            render_rect(draw, item, group_x, group_y)

        elif isinstance(item, Line):
            render_line(draw, item, group_x, group_y)

        elif isinstance(item, Label):
            render_label(draw, item, group_x, group_y)

def render_rect(draw, rect, offset_x, offset_y):
    """Render displayio Rect to PIL"""
    x = rect.x + offset_x
    y = rect.y + offset_y
    width = rect.width
    height = rect.height

    fill_color = convert_color(rect.fill)
    outline_color = convert_color(rect.outline)

    coords = [x, y, x + width, y + height]

    if fill_color:
        draw.rectangle(coords, fill=fill_color)

    if outline_color and hasattr(rect, 'stroke') and rect.stroke > 0:
        draw.rectangle(coords, outline=outline_color, width=rect.stroke)

def render_line(draw, line_obj, offset_x, offset_y):
    """Render displayio Line to PIL"""
    x = line_obj.x + offset_x
    y = line_obj.y + offset_y

    # Line object has internal bitmap - render it
    if hasattr(line_obj, 'bitmap') and line_obj.bitmap:
        color = convert_color(line_obj.color)
        if color:
            render_bitmap(draw, line_obj.bitmap, x, y, color)

def render_label(draw, label_obj, offset_x, offset_y):
    """Render displayio Label to PIL"""

    x = label_obj.x + offset_x
    y = label_obj.y + offset_y

    # Handle anchored positioning
    if hasattr(label_obj, 'anchored_position') and label_obj.anchored_position:
        anchor_x, anchor_y = label_obj.anchored_position
        anchor_point = getattr(label_obj, 'anchor_point', (0, 0))

        text = label_obj.text or ""

        # Estimate text dimensions for anchor
        if hasattr(label_obj.font, 'load_glyphs'):
            # terminalio.FONT
            text_width = len(text) * 6
            text_height = 8
        else:
            # bitmap font
            text_width = len(text) * 30  # rough estimate
            text_height = 60

        anchor_offset_x = text_width * anchor_point[0]
        anchor_offset_y = text_height * anchor_point[1]

        x = anchor_x - anchor_offset_x
        y = anchor_y - anchor_offset_y

    text = label_obj.text or ""
    color = convert_color(label_obj.color)

    if text and color:
        if hasattr(label_obj.font, 'load_glyphs'):
            # terminalio.FONT - use PIL default
            try:
                from PIL import ImageFont
                pil_font = ImageFont.load_default()
                draw.text((x, y), text, font=pil_font, fill=color)
            except:
                draw.text((x, y), text, fill=color)
        else:
            # bitmap font - render glyph by glyph
            render_bitmap_font_text(draw, text, label_obj.font, x, y, color)

def render_bitmap_font_text(draw, text, font, x, y, color):
    """Render bitmap font text glyph by glyph"""
    current_x = x

    for char in text:
        try:
            glyph = font.get_glyph(ord(char))

            # Convert glyph bitmap
            glyph_img = Image.new('1', (glyph.bitmap.width, glyph.bitmap.height), 0)
            for gy in range(glyph.bitmap.height):
                for gx in range(glyph.bitmap.width):
                    pixel = glyph.bitmap[gx, gy]
                    glyph_img.putpixel((gx, gy), pixel)

            # Position and draw glyph
            glyph_x = current_x + glyph.dx
            glyph_y = y + glyph.dy

            draw_colored_glyph(draw, glyph_img, glyph_x, glyph_y, color)

            current_x += glyph.shift_x

        except:
            current_x += 10

def draw_colored_glyph(draw, glyph_image, x, y, color):
    """Draw glyph with specified color"""
    glyph_colored = Image.new('RGBA', glyph_image.size, (0, 0, 0, 0))

    for gy in range(glyph_image.height):
        for gx in range(glyph_image.width):
            if glyph_image.getpixel((gx, gy)) == 1:
                glyph_colored.putpixel((gx, gy), color + (255,))

    draw._image.paste(glyph_colored, (x, y), glyph_colored)

def render_bitmap(draw, bitmap, x, y, color):
    """Render displayio bitmap to PIL"""
    for by in range(bitmap.height):
        for bx in range(bitmap.width):
            try:
                pixel = bitmap[bx, by]
                if pixel > 0:
                    draw.point((x + bx, y + by), fill=color)
            except:
                pass

def convert_color(displayio_color):
    """Convert displayio color to PIL RGB tuple"""
    if displayio_color is None:
        return None

    if isinstance(displayio_color, int):
        r = (displayio_color >> 16) & 0xFF
        g = (displayio_color >> 8) & 0xFF
        b = displayio_color & 0xFF
        return (r, g, b)

    return displayio_color
