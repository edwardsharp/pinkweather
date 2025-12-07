"""
Debug script to compare display elements between hardware positioning and shared logic
Run this to see what elements are being generated and compare positioning
"""

import sys
import os
import time

# Add paths for imports
sys.path.append('CIRCUITPY')
sys.path.append('web')

from display_logic import create_display_layout
from web_adapter import get_mock_sensor_data, get_mock_csv_data, get_mock_historical_data, get_mock_system_status

def print_elements(elements, title):
    """Print display elements in a readable format"""
    print(f"\n=== {title} ===")
    for i, element in enumerate(elements):
        print(f"{i:2d}: {element}")

def debug_shared_logic():
    """Test the shared display logic and show what it generates"""
    print("Testing shared display logic...")

    # Get mock data
    sensor_data = get_mock_sensor_data()
    csv_data = get_mock_csv_data('normal')
    historical_data = get_mock_historical_data(csv_data)
    system_status = get_mock_system_status('normal')

    print(f"Sensor data: {sensor_data}")
    print(f"System status: {system_status}")
    print(f"Historical averages: {historical_data['temp_averages']}, {historical_data['humidity_averages']}")

    # Generate display elements
    elements = create_display_layout(sensor_data, historical_data, system_status)

    # Print all elements
    print_elements(elements, "SHARED LOGIC ELEMENTS")

    # Group by type
    rects = [e for e in elements if e['type'] == 'rect']
    texts = [e for e in elements if e['type'] == 'text']
    lines = [e for e in elements if e['type'] == 'line']

    print(f"\nSummary: {len(rects)} rects, {len(texts)} texts, {len(lines)} lines")

    print("\n=== RECTANGLES ===")
    for i, rect in enumerate(rects):
        if 'fill' in rect:
            print(f"  {i}: Fill rect at ({rect['x']}, {rect['y']}) size {rect['width']}x{rect['height']} color {rect['fill']}")
        if 'outline' in rect:
            print(f"  {i}: Border rect at ({rect['x']}, {rect['y']}) size {rect['width']}x{rect['height']} color {rect['outline']} stroke {rect.get('stroke', 1)}")

    print("\n=== TEXT ELEMENTS ===")
    for i, text in enumerate(texts):
        pos_info = ""
        if 'anchored_position' in text:
            anchor = text.get('anchor_point', (0, 0))
            pos_info = f"anchored at {text['anchored_position']} (anchor {anchor})"
        else:
            pos_info = f"at ({text.get('x', '?')}, {text.get('y', '?')})"

        print(f"  {i}: '{text['text']}' font={text['font']} color={text['color']} {pos_info}")

def debug_hardware_positioning():
    """Show the key positioning values from hardware code"""
    print("\n=== HARDWARE POSITIONING (from code.py) ===")

    DISPLAY_WIDTH = 122
    DISPLAY_HEIGHT = 250

    print(f"Display size: {DISPLAY_WIDTH}x{DISPLAY_HEIGHT}")
    print(f"Current temp: x=20, y=25")
    print(f"Temp averages: centered at y=75")

    temp_y_start = 84
    temp_height = 32
    print(f"Temp graph: border at (0, {temp_y_start-2}) size {DISPLAY_WIDTH}x{temp_height+4}")
    print(f"Temp graph: data area at y={temp_y_start}, height={temp_height}")

    humidity_y_start = 124
    humidity_height = 32
    print(f"Humidity graph: border at (0, {humidity_y_start-2}) size {DISPLAY_WIDTH}x{humidity_height+4}")
    print(f"Humidity graph: data area at y={humidity_y_start}, height={humidity_height}")

    print(f"Humidity averages: centered at y={humidity_y_start + humidity_height + 10}")
    print(f"Current humidity: x=20, y={humidity_y_start + humidity_height + 38}")

    status_bar_height = 12
    status_bar_y = DISPLAY_HEIGHT - status_bar_height
    print(f"Status bar: at (0, {status_bar_y}) size {DISPLAY_WIDTH}x{status_bar_height}")
    print(f"Status text: centered at y={status_bar_y + 6}")

def compare_positioning():
    """Compare key positions between hardware and shared logic"""
    print("\n=== POSITION COMPARISON ===")

    # Hardware values
    hw_temp_y = 25
    hw_temp_avg_y = 75
    hw_temp_graph_y = 84
    hw_humidity_graph_y = 124
    hw_humidity_avg_y = 124 + 32 + 10  # 166
    hw_humidity_y = 124 + 32 + 38       # 194
    hw_status_y = 250 - 12 + 6          # 244

    print("Hardware positions:")
    print(f"  Temp display: y={hw_temp_y}")
    print(f"  Temp averages: y={hw_temp_avg_y}")
    print(f"  Temp graph: y={hw_temp_graph_y}")
    print(f"  Humidity graph: y={hw_humidity_graph_y}")
    print(f"  Humidity averages: y={hw_humidity_avg_y}")
    print(f"  Humidity display: y={hw_humidity_y}")
    print(f"  Status text: y={hw_status_y}")

    # Now check shared logic
    sensor_data = {'temp_c': 22.5, 'humidity': 45.0}
    csv_data = get_mock_csv_data('normal')
    historical_data = get_mock_historical_data(csv_data)
    system_status = get_mock_system_status('normal')
    elements = create_display_layout(sensor_data, historical_data, system_status)

    print("\nShared logic positions:")
    for element in elements:
        if element['type'] == 'text':
            if 'anchored_position' in element:
                x, y = element['anchored_position']
                text = element['text'][:20] + ('...' if len(element['text']) > 20 else '')
                print(f"  '{text}': anchored at y={y}")
            elif 'y' in element:
                text = element['text'][:20] + ('...' if len(element['text']) > 20 else '')
                print(f"  '{text}': y={element['y']}")

if __name__ == "__main__":
    print("PinkWeather Display Layout Debug Tool")
    print("=" * 50)

    debug_hardware_positioning()
    debug_shared_logic()
    compare_positioning()

    print("\n" + "=" * 50)
    print("Run this script to debug positioning differences between hardware and web display")
