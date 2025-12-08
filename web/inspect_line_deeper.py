#!/usr/bin/env python3
"""
Deeper inspection of Line object to understand how endpoints are stored
"""

import sys
import os

# Add CIRCUITPY to path
circuitpy_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'CIRCUITPY')
sys.path.insert(0, circuitpy_path)

def inspect_line_deeper():
    """Deep dive into Line object internals"""

    # Change to CIRCUITPY directory for imports
    current_dir = os.getcwd()

    try:
        os.chdir(circuitpy_path)

        from adafruit_display_shapes.line import Line
        import displayio

        # Create a test line
        print("Creating Line(10, 20, 50, 80, 0xFF0000)...")
        test_line = Line(10, 20, 50, 80, 0xFF0000)

        print(f"Line position: x={test_line.x}, y={test_line.y}")
        print(f"Bitmap size: {test_line.bitmap.width} x {test_line.bitmap.height}")

        # Check if Line class has any class variables or methods that store endpoints
        print(f"\nLine class: {Line}")
        print(f"Line MRO: {Line.__mro__}")

        # Look at Line's __init__ method to see how it processes arguments
        import inspect
        try:
            source = inspect.getsource(Line.__init__)
            print(f"\nLine.__init__ source:\n{source}")
        except:
            print("\nCould not get Line.__init__ source")

        # Check if it inherits from Polygon (which might store points)
        if hasattr(test_line, '_points') or hasattr(test_line, 'points'):
            points = getattr(test_line, '_points', None) or getattr(test_line, 'points', None)
            print(f"\nPoints: {points}")

        # Try to access the Line class itself to see what it does with endpoints
        print(f"\nLet's look at the Line class attributes:")
        for attr in dir(Line):
            if not attr.startswith('__'):
                try:
                    value = getattr(Line, attr)
                    if callable(value):
                        print(f"  {attr}: method")
                    else:
                        print(f"  {attr}: {value}")
                except:
                    pass

        # Create another line with different coordinates to compare bitmaps
        print(f"\n" + "="*50)
        print("Creating second line Line(0, 0, 30, 40, 0x00FF00)...")
        test_line2 = Line(0, 0, 30, 40, 0x00FF00)

        print(f"Line 1: pos=({test_line.x}, {test_line.y}), bitmap={test_line.bitmap.width}x{test_line.bitmap.height}")
        print(f"Line 2: pos=({test_line2.x}, {test_line2.y}), bitmap={test_line2.bitmap.width}x{test_line2.bitmap.height}")

        # Try to inspect the bitmap contents
        def print_bitmap_sample(bitmap, name):
            print(f"\n{name} bitmap sample (first 10x10):")
            for y in range(min(10, bitmap.height)):
                row = ""
                for x in range(min(10, bitmap.width)):
                    try:
                        pixel = bitmap[x, y]
                        row += "X" if pixel > 0 else "."
                    except:
                        row += "?"
                print(f"  {row}")

        print_bitmap_sample(test_line.bitmap, "Line 1")
        print_bitmap_sample(test_line2.bitmap, "Line 2")

        # Try to look at the actual Line constructor to understand parameter handling
        print(f"\n" + "="*50)
        print("Trying to understand Line constructor...")

        # Let's try creating lines with different parameters to see the pattern
        lines_data = [
            (0, 0, 10, 0),    # horizontal line
            (0, 0, 0, 10),    # vertical line
            (0, 0, 10, 10),   # diagonal line
            (5, 5, 15, 5),    # horizontal line offset
        ]

        for i, (x0, y0, x1, y1) in enumerate(lines_data):
            line = Line(x0, y0, x1, y1, 0x000000)
            print(f"Line({x0}, {y0}, {x1}, {y1}): pos=({line.x}, {line.y}), size=({line.bitmap.width}, {line.bitmap.height})")

            # The key insight: x,y should be the TOP-LEFT of the bounding box
            # and the bitmap should contain the line relative to that position
            expected_min_x = min(x0, x1)
            expected_min_y = min(y0, y1)
            expected_width = abs(x1 - x0) + 1
            expected_height = abs(y1 - y0) + 1

            print(f"  Expected: pos=({expected_min_x}, {expected_min_y}), size=({expected_width}, {expected_height})")

            # Check if our theory matches
            if line.x == expected_min_x and line.y == expected_min_y:
                print(f"  ✓ Position matches theory!")
            else:
                print(f"  ✗ Position doesn't match theory")

            if line.bitmap.width == expected_width and line.bitmap.height == expected_height:
                print(f"  ✓ Size matches theory!")
            else:
                print(f"  ✗ Size doesn't match theory")

        # Final test: can we reconstruct the line endpoints?
        print(f"\n" + "="*50)
        print("Can we reconstruct endpoints from bitmap analysis?")

        test_line3 = Line(10, 20, 50, 30, 0x000000)
        print(f"Original: Line(10, 20, 50, 30)")
        print(f"Object: pos=({test_line3.x}, {test_line3.y}), size=({test_line3.bitmap.width}, {test_line3.bitmap.height})")

        # Theory: endpoints should be relative to the bitmap origin
        # Find the actual line pixels in the bitmap
        line_pixels = []
        for y in range(test_line3.bitmap.height):
            for x in range(test_line3.bitmap.width):
                try:
                    if test_line3.bitmap[x, y] > 0:
                        line_pixels.append((x, y))
                except:
                    pass

        if line_pixels:
            print(f"Found {len(line_pixels)} line pixels")
            print(f"First few pixels: {line_pixels[:10]}")
            print(f"Last few pixels: {line_pixels[-10:]}")

            # Find start and end points (approximate)
            min_x = min(p[0] for p in line_pixels)
            max_x = max(p[0] for p in line_pixels)
            min_y = min(p[1] for p in line_pixels)
            max_y = max(p[1] for p in line_pixels)

            # Convert back to absolute coordinates
            abs_start_x = test_line3.x + min_x
            abs_start_y = test_line3.y + min_y
            abs_end_x = test_line3.x + max_x
            abs_end_y = test_line3.y + max_y

            print(f"Reconstructed endpoints: ({abs_start_x}, {abs_start_y}) -> ({abs_end_x}, {abs_end_y})")
            print(f"Original endpoints: (10, 20) -> (50, 30)")

    finally:
        os.chdir(current_dir)

if __name__ == "__main__":
    inspect_line_deeper()
