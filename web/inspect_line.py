#!/usr/bin/env python3
"""
Inspect the actual Line object to find the correct attribute names
"""

import sys
import os

# Add CIRCUITPY to path
circuitpy_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'CIRCUITPY')
sys.path.insert(0, circuitpy_path)

def inspect_line_object():
    """Inspect a Line object to find the correct attributes"""

    # Change to CIRCUITPY directory for imports
    current_dir = os.getcwd()

    try:
        os.chdir(circuitpy_path)

        from adafruit_display_shapes.line import Line

        # Create a test line
        test_line = Line(10, 20, 50, 80, 0xFF0000)

        print("Line object inspection:")
        print(f"Type: {type(test_line)}")
        print(f"Dir: {dir(test_line)}")
        print()

        # Check all attributes
        for attr in dir(test_line):
            if not attr.startswith('__'):
                try:
                    value = getattr(test_line, attr)
                    print(f"{attr}: {value} (type: {type(value)})")
                except Exception as e:
                    print(f"{attr}: ERROR - {e}")

        print()
        print("Expected coordinates: (10, 20) -> (50, 80)")
        print("Expected color: 0xFF0000 (red)")

        # Try some common private attribute patterns
        private_attrs = ['_x0', '_y0', '_x1', '_y1', 'x0', 'y0', 'x1', 'y1',
                        '_start_x', '_start_y', '_end_x', '_end_y',
                        'start_x', 'start_y', 'end_x', 'end_y']

        print("\nTrying private attribute patterns:")
        for attr in private_attrs:
            try:
                value = getattr(test_line, attr)
                print(f"  {attr}: {value}")
            except AttributeError:
                pass

        # Look at the actual object's __dict__
        print(f"\nObject __dict__: {test_line.__dict__}")

        # Try to see if it has a points property or similar
        if hasattr(test_line, 'points'):
            print(f"Points: {test_line.points}")

        # Check if it has bitmap coordinates
        if hasattr(test_line, 'bitmap'):
            bitmap = test_line.bitmap
            print(f"Bitmap: {bitmap}")
            print(f"Bitmap type: {type(bitmap)}")
            if bitmap:
                print(f"Bitmap width: {bitmap.width}")
                print(f"Bitmap height: {bitmap.height}")

    finally:
        os.chdir(current_dir)

if __name__ == "__main__":
    inspect_line_object()
