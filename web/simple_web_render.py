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

        create_weather_layout = text_display.create_weather_layout
        get_forecast_icon_positions_from_layout = text_display.get_forecast_icon_positions_from_layout
        get_header_height = text_display.get_header_height

        # Import alternative header functions
        try:
            create_alt_weather_layout = text_display.create_alt_weather_layout
            alt_header_path = os.path.join(circuitpy_400x300_path, 'alt_weather_header.py')
            spec = importlib.util.spec_from_file_location("alt_weather_header", alt_header_path)
            alt_weather_header = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(alt_weather_header)
            get_alt_header_height = alt_weather_header.get_alt_header_height

            # Import forecast row for icon positions
            forecast_row_path = os.path.join(circuitpy_400x300_path, 'forecast_row.py')
            spec = importlib.util.spec_from_file_location("forecast_row", forecast_row_path)
            forecast_row_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(forecast_row_module)
            get_forecast_icon_positions = forecast_row_module.get_forecast_icon_positions
        except Exception as e:
            print(f"Alternative header not available: {e}")
            create_alt_weather_layout = None
            get_alt_header_height = None
            get_forecast_icon_positions = None

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

        # Check for alternative header option in .env
        use_alternative_header = env_config.get('USE_ALTERNATIVE_HEADER', 'true').lower() == 'true'

        # Import icon position constants
        WEATHER_ICON_X = text_display.WEATHER_ICON_X
        WEATHER_ICON_Y = text_display.WEATHER_ICON_Y
        MOON_ICON_X = text_display.MOON_ICON_X
        MOON_ICON_Y = text_display.MOON_ICON_Y

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

        # Get weather data (real or fallback)
        if weather_config:
            print("Using real weather data from .env configuration (with caching)")
            forecast_data = fetch_weather_data_cached(weather_config)
            weather_data = weather_api.get_display_variables(forecast_data, timezone_offset)
        else:
            print("No .env configuration found, using fallback weather data")
            weather_data = weather_api.get_display_variables(None, timezone_offset)

        # Choose layout based on configuration
        if use_alternative_header and create_alt_weather_layout:
            print("Using alternative header layout for web preview")
            main_group = create_alt_weather_layout(
                current_timestamp=weather_data.get('current_timestamp'),
                timezone_offset_hours=timezone_offset,
                forecast_data=weather_data['forecast_data'],
                weather_desc=weather_data['weather_desc']
            )
        else:
            print("Using original header layout for web preview")
            main_group = create_weather_layout(
                day_name=weather_data['day_name'],
                day_num=weather_data['day_num'],
                month_name=weather_data['month_name'],
                current_temp=weather_data['current_temp'],
                feels_like=weather_data['feels_like'],
                high_temp=weather_data['high_temp'],
                low_temp=weather_data['low_temp'],
                sunrise_time=weather_data['sunrise_time'],
                sunset_time=weather_data['sunset_time'],
                weather_desc=weather_data['weather_desc'],
                weather_icon_name=weather_data['weather_icon_name'],
                moon_icon_name=f"{moon_icon_name}.bmp",
                forecast_data=weather_data['forecast_data']
            )

        # Add icons based on layout type
        if use_alternative_header and create_alt_weather_layout:
            # Alternative header - only forecast icons
            if weather_data['forecast_data'] and get_forecast_icon_positions:
                header_height = get_alt_header_height() if get_alt_header_height else 25
                forecast_y = header_height + 2  # Match hardware positioning
                forecast_positions = get_forecast_icon_positions(weather_data['forecast_data'], forecast_y)

                for x, y, icon_code in forecast_positions:
                    forecast_icon = load_web_bmp_icon(f"{icon_code}.bmp", x, y)
                    if forecast_icon:
                        main_group.append(forecast_icon)
        else:
            # Original header - weather, moon, and forecast icons
            # Add weather icon from weather data
            weather_icon = load_web_bmp_icon(weather_data['weather_icon_name'], WEATHER_ICON_X, WEATHER_ICON_Y)
            if weather_icon:
                main_group.append(weather_icon)

            # Add moon phase icon
            moon_icon = load_web_bmp_icon(f"{moon_icon_name}.bmp", MOON_ICON_X, MOON_ICON_Y)
            if moon_icon:
                main_group.append(moon_icon)

            # Add forecast icons
            if weather_data['forecast_data']:
                # Calculate forecast_y position (same logic as in display.py)
                header_height = get_header_height()
                forecast_y = header_height + 15
                forecast_positions = get_forecast_icon_positions_from_layout(main_group, weather_data['forecast_data'], forecast_y)

                for x, y, icon_code in forecast_positions:
                    forecast_icon = load_web_bmp_icon(f"{icon_code}.bmp", x, y)
                    if forecast_icon:
                        main_group.append(forecast_icon)

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
    """Calculate moon phase for web (simplified)"""
    import time
    current_time = time.localtime()
    year = current_time.tm_year
    month = current_time.tm_mon
    day = current_time.tm_mday

    # Calculate Julian day number
    if month <= 2:
        year -= 1
        month += 12

    a = year // 100
    b = 2 - a + (a // 4)

    julian_day = int(365.25 * (year + 4716)) + int(30.6001 * (month + 1)) + day + b - 1524.5

    # Calculate days since known new moon (January 6, 2000)
    days_since_new_moon = julian_day - 2451550.1

    # Calculate number of lunar cycles
    lunar_cycle_length = 29.53058867
    cycles = days_since_new_moon / lunar_cycle_length

    # Get fractional part (phase within current cycle)
    phase = cycles - int(cycles)

    # Ensure phase is between 0 and 1
    if phase < 0:
        phase += 1

    return phase


def web_phase_to_icon_name(phase):
    """Convert numeric phase to BMP icon filename for web"""
    if phase < 0.03 or phase > 0.97:
        return "moon-new"
    elif phase < 0.22:
        crescent_num = int((phase - 0.03) / 0.038) + 1
        crescent_num = max(1, min(5, crescent_num))
        return f"moon-waxing-crescent-{crescent_num}"
    elif phase < 0.28:
        return "moon-first-quarter"
    elif phase < 0.47:
        gibbous_num = int((phase - 0.28) / 0.032) + 1
        gibbous_num = max(1, min(6, gibbous_num))
        return f"moon-waxing-gibbous-{gibbous_num}"
    elif phase < 0.53:
        return "moon-full"
    elif phase < 0.72:
        gibbous_num = 6 - int((phase - 0.53) / 0.032)
        gibbous_num = max(1, min(6, gibbous_num))
        return f"moon-waning-gibbous-{gibbous_num}"
    elif phase < 0.78:
        return "moon-third-quarter"
    else:
        crescent_num = 5 - int((phase - 0.78) / 0.038)
        crescent_num = max(1, min(5, crescent_num))
        return f"moon-waning-crescent-{crescent_num}"


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
