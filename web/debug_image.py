#!/usr/bin/env python3
"""
Debug script to analyze the rendered image and see what's wrong with the rendering
"""

import sys
import os
from PIL import Image

def analyze_rendered_image():
    """Analyze the test_display.png to see what went wrong"""

    image_path = "test_display.png"

    if not os.path.exists(image_path):
        print(f"Image {image_path} does not exist!")
        return

    # Load the image
    img = Image.open(image_path)

    print(f"Image info:")
    print(f"  Size: {img.size}")
    print(f"  Mode: {img.mode}")
    print(f"  Format: {img.format}")

    # Analyze the pixel colors
    pixels = img.load()
    width, height = img.size

    # Count pixel colors
    color_counts = {}
    for y in range(height):
        for x in range(width):
            pixel = pixels[x, y]
            if pixel in color_counts:
                color_counts[pixel] += 1
            else:
                color_counts[pixel] = 1

    print(f"\nColor distribution:")
    for color, count in sorted(color_counts.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / (width * height)) * 100
        print(f"  {color}: {count} pixels ({percentage:.1f}%)")

    # Check if background is actually white
    background_color = pixels[0, 0]
    print(f"\nBackground color at (0,0): {background_color}")

    # Sample some key areas
    print(f"\nSample pixels:")
    sample_points = [
        (0, 0, "top-left corner"),
        (width//2, height//2, "center"),
        (20, 25, "temp display area"),
        (50, 90, "graph area"),
        (0, height-1, "bottom-left"),
    ]

    for x, y, desc in sample_points:
        if 0 <= x < width and 0 <= y < height:
            color = pixels[x, y]
            print(f"  ({x}, {y}) {desc}: {color}")

    # Look for any non-background pixels that might be the missing content
    print(f"\nLooking for non-background pixels...")
    non_bg_pixels = []

    for y in range(height):
        for x in range(width):
            pixel = pixels[x, y]
            if pixel != background_color:
                non_bg_pixels.append((x, y, pixel))
                if len(non_bg_pixels) <= 20:  # Show first 20
                    print(f"  ({x}, {y}): {pixel}")

    print(f"Total non-background pixels: {len(non_bg_pixels)}")

    # Check specific graph areas where lines should be
    print(f"\nChecking graph line areas (y=90-120):")
    line_pixels_found = 0
    for y in range(90, min(120, height)):
        for x in range(15, min(100, width)):
            pixel = pixels[x, y]
            if pixel != background_color:
                line_pixels_found += 1
                if line_pixels_found <= 10:
                    print(f"  Line pixel at ({x}, {y}): {pixel}")

    print(f"Total line pixels in graph area: {line_pixels_found}")

    # If image is all one color, there's a rendering problem
    if len(color_counts) == 1:
        print(f"\nWARNING: Image is entirely one color ({list(color_counts.keys())[0]})!")
        print("This suggests the rendering is not working at all.")

    # Save a simple test image to verify PIL is working
    print(f"\nCreating test image to verify PIL is working...")
    test_img = Image.new('RGB', (122, 250), (255, 255, 255))
    test_pixels = test_img.load()

    # Draw some test elements
    # Red rectangle
    for y in range(10, 30):
        for x in range(10, 50):
            test_pixels[x, y] = (255, 0, 0)

    # Black line
    for x in range(20, 100):
        test_pixels[x, 100] = (0, 0, 0)

    # Blue text area
    for y in range(200, 220):
        for x in range(20, 80):
            test_pixels[x, y] = (0, 0, 255)

    test_img.save("test_pil_working.png")
    print("Saved test_pil_working.png - this should have red rect, black line, blue rect")

if __name__ == "__main__":
    analyze_rendered_image()
