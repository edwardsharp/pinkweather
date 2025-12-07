"""
Shared display logic for pinkweather - pure UI layout functions
Works with both CircuitPython hardware and web mock implementations
"""

def format_time_short(seconds):
    """Format time in very short format: 30s, 9d, 25m, etc."""
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:  # < 1 hour
        return f"{int(seconds/60)}m"
    elif seconds < 86400:  # < 1 day
        return f"{int(seconds/3600)}h"
    elif seconds < 2592000:  # < 30 days
        return f"{int(seconds/86400)}d"
    elif seconds < 31536000:  # < 365 days
        return f"{int(seconds/2592000)}M"
    else:
        return f"{int(seconds/31536000)}y"

def calculate_historical_averages(csv_data, current_time_ms):
    """Calculate day, week, month, year averages from CSV data"""
    if not csv_data:
        return {
            'temp': {'day': 0, 'week': 0, 'month': 0, 'year': 0},
            'humidity': {'day': 0, 'week': 0, 'month': 0, 'year': 0}
        }

    # Time periods in milliseconds
    day_ms = 24 * 60 * 60 * 1000
    week_ms = 7 * day_ms
    month_ms = 30 * day_ms
    year_ms = 365 * day_ms

    periods = {
        'day': current_time_ms - day_ms,
        'week': current_time_ms - week_ms,
        'month': current_time_ms - month_ms,
        'year': current_time_ms - year_ms
    }

    averages = {
        'temp': {'day': 0, 'week': 0, 'month': 0, 'year': 0},
        'humidity': {'day': 0, 'week': 0, 'month': 0, 'year': 0}
    }

    for period_name, cutoff_time in periods.items():
        temp_sum = humidity_sum = count = 0

        for entry in csv_data:
            if entry['timestamp'] >= cutoff_time:
                temp_sum += entry['temp']
                humidity_sum += entry['humidity']
                count += 1

        if count > 0:
            averages['temp'][period_name] = int(temp_sum / count)
            averages['humidity'][period_name] = int(humidity_sum / count)

    return averages

def get_graph_data_from_csv(csv_data, num_points=60):
    """Extract graph data points from CSV data"""
    if not csv_data:
        return [22] * num_points, [45] * num_points

    # Get the last num_points entries
    recent_entries = csv_data[-num_points:] if len(csv_data) >= num_points else csv_data

    temp_data = [entry['temp'] for entry in recent_entries]
    humidity_data = [entry['humidity'] for entry in recent_entries]

    # Fill with first values if we don't have enough points
    if len(temp_data) < num_points and temp_data:
        first_temp = temp_data[0]
        first_humidity = humidity_data[0]
        while len(temp_data) < num_points:
            temp_data.insert(0, first_temp)
            humidity_data.insert(0, first_humidity)
    elif len(temp_data) == 0:
        temp_data = [22] * num_points
        humidity_data = [45] * num_points

    return temp_data[-num_points:], humidity_data[-num_points:]

def create_display_layout(sensor_data, historical_data, system_status):
    """
    Create complete display layout as a list of display elements

    Args:
        sensor_data: {'temp_c': float, 'humidity': float}
        historical_data: {'temp_averages': dict, 'humidity_averages': dict,
                          'temp_graph_data': list, 'humidity_graph_data': list}
        system_status: {'sd_available': bool, 'sd_total_time': str, 'uptime': str,
                       'power_status': str, 'battery_status': str}

    Returns:
        List of display elements with type, position, and styling info
    """

    DISPLAY_WIDTH = 122
    DISPLAY_HEIGHT = 250
    BLACK = '#000000'
    WHITE = '#FFFFFF'
    RED = '#FF0000'

    elements = []

    # Background
    elements.append({
        'type': 'rect',
        'x': 0, 'y': 0,
        'width': DISPLAY_WIDTH, 'height': DISPLAY_HEIGHT,
        'fill': WHITE
    })

    # Current temperature (top)
    temp_str = str(int(round(sensor_data['temp_c'])))
    is_negative = sensor_data['temp_c'] < 0

    temp_elements = create_temperature_elements(temp_str, is_negative, 20, 20)
    elements.extend(temp_elements)

    # Temperature averages
    temp_avg_text = f"{historical_data['temp_averages']['day']}, {historical_data['temp_averages']['week']}, {historical_data['temp_averages']['month']}, {historical_data['temp_averages']['year']}"
    elements.append({
        'type': 'text',
        'text': temp_avg_text,
        'font': 'small',
        'color': BLACK,
        'anchor_point': (0.5, 0.5),
        'anchored_position': (DISPLAY_WIDTH // 2, 75)
    })

    # Temperature graph with border
    temp_y_start = 84
    temp_height = 32

    # Temperature border
    elements.append({
        'type': 'rect',
        'x': 8, 'y': temp_y_start - 2,
        'width': DISPLAY_WIDTH - 16, 'height': temp_height + 4,
        'outline': BLACK, 'stroke': 2
    })

    # Temperature graph lines and labels
    temp_graph_elements = create_line_graph_elements(
        historical_data['temp_graph_data'], BLACK, temp_y_start, temp_height
    )
    elements.extend(temp_graph_elements)

    # Humidity graph with border
    humidity_y_start = 124
    humidity_height = 32

    # Humidity border
    elements.append({
        'type': 'rect',
        'x': 8, 'y': humidity_y_start - 2,
        'width': DISPLAY_WIDTH - 16, 'height': humidity_height + 4,
        'outline': RED, 'stroke': 2
    })

    # Humidity graph lines and labels
    humidity_graph_elements = create_line_graph_elements(
        historical_data['humidity_graph_data'], RED, humidity_y_start, humidity_height
    )
    elements.extend(humidity_graph_elements)

    # Humidity averages (right under the graph)
    humidity_avg_text = f"{historical_data['humidity_averages']['day']}, {historical_data['humidity_averages']['week']}, {historical_data['humidity_averages']['month']}, {historical_data['humidity_averages']['year']}"
    elements.append({
        'type': 'text',
        'text': humidity_avg_text,
        'font': 'small',
        'color': RED,
        'anchor_point': (0.5, 0.5),
        'anchored_position': (DISPLAY_WIDTH // 2, humidity_y_start + humidity_height + 10)
    })

    # Current humidity (bottom area)
    humidity_str = str(int(round(sensor_data['humidity'])))
    humidity_elements = create_humidity_elements(humidity_str, 20, humidity_y_start + humidity_height + 38)
    elements.extend(humidity_elements)

    # Status bar at bottom
    status_bar_height = 12
    status_bar_y = DISPLAY_HEIGHT - status_bar_height

    elements.append({
        'type': 'rect',
        'x': 0, 'y': status_bar_y,
        'width': DISPLAY_WIDTH, 'height': status_bar_height,
        'fill': BLACK
    })

    # Status text
    sd_status = "SD" if system_status['sd_available'] else "NOD"
    status_text = f"{sd_status} {system_status['sd_total_time']} {system_status['uptime']} {system_status['power_status']} {system_status['battery_status']}"

    elements.append({
        'type': 'text',
        'text': status_text,
        'font': 'small',
        'color': WHITE,
        'anchor_point': (0.5, 0.5),
        'anchored_position': (DISPLAY_WIDTH // 2, status_bar_y + 6)
    })

    return elements

def create_temperature_elements(temp_str, is_negative, x, y):
    """Create elements for temperature display with degree symbol"""
    elements = []
    current_x = x

    # Minus sign if negative
    if is_negative:
        elements.append({
            'type': 'text',
            'text': '-',
            'font': 'small',
            'color': '#000000',
            'x': current_x,
            'y': y
        })
        current_x += 15

    # Number
    elements.append({
        'type': 'text',
        'text': temp_str,
        'font': 'large',
        'color': '#000000',
        'x': current_x,
        'y': y
    })
    current_x += len(temp_str) * 30  # rough width estimate

    # Degree symbol (superscript)
    elements.append({
        'type': 'text',
        'text': '°',
        'font': 'small',
        'color': '#000000',
        'x': current_x,
        'y': y - 10
    })

    return elements

def create_humidity_elements(humidity_str, x, y):
    """Create elements for humidity display with percent symbol"""
    elements = []

    # Number
    elements.append({
        'type': 'text',
        'text': humidity_str,
        'font': 'large',
        'color': '#FF0000',
        'x': x,
        'y': y
    })

    # Percent symbol (baseline)
    elements.append({
        'type': 'text',
        'text': '%',
        'font': 'small',
        'color': '#FF0000',
        'x': x + len(humidity_str) * 30,  # rough width estimate
        'y': y + 15
    })

    return elements

def create_line_graph_elements(data_points, color, y_start, height):
    """Create line graph elements with thick lines and min/max labels"""
    elements = []

    if len(data_points) < 2:
        return elements

    DISPLAY_WIDTH = 122
    graph_width = DISPLAY_WIDTH
    x_step = graph_width // (len(data_points) - 1) if len(data_points) > 1 else 0

    # Normalize data to fit in height
    min_val = min(data_points)
    max_val = max(data_points)
    val_range = max_val - min_val if max_val != min_val else 1

    # Create line segments (thick lines = 2 parallel lines)
    for i in range(len(data_points) - 1):
        x1 = 10 + i * x_step
        x2 = 10 + (i + 1) * x_step

        # Scale y values
        y1 = y_start + height - int(((data_points[i] - min_val) / val_range) * height)
        y2 = y_start + height - int(((data_points[i + 1] - min_val) / val_range) * height)

        # Two parallel lines for thickness
        elements.append({
            'type': 'line',
            'x1': x1, 'y1': y1,
            'x2': x2, 'y2': y2,
            'color': color
        })
        elements.append({
            'type': 'line',
            'x1': x1, 'y1': y1 + 1,
            'x2': x2, 'y2': y2 + 1,
            'color': color
        })

    # Max label (top left)
    elements.append({
        'type': 'rect',
        'x': 0, 'y': y_start - 2,
        'width': 16, 'height': 14,
        'fill': color
    })
    elements.append({
        'type': 'text',
        'text': str(int(max_val)),
        'font': 'small',
        'color': '#FFFFFF',
        'x': 2,
        'y': y_start + 5
    })

    # Min label (bottom left)
    elements.append({
        'type': 'rect',
        'x': 0, 'y': y_start + height - 12,
        'width': 16, 'height': 14,
        'fill': color
    })
    elements.append({
        'type': 'text',
        'text': str(int(min_val)),
        'font': 'small',
        'color': '#FFFFFF',
        'x': 2,
        'y': y_start + height - 5
    })

    return elements
