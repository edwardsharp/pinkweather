"""
Web adapter for mock data and HTML rendering - for testing and development
"""
import time
import random

def get_mock_sensor_data():
    """Get mock sensor readings that vary slightly"""
    base_temp = 22.0
    base_humidity = 45.0

    # Add some random variation
    temp_variation = random.uniform(-2.0, 3.0)
    humidity_variation = random.uniform(-5.0, 8.0)

    return {
        'temp_c': base_temp + temp_variation,
        'humidity': base_humidity + humidity_variation
    }

def get_mock_csv_data(scenario='normal'):
    """Generate mock CSV data for different scenarios"""
    scenarios = {
        'normal': generate_normal_data(),
        'trending_up': generate_trending_data(1.0),
        'trending_down': generate_trending_data(-0.5),
        'volatile': generate_volatile_data(),
        'seasonal': generate_seasonal_data(),
        'empty': []
    }

    return scenarios.get(scenario, scenarios['normal'])

def generate_normal_data(num_points=100):
    """Generate normal temperature/humidity data"""
    data = []
    current_time = time.time() * 1000

    for i in range(num_points):
        timestamp = int(current_time - (num_points - i) * 180000)  # 3 min intervals
        temp = 22.0 + random.uniform(-3.0, 4.0)
        humidity = 45.0 + random.uniform(-8.0, 12.0)

        data.append({
            'timestamp': timestamp,
            'temp': temp,
            'humidity': humidity
        })

    return data

def generate_trending_data(trend_rate, num_points=100):
    """Generate data with a trend"""
    data = []
    current_time = time.time() * 1000

    for i in range(num_points):
        timestamp = int(current_time - (num_points - i) * 180000)

        # Add trend over time
        trend_offset = (i / num_points) * trend_rate * 10
        temp = 22.0 + trend_offset + random.uniform(-2.0, 2.0)
        humidity = 45.0 + trend_offset * 2 + random.uniform(-5.0, 5.0)

        data.append({
            'timestamp': timestamp,
            'temp': temp,
            'humidity': humidity
        })

    return data

def generate_volatile_data(num_points=100):
    """Generate highly variable data"""
    data = []
    current_time = time.time() * 1000

    for i in range(num_points):
        timestamp = int(current_time - (num_points - i) * 180000)
        temp = 22.0 + random.uniform(-8.0, 12.0)
        humidity = 45.0 + random.uniform(-20.0, 25.0)

        data.append({
            'timestamp': timestamp,
            'temp': temp,
            'humidity': humidity
        })

    return data

def generate_seasonal_data(num_points=100):
    """Generate data with seasonal patterns"""
    import math
    data = []
    current_time = time.time() * 1000

    for i in range(num_points):
        timestamp = int(current_time - (num_points - i) * 180000)

        # Simulate daily temperature cycle
        daily_cycle = math.sin(2 * math.pi * i / 24) * 3
        temp = 22.0 + daily_cycle + random.uniform(-1.5, 1.5)

        # Inverse humidity cycle
        humidity = 45.0 - daily_cycle + random.uniform(-3.0, 3.0)

        data.append({
            'timestamp': timestamp,
            'temp': temp,
            'humidity': humidity
        })

    return data

def get_mock_system_status(scenario='normal'):
    """Get mock system status for different scenarios"""
    scenarios = {
        'normal': {
            'sd_available': True,
            'sd_total_time': '5d',
            'uptime': '2h',
            'power_status': 'P',
            'battery_status': 'B85'
        },
        'no_sd': {
            'sd_available': False,
            'sd_total_time': '0s',
            'uptime': '15m',
            'power_status': 'P',
            'battery_status': 'B--'
        },
        'long_running': {
            'sd_available': True,
            'sd_total_time': '45d',
            'uptime': '12d',
            'power_status': 'P',
            'battery_status': 'B23'
        },
        'fresh_boot': {
            'sd_available': True,
            'sd_total_time': '0s',
            'uptime': '30s',
            'power_status': 'P',
            'battery_status': 'B--'
        }
    }

    return scenarios.get(scenario, scenarios['normal'])

def get_mock_historical_data(csv_data):
    """Get mock historical data from CSV data"""
    from display_logic import calculate_historical_averages, get_graph_data_from_csv

    # Calculate averages
    current_time_ms = time.time() * 1000
    averages = calculate_historical_averages(csv_data, current_time_ms)

    # Get graph data
    temp_graph_data, humidity_graph_data = get_graph_data_from_csv(csv_data)

    return {
        'temp_averages': averages['temp'],
        'humidity_averages': averages['humidity'],
        'temp_graph_data': temp_graph_data,
        'humidity_graph_data': humidity_graph_data
    }

def create_pil_image_from_elements(elements):
    """Convert display elements to PIL Image"""
    from PIL import Image, ImageDraw, ImageFont
    import os

    DISPLAY_WIDTH = 122
    DISPLAY_HEIGHT = 250

    # Create image
    image = Image.new("RGB", (DISPLAY_WIDTH, DISPLAY_HEIGHT), (255, 255, 255))
    draw = ImageDraw.Draw(image)

    # Try to load Barlow Condensed fonts to match hardware
    try:
        large_font = ImageFont.truetype("googz/Barlow_Condensed/BarlowCondensed-Regular.ttf", 60)
    except:
        try:
            large_font = ImageFont.truetype("Arial.ttf", 32)
        except:
            large_font = ImageFont.load_default()

    try:
        small_font = ImageFont.truetype("googz/Barlow_Condensed/BarlowCondensed-Regular.ttf", 30)
    except:
        try:
            small_font = ImageFont.truetype("Arial.ttf", 12)
        except:
            small_font = ImageFont.load_default()

    try:
        # Use monospace for tiny font to match terminalio
        tiny_font = ImageFont.truetype("DejaVuSansMono.ttf", 8)
    except:
        try:
            tiny_font = ImageFont.truetype("Courier.ttf", 8)
        except:
            tiny_font = ImageFont.load_default()

    for element in elements:
        if element['type'] == 'rect':
            # Convert hex color to RGB tuple
            fill_color = None
            outline_color = None

            if 'fill' in element:
                hex_color = element['fill'].replace('#', '')
                fill_color = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

            if 'outline' in element:
                hex_color = element['outline'].replace('#', '')
                outline_color = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

            x, y = element['x'], element['y']
            width, height = element['width'], element['height']

            if fill_color:
                draw.rectangle([x, y, x + width, y + height], fill=fill_color)

            if outline_color:
                stroke = element.get('stroke', 1)
                for i in range(stroke):
                    draw.rectangle([x + i, y + i, x + width - i, y + height - i], outline=outline_color)

        elif element['type'] == 'text':
            # Convert hex color to RGB tuple
            hex_color = element['color'].replace('#', '')
            text_color = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

            # Choose font
            if element['font'] == 'large':
                font = large_font
            elif element['font'] == 'small':
                font = small_font
            else:  # 'tiny' or default
                font = tiny_font

            # Handle positioning - adjust for CircuitPython displayio compatibility
            if 'anchored_position' in element:
                x, y = element['anchored_position']
                anchor = element.get('anchor_point', (0, 0))

                if anchor == (0.5, 0.5):
                    # Center alignment
                    bbox = draw.textbbox((0, 0), element['text'], font=font)
                    text_width = bbox[2] - bbox[0]
                    text_height = bbox[3] - bbox[1]
                    x -= text_width // 2
                    y -= text_height // 2

                draw.text((x, y), element['text'], font=font, fill=text_color)
            else:
                # Adjust y position for font baseline differences
                # CircuitPython displayio uses top-left, PIL uses baseline
                adjust_y = element['y']
                if element['font'] == 'large':
                    adjust_y = element['y'] + 45  # Adjust for large font baseline
                elif element['font'] == 'small':
                    adjust_y = element['y'] + 22  # Adjust for small font baseline
                else:  # tiny
                    adjust_y = element['y'] + 8   # Adjust for tiny font baseline

                draw.text((element['x'], adjust_y), element['text'], font=font, fill=text_color)

        elif element['type'] == 'line':
            # Convert hex color to RGB tuple
            hex_color = element['color'].replace('#', '')
            line_color = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

            draw.line([element['x1'], element['y1'], element['x2'], element['y2']], fill=line_color, width=1)

    return image

def get_scenario_list():
    """Get list of available test scenarios"""
    return [
        {'name': 'Normal', 'csv': 'normal', 'status': 'normal'},
        {'name': 'Trending Up', 'csv': 'trending_up', 'status': 'normal'},
        {'name': 'Trending Down', 'csv': 'trending_down', 'status': 'normal'},
        {'name': 'Volatile Data', 'csv': 'volatile', 'status': 'normal'},
        {'name': 'Seasonal Pattern', 'csv': 'seasonal', 'status': 'normal'},
        {'name': 'No SD Card', 'csv': 'empty', 'status': 'no_sd'},
        {'name': 'Long Running', 'csv': 'normal', 'status': 'long_running'},
        {'name': 'Fresh Boot', 'csv': 'empty', 'status': 'fresh_boot'}
    ]
