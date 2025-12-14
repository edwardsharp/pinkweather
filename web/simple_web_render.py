"""
Minimal web renderer using the exact shared display code from CIRCUITPY
"""

import sys
import os
import importlib.util
from PIL import Image, ImageDraw, ImageFont
import displayio

# Add CIRCUITPY to path so we can use the shared display module
circuitpy_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'CIRCUITPY')

# Add 300x400/CIRCUITPY to path for the new display
circuitpy_400x300_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '300x400', 'CIRCUITPY')
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
        weather_display_path = os.path.join(circuitpy_path, 'display.py')
        spec = importlib.util.spec_from_file_location("weather_display", weather_display_path)
        weather_display = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(weather_display)

        create_complete_display = weather_display.create_complete_display
        format_time_short = weather_display.format_time_short

        # Process CSV data for averages and graphs
        averages = get_averages_from_csv(csv_data) if csv_data else get_default_averages()
        temp_data, humidity_data = get_graph_data_from_csv(csv_data) if csv_data else get_default_graph_data()

        # Process system status
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
            battery_status = "B85"

        # Create display using EXACT same function as hardware
        display_group = create_complete_display(
            temp_c, humidity, averages, temp_data, humidity_data,
            sd_status, sd_time, uptime, power_status, battery_status
        )

    finally:
        os.chdir(current_dir)

    # Convert displayio group to PIL Image
    return displayio_group_to_pil_image(display_group)


def render_400x300_display(text_content):
    """
    Render 400x300 weather display for web using the weather layout
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

        # Load text display module from specific path
        text_display_path = os.path.join(circuitpy_400x300_path, 'display.py')
        spec = importlib.util.spec_from_file_location("text_display", text_display_path)
        text_display = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(text_display)

        # Import alternative header functions
        try:
            create_weather_layout = text_display.create_weather_layout
            header_path = os.path.join(circuitpy_400x300_path, 'header.py')
            spec = importlib.util.spec_from_file_location("header", header_path)
            header = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(header)
            get_header_height = header.get_header_height

            # Import forecast row for icon loading setup
            forecast_row_path = os.path.join(circuitpy_400x300_path, 'forecast_row.py')
            spec = importlib.util.spec_from_file_location("forecast_row", forecast_row_path)
            forecast_row_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(forecast_row_module)
            set_icon_loader = forecast_row_module.set_icon_loader

            # Store the configured module to avoid re-import issues
            configured_forecast_module = forecast_row_module
        except Exception as e:
            print(f"Alternative header not available: {e}")
            create_alt_weather_layout = None
            get_alt_header_height = None

        # Import weather API module and cached version
        weather_api_path = os.path.join(circuitpy_400x300_path, 'weather_api.py')
        spec = importlib.util.spec_from_file_location("weather_api", weather_api_path)
        weather_api = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(weather_api)

        # Import web-specific cached weather module
        from cached_weather import fetch_weather_data_cached

        # Import moon phase module
        moon_phase_path = os.path.join(circuitpy_400x300_path, 'moon_phase.py')
        spec = importlib.util.spec_from_file_location("moon_phase_module", moon_phase_path)
        moon_phase_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(moon_phase_module)

        # Load .env file for web server configuration
        env_config = {}
        env_path = os.path.join(os.path.dirname(__file__), '.env')
        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                for line in f:
                    if '=' in line and not line.strip().startswith('#'):
                        key, value = line.strip().split('=', 1)
                        env_config[key.strip()] = value.strip()

        # Configure weather API from environment
        weather_config = None
        if all(key in env_config for key in ['OPENWEATHER_API_KEY', 'LATITUDE', 'LONGITUDE']):
            weather_config = {
                'api_key': env_config['OPENWEATHER_API_KEY'],
                'latitude': float(env_config['LATITUDE']),
                'longitude': float(env_config['LONGITUDE']),
                'units': 'metric'
            }

        # Get timezone offset for web server (same as hardware)
        timezone_offset = int(env_config.get('TIMEZONE_OFFSET_HOURS', '-5'))

        # Get current moon phase
        moon_phase = calculate_web_moon_phase()
        moon_icon_name = web_phase_to_icon_name(moon_phase)

        # Create weather layout with sample data
        import time
        current_time = time.localtime()
        days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

        day_name = days[current_time.tm_wday]
        day_num = current_time.tm_mday
        month_name = months[current_time.tm_mon - 1]

        # Calculate moon phase using shared module
        current_phase = moon_phase_module.calculate_moon_phase()
        moon_icon_name = moon_phase_module.phase_to_icon_name(current_phase)
        print(f"Web server moon phase: {moon_icon_name}")

        # Set up icon loader for forecast rows (web version uses real icons)
        def web_icon_loader(filename):
            """Web version icon loading that matches hardware interface"""

            try:
                # Look in iconz/bmp folder
                icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'iconz', 'bmp', filename)

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
                    return tilegrid
                else:

                    return None
            except Exception as e:

                return None

        # Configure the icon loader on the same module instance
        set_icon_loader(True, web_icon_loader)  # True indicates icons are "available"

        # Inject the configured forecast module into sys.modules to prevent re-import
        import sys
        sys.modules['forecast_row'] = configured_forecast_module

        # Get weather data (real or fallback)
        if weather_config:
            print("Using real weather data from .env configuration (with caching)")
            forecast_data = fetch_weather_data_cached(weather_config)
            weather_data = weather_api.get_display_variables(forecast_data, timezone_offset)
        else:
            print("No .env configuration found, using fallback weather data")
            weather_data = weather_api.get_display_variables(None, timezone_offset)

        # Use single-line header layout
        print("Using single-line header layout for web preview")

        main_group = create_weather_layout(
            current_timestamp=weather_data.get('current_timestamp'),
            timezone_offset_hours=timezone_offset,
            forecast_data=weather_data['forecast_data'],
            weather_desc=weather_data['weather_desc'],
            icon_loader=web_icon_loader
        )

        # Icons are integrated directly into forecast cells and header via icon_loader

    finally:
        # Clean up: remove from path and restore directory
        if circuitpy_400x300_path in sys.path:
            sys.path.remove(circuitpy_400x300_path)
        os.chdir(current_dir)

    # Convert displayio group to PIL Image
    return displayio_group_to_pil_image(main_group, width=400, height=300)


def load_web_bmp_icon(filename, x, y):
    """Load BMP icon for web rendering"""
    try:
        # Look in iconz/bmp folder
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'iconz', 'bmp', filename)
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


def calculate_web_moon_phase():
    """Calculate moon phase for web using shared module"""
    import time
    current_timestamp = int(time.time())
    return calculate_moon_phase(current_timestamp)

def web_phase_to_icon_name(phase):
    """Convert numeric phase to BMP icon filename for web using shared module"""
    return phase_to_icon_name(phase)


def get_averages_from_csv(csv_data):
    """Extract historical averages from CSV data"""
    if not csv_data or len(csv_data) < 10:
        return get_default_averages()

    # Simple averaging - could be enhanced
    temps = [d['temp'] for d in csv_data[-50:]]  # Last 50 readings
    humidity_vals = [d['humidity'] for d in csv_data[-50:]]

    avg_temp = int(sum(temps) / len(temps)) if temps else 22
    avg_humidity = int(sum(humidity_vals) / len(humidity_vals)) if humidity_vals else 45

    return {
        'temp': {'day': avg_temp, 'week': avg_temp-1, 'month': avg_temp-2, 'year': avg_temp-3},
        'humidity': {'day': avg_humidity, 'week': avg_humidity+1, 'month': avg_humidity+2, 'year': avg_humidity+3}
    }


def get_graph_data_from_csv(csv_data, num_points=60):
    """Extract graph data from CSV data"""
    if not csv_data or len(csv_data) < 2:
        return get_default_graph_data()

    # Get last num_points readings
    recent_data = csv_data[-num_points:] if len(csv_data) >= num_points else csv_data

    temp_data = [d['temp'] for d in recent_data]
    humidity_data = [d['humidity'] for d in recent_data]

    # Pad if not enough data
    while len(temp_data) < num_points:
        temp_data.insert(0, temp_data[0] if temp_data else 22)
        humidity_data.insert(0, humidity_data[0] if humidity_data else 45)

    return temp_data, humidity_data


def get_default_averages():
    """Default averages when no CSV data available"""
    return {
        'temp': {'day': 22, 'week': 21, 'month': 20, 'year': 19},
        'humidity': {'day': 45, 'week': 46, 'month': 47, 'year': 48}
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
    image = Image.new('RGB', (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(image)

    render_group_recursive(draw, group, 0, 0)
    return image


def render_group_recursive(draw, group, offset_x, offset_y):
    """Recursively render displayio group items"""
    group_x = getattr(group, 'x', 0) + offset_x
    group_y = getattr(group, 'y', 0) + offset_y

    if getattr(group, 'hidden', False):
        return

    for item in group:
        if isinstance(item, displayio.Group):
            render_group_recursive(draw, item, group_x, group_y)
        elif hasattr(item, '__class__') and 'Rect' in str(type(item)):
            render_rect(draw, item, group_x, group_y)
        elif hasattr(item, '__class__') and 'Line' in str(type(item)):
            render_line(draw, item, group_x, group_y)
        elif hasattr(item, '__class__') and 'TileGrid' in str(type(item)):
            render_tilegrid(draw, item, group_x, group_y)


def render_rect(draw, rect, offset_x, offset_y):
    """Render displayio Rect to PIL"""
    x = rect.x + offset_x
    y = rect.y + offset_y
    width = rect.width
    height = rect.height

    # Handle fill
    fill_color = None
    if hasattr(rect, 'fill') and rect.fill is not None:
        fill_color = convert_displayio_color(rect.fill)

    # Handle outline
    outline_color = None
    if hasattr(rect, 'outline') and rect.outline is not None:
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
            outline_coords = [coords[0] - i, coords[1] - i, coords[2] + i, coords[3] + i]
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
