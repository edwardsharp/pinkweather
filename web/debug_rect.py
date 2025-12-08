#!/usr/bin/env python3
"""
Debug script to understand how Rect fill behavior works with displayio
"""

import sys
import os

# Add CIRCUITPY to path
circuitpy_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'CIRCUITPY')
sys.path.insert(0, circuitpy_path)

def debug_rect_fill():
    """Debug how Rect handles fill parameter"""

    # Change to CIRCUITPY directory for imports
    current_dir = os.getcwd()

    try:
        os.chdir(circuitpy_path)

        from adafruit_display_shapes.rect import Rect

        # Test different Rect constructor calls
        print("Testing Rect fill behavior:")
        print("=" * 50)

        # Test 1: No fill parameter
        print("\n1. Rect with no fill parameter:")
        rect1 = Rect(0, 0, 100, 50, outline=0x000000, stroke=2)
        print(f"   rect.fill = {rect1.fill}")
        print(f"   hasattr(rect, 'fill') = {hasattr(rect1, 'fill')}")
        print(f"   rect.fill is None = {rect1.fill is None}")

        # Test 2: Explicit fill=None
        print("\n2. Rect with explicit fill=None:")
        rect2 = Rect(0, 0, 100, 50, outline=0x000000, stroke=2, fill=None)
        print(f"   rect.fill = {rect2.fill}")
        print(f"   hasattr(rect, 'fill') = {hasattr(rect2, 'fill')}")
        print(f"   rect.fill is None = {rect2.fill is None}")

        # Test 3: Explicit fill color
        print("\n3. Rect with explicit fill=WHITE:")
        rect3 = Rect(0, 0, 100, 50, outline=0x000000, stroke=2, fill=0xFFFFFF)
        print(f"   rect.fill = {rect3.fill}")
        print(f"   hasattr(rect, 'fill') = {hasattr(rect3, 'fill')}")
        print(f"   rect.fill is None = {rect3.fill is None}")

        # Test 4: Only outline, no stroke
        print("\n4. Rect with only outline, no stroke:")
        rect4 = Rect(0, 0, 100, 50, outline=0x000000)
        print(f"   rect.fill = {rect4.fill}")
        print(f"   rect.outline = {rect4.outline}")
        print(f"   hasattr(rect, 'stroke') = {hasattr(rect4, 'stroke')}")
        if hasattr(rect4, 'stroke'):
            print(f"   rect.stroke = {rect4.stroke}")

        # Test 5: Check all attributes
        print("\n5. All attributes of rect with outline+stroke:")
        rect5 = Rect(0, 0, 100, 50, outline=0xFF0000, stroke=2, fill=None)
        print("   All attributes:")
        for attr in dir(rect5):
            if not attr.startswith('__'):
                try:
                    value = getattr(rect5, attr)
                    if not callable(value):
                        print(f"     {attr}: {value}")
                except:
                    print(f"     {attr}: <error reading>")

        # Test 6: Check the Rect source/docs
        print("\n6. Rect class info:")
        print(f"   Rect class: {Rect}")
        print(f"   Rect MRO: {Rect.__mro__}")

        # Test 7: Try to understand the actual issue
        print("\n7. Understanding the issue:")
        print("   Creating rect identical to hardware graph border...")
        DISPLAY_WIDTH = 122
        temp_y_start = 84
        temp_height = 32
        BLACK = 0x000000

        # This is the exact line from the hardware code
        temp_border = Rect(0, temp_y_start - 2, DISPLAY_WIDTH, temp_height + 4, outline=BLACK, stroke=2, fill=None)

        print(f"   temp_border.fill = {temp_border.fill}")
        print(f"   temp_border.outline = {temp_border.outline}")
        print(f"   temp_border.stroke = {getattr(temp_border, 'stroke', 'NO STROKE ATTR')}")

        # Check if the issue is in how we detect transparent fill
        if temp_border.fill is None:
            print("   ✓ Fill is None - should be transparent")
        elif temp_border.fill == 0:
            print("   ⚠ Fill is 0 (black) - might be default value issue")
        else:
            print(f"   ✗ Fill is {temp_border.fill} - unexpected value")

    finally:
        os.chdir(current_dir)

if __name__ == "__main__":
    debug_rect_fill()
