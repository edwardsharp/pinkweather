"""
Hardware adapter for CircuitPython - interfaces with real sensors and SD card
"""
import time
import os

def get_sensor_data(sensor):
    """Get current sensor readings"""
    return {
        'temp_c': sensor.temperature,
        'humidity': sensor.relative_humidity
    }

def get_csv_data_from_sd(sd_available):
    """Read CSV data from SD card and return structured data"""
    if not sd_available:
        return []

    csv_data = []
    try:
        with open("/sd/recent.csv", "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("uptime_ms"):  # Skip header
                    try:
                        parts = line.split(",")
                        timestamp = int(parts[0])
                        temp = float(parts[1])
                        humidity = float(parts[2])

                        csv_data.append({
                            'timestamp': timestamp,
                            'temp': temp,
                            'humidity': humidity
                        })
                    except (ValueError, IndexError):
                        continue
    except OSError:
        pass  # File doesn't exist

    return csv_data

def get_sd_total_time(sd_available):
    """Get total time span of data stored on SD card"""
    if not sd_available:
        return "0s"

    try:
        min_time = None
        max_time = None

        # Check recent.csv for time range
        with open("/sd/recent.csv", "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("uptime_ms"):
                    try:
                        timestamp = int(line.split(",")[0])
                        if min_time is None or timestamp < min_time:
                            min_time = timestamp
                        if max_time is None or timestamp > max_time:
                            max_time = timestamp
                    except (ValueError, IndexError):
                        continue

        if min_time and max_time:
            from display_logic import format_time_short
            total_seconds = (max_time - min_time) / 1000
            return format_time_short(total_seconds)
    except OSError:
        pass

    return "0s"

def get_system_status(sd_available):
    """Get current system status"""
    from display_logic import format_time_short

    return {
        'sd_available': sd_available,
        'sd_total_time': get_sd_total_time(sd_available),
        'uptime': format_time_short(time.monotonic()),
        'power_status': 'P',  # Will update when we detect power source
        'battery_status': 'B--'  # Will update when battery monitoring is added
    }

def get_historical_data(sd_available):
    """Get all historical data needed for display"""
    from display_logic import calculate_historical_averages, get_graph_data_from_csv

    # Get CSV data
    csv_data = get_csv_data_from_sd(sd_available)

    # Calculate averages
    current_time_ms = time.monotonic() * 1000
    averages = calculate_historical_averages(csv_data, current_time_ms)

    # Get graph data
    temp_graph_data, humidity_graph_data = get_graph_data_from_csv(csv_data)

    return {
        'temp_averages': averages['temp'],
        'humidity_averages': averages['humidity'],
        'temp_graph_data': temp_graph_data,
        'humidity_graph_data': humidity_graph_data
    }

def create_display_from_elements(elements):
    """Convert display elements to CircuitPython displayio objects"""
    import displayio
    from adafruit_display_text import label
    from adafruit_bitmap_font import bitmap_font
    from adafruit_display_shapes.rect import Rect
    from adafruit_display_shapes.line import Line
    import terminalio

    # Load fonts
    large_font = bitmap_font.load_font("barlowcond60.pcf")
    small_font = bitmap_font.load_font("barlowcond30.pcf")

    # Create main group
    g = displayio.Group()

    for element in elements:
        if element['type'] == 'rect':
            # Convert hex colors to integers
            fill_color = None
            outline_color = None

            if 'fill' in element:
                fill_color = int(element['fill'].replace('#', ''), 16)
            if 'outline' in element:
                outline_color = int(element['outline'].replace('#', ''), 16)

            stroke = element.get('stroke', 1)

            rect = Rect(
                element['x'], element['y'],
                element['width'], element['height'],
                fill=fill_color,
                outline=outline_color,
                stroke=stroke
            )
            g.append(rect)

        elif element['type'] == 'text':
            # Convert hex color to integer
            color = int(element['color'].replace('#', ''), 16)

            # Choose font
            if element['font'] == 'large':
                font = large_font
            elif element['font'] == 'small':
                font = small_font
            else:  # 'tiny' or default
                font = terminalio.FONT

            text_label = label.Label(font, text=element['text'], color=color)

            # Handle positioning
            if 'anchor_point' in element and 'anchored_position' in element:
                text_label.anchor_point = element['anchor_point']
                text_label.anchored_position = element['anchored_position']
            else:
                text_label.x = element['x']
                text_label.y = element['y']

            g.append(text_label)

        elif element['type'] == 'line':
            # Convert hex color to integer
            color = int(element['color'].replace('#', ''), 16)

            line = Line(
                element['x1'], element['y1'],
                element['x2'], element['y2'],
                color
            )
            g.append(line)

    return g
