"""
Debug renderer for displayio groups - converts to PIL Image for visualization
This is a simplified renderer focused on debugging the line graph issue
"""

from PIL import Image, ImageDraw, ImageFont
import displayio
from adafruit_display_text.label import Label
from adafruit_display_shapes.rect import Rect
from adafruit_display_shapes.line import Line


def render_displayio_group_to_image(group, width=122, height=250, debug=True):
    """
    Convert displayio.Group to PIL Image for debugging
    """
    # Create white background image
    image = Image.new('RGB', (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(image)

    if debug:
        print(f"Rendering group with {len(group)} items")

    # Render all items in the group
    render_group_recursive(draw, group, 0, 0, debug=debug)

    return image


def render_group_recursive(draw, group, offset_x, offset_y, depth=0, debug=True):
    """Recursively render displayio group items"""

    # Get group position
    group_x = getattr(group, 'x', 0) + offset_x
    group_y = getattr(group, 'y', 0) + offset_y

    if debug:
        indent = "  " * depth
        print(f"{indent}Group at ({group_x}, {group_y}) with {len(group)} items")

    # Skip if hidden
    if getattr(group, 'hidden', False):
        if debug:
            print(f"{indent}  HIDDEN - skipping")
        return

    # Render each item in the group
    for i, item in enumerate(group):
        if debug:
            print(f"{indent}  Item {i}: {type(item).__name__}")

        if isinstance(item, displayio.Group):
            render_group_recursive(draw, item, group_x, group_y, depth + 1, debug=debug)

        elif isinstance(item, Rect):
            render_rect(draw, item, group_x, group_y, debug=debug)

        elif isinstance(item, Line):
            render_line(draw, item, group_x, group_y, debug=debug)

        elif isinstance(item, Label):
            render_label(draw, item, group_x, group_y, debug=debug)

        elif hasattr(item, '__class__') and 'TileGrid' in str(type(item)):
            render_tilegrid(draw, item, group_x, group_y, debug=debug)

        else:
            if debug:
                print(f"{indent}    Unknown item type: {type(item)}")


def render_rect(draw, rect, offset_x, offset_y, debug=True):
    """Render displayio Rect to PIL"""
    x = rect.x + offset_x
    y = rect.y + offset_y
    width = rect.width
    height = rect.height

    # Handle fill - if fill attribute doesn't exist or is None, no fill
    fill_color = None
    if hasattr(rect, 'fill') and rect.fill is not None:
        fill_color = convert_displayio_color(rect.fill)

    # Handle outline - if outline attribute doesn't exist or is None, no outline
    outline_color = None
    if hasattr(rect, 'outline') and rect.outline is not None:
        outline_color = convert_displayio_color(rect.outline)

    if debug:
        print(f"      Rect: ({x}, {y}) {width}x{height}, fill={fill_color}, outline={outline_color}")

    # Draw filled rectangle (only if fill_color is specified and not None)
    if fill_color is not None:
        coords = [x, y, x + width - 1, y + height - 1]
        draw.rectangle(coords, fill=fill_color)

    # Draw outline (stroke) - only if outline color is specified and not None
    if outline_color is not None:
        coords = [x, y, x + width - 1, y + height - 1]
        # Default stroke width of 2 for graph borders
        stroke_width = 2
        for i in range(stroke_width):
            outline_coords = [coords[0] - i, coords[1] - i, coords[2] + i, coords[3] + i]
            draw.rectangle(outline_coords, outline=outline_color, fill=None)


def render_line(draw, line_obj, offset_x, offset_y, debug=True):
    """Render displayio Line to PIL by rendering its bitmap"""

    # Get line position and bitmap
    x = line_obj.x + offset_x
    y = line_obj.y + offset_y
    bitmap = line_obj.bitmap
    color = convert_displayio_color(line_obj.color)

    if debug:
        print(f"      Line: bitmap at ({x}, {y}), size=({bitmap.width}, {bitmap.height}), color={color}")

    if color is not None and bitmap:
        # Render each pixel of the line bitmap
        for by in range(bitmap.height):
            for bx in range(bitmap.width):
                try:
                    pixel = bitmap[bx, by]
                    if pixel > 0:  # Non-zero pixel means line is present
                        draw.point((x + bx, y + by), fill=color)
                except:
                    pass


def render_label(draw, label_obj, offset_x, offset_y, debug=True):
    """Render displayio Label to PIL"""

    text = getattr(label_obj, 'text', '') or ''
    if not text:
        return

    color = convert_displayio_color(label_obj.color)
    if color is None:
        return

    # Handle positioning
    x = label_obj.x + offset_x
    y = label_obj.y + offset_y

    # Handle anchored positioning
    if hasattr(label_obj, 'anchored_position') and label_obj.anchored_position:
        anchor_x, anchor_y = label_obj.anchored_position
        anchor_point = getattr(label_obj, 'anchor_point', (0, 0))

        # Estimate text size for anchor calculation
        if hasattr(label_obj.font, 'load_glyphs'):
            # terminalio.FONT
            text_width = len(text) * 6
            text_height = 8
        else:
            # bitmap font - rough estimate
            text_width = len(text) * 25
            text_height = 50

        # Apply anchor offset
        x = anchor_x - int(text_width * anchor_point[0]) + offset_x
        y = anchor_y - int(text_height * anchor_point[1]) + offset_y

    if debug:
        print(f"      Label: '{text}' at ({x}, {y}), color={color}")

    # Use default font for now - could be enhanced for bitmap fonts
    try:
        font = ImageFont.load_default()
        draw.text((x, y), text, font=font, fill=color)
    except:
        draw.text((x, y), text, fill=color)


def convert_displayio_color(color):
    """Convert displayio color (int) to PIL RGB tuple"""
    if color is None:
        return None

    if isinstance(color, int):
        # Convert 0xRRGGBB to (R, G, B)
        r = (color >> 16) & 0xFF
        g = (color >> 8) & 0xFF
        b = color & 0xFF
        return (r, g, b)

    return color


def save_debug_image(group, filename="debug_display.png", debug=True):
    """Render group to image and save it"""
    image = render_displayio_group_to_image(group, debug=debug)
    image.save(filename)
    if debug:
        print(f"Saved debug image: {filename}")
    return image


def render_tilegrid(draw, tilegrid, offset_x, offset_y, debug=True):
    """Render displayio TileGrid to PIL - this handles text rendering"""

    x = tilegrid.x + offset_x
    y = tilegrid.y + offset_y

    if debug:
        print(f"      TileGrid: at ({x}, {y}), bitmap={tilegrid.bitmap}, palette={tilegrid.pixel_shader}")

    # Skip if hidden
    if getattr(tilegrid, 'hidden', False):
        return

    bitmap = tilegrid.bitmap
    palette = tilegrid.pixel_shader

    if not bitmap or not palette:
        return

    # Render each pixel of the bitmap using the palette
    for by in range(bitmap.height):
        for bx in range(bitmap.width):
            try:
                palette_index = bitmap[bx, by]
                if palette_index > 0:  # 0 is usually transparent
                    # Get color from palette
                    try:
                        color_val = palette[palette_index]
                        color = convert_displayio_color(color_val)
                        if color:
                            draw.point((x + bx, y + by), fill=color)
                    except (IndexError, AttributeError):
                        # Fallback to black for any palette issues
                        draw.point((x + bx, y + by), fill=(0, 0, 0))
            except:
                pass


if __name__ == "__main__":
    print("Debug renderer ready")
