#!/usr/bin/env python3
"""
Test script to render the exact hardware display output to an image for debugging.
This uses the same shared code as the hardware but saves the result as a PNG.
"""

import sys
import os

# Add CIRCUITPY to path
circuitpy_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'CIRCUITPY')
sys.path.insert(0, circuitpy_path)

from debug_renderer import save_debug_image


def test_hardware_display_render():
    """Test rendering hardware display to image"""

    # Change to CIRCUITPY directory for font loading
    current_dir = os.getcwd()

    try:
        os.chdir(circuitpy_path)

        # Import exact same modules as hardware
        import displayio
        import terminalio
        from adafruit_display_text import label
        from adafruit_bitmap_font import bitmap_font
        from adafruit_display_shapes.rect import Rect
        from adafruit_display_shapes.line import Line

        # Load fonts exactly like hardware
        font = bitmap_font.load_font("barlowcond60.pcf")
        small_font = bitmap_font.load_font("barlowcond30.pcf")

        # Constants exactly like hardware
        BLACK = 0x000000
        WHITE = 0xFFFFFF
        RED = 0xFF0000
        DISPLAY_WIDTH = 122
        DISPLAY_HEIGHT = 250

        # Create test display group using exact hardware functions
        def create_test_display():
            g = displayio.Group()

            # Background
            bg = Rect(0, 0, DISPLAY_WIDTH, DISPLAY_HEIGHT, fill=WHITE)
            g.append(bg)

            # Test temperature display
            temp_str = "23"
            temp_group = displayio.Group()
            number = label.Label(font, text=temp_str, color=BLACK)
            number.x = 0
            number.y = 0
            temp_group.append(number)

            degree = label.Label(small_font, text="°", color=BLACK)
            degree.x = len(temp_str) * 30 + 6
            degree.y = -10
            temp_group.append(degree)

            temp_group.x = 20
            temp_group.y = 25
            g.append(temp_group)

            # Test line graph - this is where the issue likely is
            print("Creating test line graph...")
            graph_group = displayio.Group()

            # Graph border
            border = Rect(10, 80, 100, 40, outline=BLACK, stroke=2)
            graph_group.append(border)

            # Test data points
            test_data = [20, 25, 22, 28, 24, 26, 23, 21]
            y_start = 82
            height = 36

            # Create lines between points
            for i in range(len(test_data) - 1):
                x1 = 15 + i * 12
                x2 = 15 + (i + 1) * 12

                # Simple linear mapping for test
                y1 = y_start + height - (test_data[i] - 20) * 3
                y2 = y_start + height - (test_data[i + 1] - 20) * 3

                print(f"Line {i}: ({x1}, {y1}) -> ({x2}, {y2})")

                # Create line - this is the critical part
                line = Line(x1, y1, x2, y2, BLACK)
                graph_group.append(line)

                # Thick line (second line offset by 1)
                line2 = Line(x1, y1 + 1, x2, y2 + 1, BLACK)
                graph_group.append(line2)

            # Min/max labels with backgrounds
            max_bg = Rect(12, y_start - 2, 16, 14, fill=BLACK)
            graph_group.append(max_bg)
            max_label = label.Label(terminalio.FONT, text="28", color=WHITE)
            max_label.x = 14
            max_label.y = y_start + 5
            graph_group.append(max_label)

            min_bg = Rect(12, y_start + height - 12, 16, 14, fill=BLACK)
            graph_group.append(min_bg)
            min_label = label.Label(terminalio.FONT, text="20", color=WHITE)
            min_label.x = 14
            min_label.y = y_start + height - 5
            graph_group.append(min_label)

            g.append(graph_group)

            # Test humidity display in red
            humidity_group = displayio.Group()
            humidity_num = label.Label(font, text="65", color=RED)
            humidity_num.x = 0
            humidity_num.y = 0
            humidity_group.append(humidity_num)

            percent = label.Label(small_font, text="%", color=RED)
            percent.x = 2 * 30 + 4
            percent.y = 15
            humidity_group.append(percent)

            humidity_group.x = 20
            humidity_group.y = 180
            g.append(humidity_group)

            # Status bar
            status_bar = Rect(0, DISPLAY_HEIGHT - 12, DISPLAY_WIDTH, 12, fill=BLACK)
            g.append(status_bar)

            status_label = label.Label(terminalio.FONT, text="SD 2d 1h P B--", color=WHITE)
            status_label.anchor_point = (0.5, 0.5)
            status_label.anchored_position = (DISPLAY_WIDTH // 2, DISPLAY_HEIGHT - 6)
            g.append(status_label)

            return g

        # Create the display group
        print("Creating display group...")
        display_group = create_test_display()

        print(f"Created group with {len(display_group)} items")

    finally:
        os.chdir(current_dir)

    # Now render to image for debugging
    print("Rendering to image...")
    image = save_debug_image(display_group, "test_display.png", debug=True)

    print("Done! Check test_display.png to see the result.")
    return image


if __name__ == "__main__":
    test_hardware_display_render()
