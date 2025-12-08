#!/usr/bin/env python3
"""
Debug script to check color values being passed to create_line_graph
"""

import sys
import os

# Add CIRCUITPY to path
circuitpy_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'CIRCUITPY')
sys.path.insert(0, circuitpy_path)

def debug_colors():
    """Debug what colors are being passed and used"""

    # Change to CIRCUITPY directory for imports
    current_dir = os.getcwd()

    try:
        os.chdir(circuitpy_path)

        from adafruit_display_shapes.rect import Rect

        # Test color constants
        BLACK = 0x000000
        WHITE = 0xFFFFFF
        RED = 0xFF0000

        print("Color constants:")
        print(f"  BLACK = {BLACK} = {hex(BLACK)}")
        print(f"  WHITE = {WHITE} = {hex(WHITE)}")
        print(f"  RED = {RED} = {hex(RED)}")

        # Test rectangle creation with different colors
        print("\nTesting Rect creation:")

        # Test black background
        black_rect = Rect(0, 0, 16, 14, fill=BLACK)
        print(f"  Black rect.fill = {black_rect.fill} = {hex(black_rect.fill) if black_rect.fill else 'None'}")

        # Test red background
        red_rect = Rect(0, 0, 16, 14, fill=RED)
        print(f"  Red rect.fill = {red_rect.fill} = {hex(red_rect.fill) if red_rect.fill else 'None'}")

        # Test white background
        white_rect = Rect(0, 0, 16, 14, fill=WHITE)
        print(f"  White rect.fill = {white_rect.fill} = {hex(white_rect.fill) if white_rect.fill else 'None'}")

        # Test the exact create_line_graph pattern
        print("\nTesting create_line_graph pattern:")

        def test_create_line_graph_labels(color, color_name):
            print(f"\n  Testing with {color_name} = {color} = {hex(color)}")

            # This is the exact pattern from create_line_graph
            y_start = 84
            height = 32

            max_bg = Rect(0, y_start - 2, 16, 14, fill=color)
            min_bg = Rect(0, y_start + height - 12, 16, 14, fill=color)

            print(f"    max_bg.fill = {max_bg.fill} = {hex(max_bg.fill) if max_bg.fill else 'None'}")
            print(f"    min_bg.fill = {min_bg.fill} = {hex(min_bg.fill) if min_bg.fill else 'None'}")

            # Check if the color got preserved
            if max_bg.fill == color:
                print(f"    ✓ Color preserved correctly")
            else:
                print(f"    ✗ Color changed! Expected {hex(color)}, got {hex(max_bg.fill)}")

        test_create_line_graph_labels(BLACK, "BLACK")
        test_create_line_graph_labels(RED, "RED")

        # Test if there's an issue with color comparison
        print(f"\nColor comparison tests:")
        print(f"  RED == 0xFF0000: {RED == 0xFF0000}")
        print(f"  RED == 16711680: {RED == 16711680}")  # decimal equivalent
        print(f"  type(RED): {type(RED)}")

        # Test if there's an issue with the debug renderer color conversion
        def convert_displayio_color(color):
            """Copy of the debug renderer color conversion"""
            if color is None:
                return None

            if isinstance(color, int):
                r = (color >> 16) & 0xFF
                g = (color >> 8) & 0xFF
                b = color & 0xFF
                return (r, g, b)

            return color

        print(f"\nColor conversion tests:")
        print(f"  BLACK -> {convert_displayio_color(BLACK)}")
        print(f"  RED -> {convert_displayio_color(RED)}")
        print(f"  WHITE -> {convert_displayio_color(WHITE)}")

    finally:
        os.chdir(current_dir)

if __name__ == "__main__":
    debug_colors()
