"""
Minimal web renderer using the exact shared display code from CIRCUITPY
"""

import importlib.util
import os
import sys

import displayio
from PIL import Image, ImageDraw, ImageFont

# Add CIRCUITPY to path so we can use the shared display module
circuitpy_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "CIRCUITPY")

# Add 300x400/CIRCUITPY to path for the new display
circuitpy_400x300_path = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "300x400", "CIRCUITPY"
)
sys.path.insert(0, circuitpy_400x300_path)

# Import shared moon phase functions from 300x400/CIRCUITPY
from moon_phase import calculate_moon_phase, phase_to_icon_name


def render_250x122_display(temp_c, humidity, csv_data=None, system_status=None):
    """
    Render 250x122 weather display for web using exact same shared display module as hardware
    Returns PIL Image
    """
    current_dir = os.getcwd()

    try:
        # Change to CIRCUITPY directory for font loading
        os.chdir(circuitpy_path)

        # Load weather display module from specific path
        weather_display_path = os.path.join(circuitpy_path, "display.py")
        spec = importlib.util.spec_from_file_location(
            "weather_display", weather_display_path
        )
        weather_display = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(weather_display)

        create_complete_display = weather_display.create_complete_display
        format_time_short = weather_display.format_time_short

        # Process CSV data for averages and graphs
        averages = (
            get_averages_from_csv(csv_data) if csv_data else get_default_averages()
        )
        temp_data, humidity_data = (
            get_graph_data_from_csv(csv_data) if csv_data else get_default_graph_data()
        )

        # Process system status
        if system_status:
            sd_status = "SD" if system_status.get("sd_available", False) else "NOD"
            sd_time = system_status.get("sd_total_time", "0s")
            uptime = system_status.get("uptime", "0s")
            power_status = system_status.get("power_status", "P")
            battery_status = system_status.get("battery_status", "B--")
        else:
            sd_status = "SD"
            sd_time = "2d"
            uptime = "1h"
            power_status = "P"
            battery_status = "B85"

        # Create display using EXACT same function as hardware
        display_group = create_complete_display(
            temp_c,
            humidity,
            averages,
            temp_data,
            humidity_data,
            sd_status,
            sd_time,
            uptime,
            power_status,
            battery_status,
        )

    finally:
        os.chdir(current_dir)

    # Convert displayio group to PIL Image
    return displayio_group_to_pil_image(display_group)


def render_400x300_display(text_content):
    """
    Render 400x300 display for web using provided text content
    Returns PIL Image
    """
    current_dir = os.getcwd()

    try:
        # Add CIRCUITPY directory to Python path for imports
        import sys

        if circuitpy_400x300_path not in sys.path:
            sys.path.insert(0, circuitpy_400x300_path)

        # Change to 400x300 CIRCUITPY directory for font loading
        os.chdir(circuitpy_400x300_path)

        # Load text renderer for simple text display
        text_renderer_path = os.path.join(circuitpy_400x300_path, "text_renderer.py")
        spec = importlib.util.spec_from_file_location(
            "text_renderer", text_renderer_path
        )
        text_renderer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(text_renderer)

        # Create simple text display with the provided content
        renderer = text_renderer.TextRenderer()
        main_group = renderer.render_text(text_content)

    finally:
        # Clean up: remove from path and restore directory
        if circuitpy_400x300_path in sys.path:
            sys.path.remove(circuitpy_400x300_path)
        os.chdir(current_dir)

    # Convert displayio group to PIL Image
    return displayio_group_to_pil_image(main_group, width=400, height=300)


def render_400x300_weather_layout(
    current_weather=None,
    forecast_data=None,
    weather_desc=None,
    current_timestamp=None,
    day_name=None,
    day_num=None,
    month_name=None,
    air_quality=None,
    zodiac_sign=None,
):
    """
    Render full 400x300 weather layout with header, forecast, and description
    Returns PIL Image
    """
    current_dir = os.getcwd()

    try:
        # Add CIRCUITPY directory to Python path for imports
        import sys

        if circuitpy_400x300_path not in sys.path:
            sys.path.insert(0, circuitpy_400x300_path)

        # Change to 400x300 CIRCUITPY directory for font loading
        os.chdir(circuitpy_400x300_path)

        # Load display module
        display_path = os.path.join(circuitpy_400x300_path, "display.py")
        spec = importlib.util.spec_from_file_location("display", display_path)
        display_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(display_module)

        # Create icon loader wrapper function that matches expected interface
        def icon_loader_wrapper(filename):
            # The caller will set x,y position after this returns
            return load_web_bmp_icon(filename, 0, 0)

        # Configure forecast row icon loader (required for forecast icons to show)
        try:
            from forecast_row import set_icon_loader

            set_icon_loader(True, icon_loader_wrapper)  # Icons available via web loader
        except ImportError:
            pass  # Forecast row module not available

        # Create weather layout with date info from weather data
        main_group = display_module.create_weather_layout(
            current_timestamp=current_timestamp,
            forecast_data=forecast_data,
            weather_desc=weather_desc,
            icon_loader=icon_loader_wrapper,  # Use wrapped icon loader
            day_name=day_name,
            day_num=day_num,
            month_name=month_name,
            air_quality=air_quality,
            zodiac_sign=zodiac_sign,
        )

        # Add font metrics debugging while in the correct directory
        try:
            from adafruit_bitmap_font import bitmap_font
            from adafruit_display_text import label

            vollkorn_font = bitmap_font.load_font("vollkorn20reg.pcf")
            hyperl_font = bitmap_font.load_font("hyperl20reg.pcf")

            print("Font metrics comparison:")

            # Test degree symbol specifically
            v_degree = label.Label(vollkorn_font, text="°", color=0x000000)
            h_degree = label.Label(hyperl_font, text="°", color=0x000000)

            print(f"Vollkorn '°' bounding box: {v_degree.bounding_box}")
            print(f"Hyperlegible '°' bounding box: {h_degree.bounding_box}")

            # Test number with degree
            v_temp = label.Label(vollkorn_font, text="3°", color=0x000000)
            h_temp = label.Label(hyperl_font, text="3°", color=0x000000)

            print(f"Vollkorn '3°' bounding box: {v_temp.bounding_box}")
            print(f"Hyperlegible '3°' bounding box: {h_temp.bounding_box}")

            # Test punctuation after degree
            v_punc = label.Label(vollkorn_font, text="3°.", color=0x000000)
            h_punc = label.Label(hyperl_font, text="3°.", color=0x000000)

            print(f"Vollkorn '3°.' bounding box: {v_punc.bounding_box}")
            print(f"Hyperlegible '3°.' bounding box: {h_punc.bounding_box}")

        except Exception as e:
            print(f"Font metrics debug failed: {e}")

    finally:
        # Clean up: remove from path and restore directory
        if circuitpy_400x300_path in sys.path:
            sys.path.remove(circuitpy_400x300_path)
        os.chdir(current_dir)

    # Convert displayio group to PIL Image
    return displayio_group_to_pil_image(main_group, width=400, height=300)


def load_web_bmp_icon(filename, x=0, y=0):
    """Load BMP icon for web rendering"""
    try:
        # Look in iconz/bmp folder
        icon_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "iconz", "bmp", filename
        )
        if os.path.exists(icon_path):
            # Load image and convert to displayio-like structure
            pil_image = Image.open(icon_path)

            # Convert PIL image to bitmap-like structure for displayio emulation
            width, height = pil_image.size
            bitmap = displayio.Bitmap(width, height, 2)
            palette = displayio.Palette(2)
            palette[0] = 0xFFFFFF  # White
            palette[1] = 0x000000  # Black

            # Simple black/white conversion
            for py in range(height):
                for px in range(width):
                    pixel = pil_image.getpixel((px, py))
                    if isinstance(pixel, tuple):
                        # RGB/RGBA
                        gray = sum(pixel[:3]) / 3
                    else:
                        # Grayscale
                        gray = pixel
                    bitmap[px, py] = 0 if gray > 128 else 1

            tilegrid = displayio.TileGrid(bitmap, pixel_shader=palette)
            tilegrid.x = x
            tilegrid.y = y
            return tilegrid
    except Exception as e:
        print(f"Failed to load web icon {filename}: {e}")
    return None


def calculate_web_moon_phase(timestamp=None):
    """Calculate moon phase for web using shared module"""
    if timestamp is None:
        raise ValueError("timestamp must be provided - no system time allowed")
    return calculate_moon_phase(timestamp)


def web_phase_to_icon_name(phase):
    """Convert numeric phase to BMP icon filename for web using shared module"""
    return phase_to_icon_name(phase)


def get_averages_from_csv(csv_data):
    """Extract historical averages from CSV data"""
    if not csv_data or len(csv_data) < 10:
        return get_default_averages()

    # Simple averaging - could be enhanced
    temps = [d["temp"] for d in csv_data[-50:]]  # Last 50 readings
    humidity_vals = [d["humidity"] for d in csv_data[-50:]]

    avg_temp = int(sum(temps) / len(temps)) if temps else 22
    avg_humidity = int(sum(humidity_vals) / len(humidity_vals)) if humidity_vals else 45

    return {
        "temp": {
            "day": avg_temp,
            "week": avg_temp - 1,
            "month": avg_temp - 2,
            "year": avg_temp - 3,
        },
        "humidity": {
            "day": avg_humidity,
            "week": avg_humidity + 1,
            "month": avg_humidity + 2,
            "year": avg_humidity + 3,
        },
    }


def get_graph_data_from_csv(csv_data, num_points=60):
    """Extract graph data from CSV data"""
    if not csv_data or len(csv_data) < 2:
        return get_default_graph_data()

    # Get last num_points readings
    recent_data = csv_data[-num_points:] if len(csv_data) >= num_points else csv_data

    temp_data = [d["temp"] for d in recent_data]
    humidity_data = [d["humidity"] for d in recent_data]

    # Pad if not enough data
    while len(temp_data) < num_points:
        temp_data.insert(0, temp_data[0] if temp_data else 22)
        humidity_data.insert(0, humidity_data[0] if humidity_data else 45)

    return temp_data, humidity_data


def get_default_averages():
    """Default averages when no CSV data available"""
    return {
        "temp": {"day": 22, "week": 21, "month": 20, "year": 19},
        "humidity": {"day": 45, "week": 46, "month": 47, "year": 48},
    }


def get_default_graph_data(num_points=60):
    """Default graph data when no CSV data available"""
    import math

    temp_data = []
    humidity_data = []

    for i in range(num_points):
        # Create realistic test data with variation
        temp = 22 + 4 * math.sin(i * 0.3) + (i % 3) - 1
        humidity = 50 + 8 * math.cos(i * 0.2) + (i % 5) - 2
        temp_data.append(max(18, min(26, temp)))
        humidity_data.append(max(40, min(60, humidity)))

    return temp_data, humidity_data


def displayio_group_to_pil_image(group, width=122, height=250):
    """Convert displayio.Group to PIL Image"""
    image = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(image)

    render_group_recursive(draw, group, 0, 0)
    return image


def render_group_recursive(draw, group, offset_x, offset_y):
    """Recursively render displayio group items"""
    group_x = getattr(group, "x", 0) + offset_x
    group_y = getattr(group, "y", 0) + offset_y

    if getattr(group, "hidden", False):
        return

    for item in group:
        if isinstance(item, displayio.Group):
            render_group_recursive(draw, item, group_x, group_y)
        elif hasattr(item, "__class__") and "Rect" in str(type(item)):
            # Allow black-filled Rect objects (header background) but skip others
            if hasattr(item, "fill") and item.fill == 0x000000:
                render_rect(draw, item, group_x, group_y)  # Render black backgrounds
            else:
                pass  # Skip other Rect objects (forecast borders)
        elif hasattr(item, "__class__") and "Line" in str(type(item)):
            # TEMP: Skip ALL Line objects to test
            pass
        elif hasattr(item, "__class__") and "TileGrid" in str(type(item)):
            render_tilegrid(draw, item, group_x, group_y)


def render_rect(draw, rect, offset_x, offset_y):
    """Render displayio Rect to PIL"""
    x = rect.x + offset_x
    y = rect.y + offset_y
    width = rect.width
    height = rect.height

    # Handle fill
    fill_color = None
    if hasattr(rect, "fill") and rect.fill is not None:
        fill_color = convert_displayio_color(rect.fill)

    # Handle outline
    outline_color = None
    if hasattr(rect, "outline") and rect.outline is not None:
        outline_color = convert_displayio_color(rect.outline)

    # Draw filled rectangle
    if fill_color is not None:
        coords = [x, y, x + width - 1, y + height - 1]
        draw.rectangle(coords, fill=fill_color)

    # Draw outline (stroke=2 for graph borders)
    if outline_color is not None:
        coords = [x, y, x + width - 1, y + height - 1]
        stroke_width = 2
        for i in range(stroke_width):
            outline_coords = [
                coords[0] - i,
                coords[1] - i,
                coords[2] + i,
                coords[3] + i,
            ]
            draw.rectangle(outline_coords, outline=outline_color, fill=None)


def render_line(draw, line_obj, offset_x, offset_y):
    """Render displayio Line to PIL by rendering its bitmap"""
    x = line_obj.x + offset_x
    y = line_obj.y + offset_y
    bitmap = line_obj.bitmap
    color = convert_displayio_color(line_obj.color)

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


def render_tilegrid(draw, tilegrid, offset_x, offset_y):
    """Render displayio TileGrid to PIL - handles text rendering"""
    x = tilegrid.x + offset_x
    y = tilegrid.y + offset_y

    if getattr(tilegrid, "hidden", False):
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
