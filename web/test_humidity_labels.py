#!/usr/bin/env python3
"""
Test specifically the humidity graph min/max label colors
"""

import sys
import os

# Add CIRCUITPY to path
circuitpy_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'CIRCUITPY')
sys.path.insert(0, circuitpy_path)

from debug_renderer import render_displayio_group_to_image

def test_humidity_labels():
    """Test that humidity graph labels have red backgrounds"""

    # Change to CIRCUITPY directory for font loading
    current_dir = os.getcwd()

    try:
        os.chdir(circuitpy_path)

        # Import exact same modules as hardware
        import displayio
        import terminalio
        from adafruit_display_text import label
        from adafruit_display_shapes.rect import Rect

        # Constants
        BLACK = 0x000000
        WHITE = 0xFFFFFF
        RED = 0xFF0000
        DISPLAY_WIDTH = 122
        DISPLAY_HEIGHT = 250

        def create_line_graph(data_points, color, y_start, height):
            """Simplified line graph creation focusing on min/max labels"""
            if len(data_points) < 2:
                return displayio.Group()

            group = displayio.Group()

            min_val = min(data_points)
            max_val = max(data_points)

            print(f"Creating line graph:")
            print(f"  color = {color} = {hex(color)}")
            print(f"  min_val = {min_val}, max_val = {max_val}")
            print(f"  y_start = {y_start}, height = {height}")

            # Add min/max labels with colored backgrounds - EXACT same code as hardware
            # Max label (top left)
            max_bg = Rect(0, y_start - 2, 22, 14, fill=color, outline=color)  # Made wider so we can see it
            group.append(max_bg)
            print(f"  max_bg.fill = {max_bg.fill} = {hex(max_bg.fill) if max_bg.fill else 'None'}")
            print(f"  max_bg.outline = {max_bg.outline} = {hex(max_bg.outline) if max_bg.outline else 'None'}")

            max_label = label.Label(terminalio.FONT, text=f"{int(max_val)}", color=WHITE)
            max_label.x = 2
            max_label.y = y_start + 5
            group.append(max_label)

            # Min label (bottom left)
            min_bg = Rect(0, y_start + height - 12, 22, 14, fill=color, outline=color)  # Made wider so we can see it
            group.append(min_bg)
            print(f"  min_bg.fill = {min_bg.fill} = {hex(min_bg.fill) if min_bg.fill else 'None'}")
            print(f"  min_bg.outline = {min_bg.outline} = {hex(min_bg.outline) if min_bg.outline else 'None'}")

            min_label = label.Label(terminalio.FONT, text=f"{int(min_val)}", color=WHITE)
            min_label.x = 2
            min_label.y = y_start + height - 5
            group.append(min_label)

            return group

        # Create test display
        g = displayio.Group()

        # Background
        bg = Rect(0, 0, DISPLAY_WIDTH, DISPLAY_HEIGHT, fill=WHITE)
        g.append(bg)

        # Test data
        temp_data = [18, 22, 25, 23, 20]
        humidity_data = [40, 55, 60, 45, 50]

        print("\n=== TEMPERATURE GRAPH (should be BLACK labels) ===")
        # Temperature graph
        temp_y_start = 50
        temp_height = 40
        temp_border = Rect(0, temp_y_start - 2, DISPLAY_WIDTH, temp_height + 4, outline=BLACK, stroke=2, fill=WHITE)
        g.append(temp_border)
        temp_graph = create_line_graph(temp_data, BLACK, temp_y_start, temp_height)
        g.append(temp_graph)

        print("\n=== HUMIDITY GRAPH (should be RED labels) ===")
        # Humidity graph
        humidity_y_start = 120
        humidity_height = 40
        humidity_border = Rect(0, humidity_y_start - 2, DISPLAY_WIDTH, humidity_height + 4, outline=RED, stroke=2, fill=WHITE)
        g.append(humidity_border)
        humidity_graph = create_line_graph(humidity_data, RED, humidity_y_start, humidity_height)
        g.append(humidity_graph)

        print(f"\nTotal items in group: {len(g)}")
        for i, item in enumerate(g):
            if hasattr(item, 'fill'):
                print(f"  Item {i}: {type(item).__name__} fill={item.fill} outline={getattr(item, 'outline', 'N/A')}")
            else:
                print(f"  Item {i}: {type(item).__name__}")

    finally:
        os.chdir(current_dir)

    # Render to image
    print("\nRendering to image...")
    image = render_displayio_group_to_image(g, debug=True)
    image.save("humidity_labels_test.png")

    print("\nSUCCESS! Check humidity_labels_test.png")
    print("Expected:")
    print("  - Temperature labels (top): BLACK backgrounds")
    print("  - Humidity labels (bottom): RED backgrounds")

if __name__ == "__main__":
    test_humidity_labels()
