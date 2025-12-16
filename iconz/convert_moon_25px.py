#!/usr/bin/env python3
"""
Convert SVG moon phase icons to 25x25px BMP format for header use
This script overwrites existing moon BMP files with 25x25px versions
"""

import os
from PIL import Image
from io import BytesIO

def convert_svg_to_bmp_with_border(svg_file, output_file, size=(25, 25)):
    """Convert SVG to BMP using cairosvg with pure black/white conversion and 1px border"""
    try:
        import cairosvg

        # Convert SVG to PNG first
        png_data = cairosvg.svg2png(url=svg_file, output_width=size[0], output_height=size[1])

        # Convert PNG data to PIL Image
        png_image = Image.open(BytesIO(png_data))

        # Convert to RGB (BMP doesn't support RGBA)
        if png_image.mode in ('RGBA', 'LA'):
            # Create white background for moon phases
            background = Image.new('RGB', png_image.size, (255, 255, 255))
            if png_image.mode == 'RGBA':
                background.paste(png_image, mask=png_image.split()[-1])
            else:
                background.paste(png_image)
            png_image = background
        elif png_image.mode != 'RGB':
            png_image = png_image.convert('RGB')

        # Force pure black/white to avoid red artifacts
        pixels = png_image.load()
        width, height = png_image.size

        # Convert to pure black and white
        for y in range(height):
            for x in range(width):
                r, g, b = pixels[x, y]
                # Calculate grayscale value
                gray = int(0.299 * r + 0.587 * g + 0.114 * b)
                # Threshold to pure black or white
                if gray > 127:
                    pixels[x, y] = (255, 255, 255)  # Pure white
                else:
                    pixels[x, y] = (0, 0, 0)        # Pure black

        # Add 1-pixel black border by replacing edge pixels
        # Top and bottom edges
        for x in range(width):
            pixels[x, 0] = (0, 0, 0)        # Top edge
            pixels[x, height-1] = (0, 0, 0)  # Bottom edge

        # Left and right edges
        for y in range(height):
            pixels[0, y] = (0, 0, 0)        # Left edge
            pixels[width-1, y] = (0, 0, 0)  # Right edge

        # Save as 24-bit BMP
        png_image.save(output_file, 'BMP')
        return True

    except ImportError:
        print("Error: cairosvg not found. Install with: pip install cairosvg")
        return False
    except Exception as e:
        print(f"Error converting {svg_file}: {e}")
        return False

def main():
    """Convert moon phase icons to 25x25px for header use"""

    # Create output directory if it doesn't exist
    os.makedirs('bmp', exist_ok=True)

    # Moon phase mappings - using only alt versions with clean names (no "alt" in output)
    moon_phases = [
        # Main moon phases (alt versions with full outline circle)
        ('wi-moon-alt-new.svg', 'moon-new.bmp'),
        ('wi-moon-alt-first-quarter.svg', 'moon-first-quarter.bmp'),
        ('wi-moon-alt-full.svg', 'moon-full.bmp'),
        ('wi-moon-alt-third-quarter.svg', 'moon-third-quarter.bmp'),

        # Waxing crescent phases (alt versions)
        ('wi-moon-alt-waxing-crescent-1.svg', 'moon-waxing-crescent-1.bmp'),
        ('wi-moon-alt-waxing-crescent-2.svg', 'moon-waxing-crescent-2.bmp'),
        ('wi-moon-alt-waxing-crescent-3.svg', 'moon-waxing-crescent-3.bmp'),
        ('wi-moon-alt-waxing-crescent-4.svg', 'moon-waxing-crescent-4.bmp'),
        ('wi-moon-alt-waxing-crescent-5.svg', 'moon-waxing-crescent-5.bmp'),
        ('wi-moon-alt-waxing-crescent-6.svg', 'moon-waxing-crescent-6.bmp'),

        # Waxing gibbous phases (alt versions)
        ('wi-moon-alt-waxing-gibbous-1.svg', 'moon-waxing-gibbous-1.bmp'),
        ('wi-moon-alt-waxing-gibbous-2.svg', 'moon-waxing-gibbous-2.bmp'),
        ('wi-moon-alt-waxing-gibbous-3.svg', 'moon-waxing-gibbous-3.bmp'),
        ('wi-moon-alt-waxing-gibbous-4.svg', 'moon-waxing-gibbous-4.bmp'),
        ('wi-moon-alt-waxing-gibbous-5.svg', 'moon-waxing-gibbous-5.bmp'),
        ('wi-moon-alt-waxing-gibbous-6.svg', 'moon-waxing-gibbous-6.bmp'),

        # Waning gibbous phases (alt versions)
        ('wi-moon-alt-waning-gibbous-1.svg', 'moon-waning-gibbous-1.bmp'),
        ('wi-moon-alt-waning-gibbous-2.svg', 'moon-waning-gibbous-2.bmp'),
        ('wi-moon-alt-waning-gibbous-3.svg', 'moon-waning-gibbous-3.bmp'),
        ('wi-moon-alt-waning-gibbous-4.svg', 'moon-waning-gibbous-4.bmp'),
        ('wi-moon-alt-waning-gibbous-5.svg', 'moon-waning-gibbous-5.bmp'),
        ('wi-moon-alt-waning-gibbous-6.svg', 'moon-waning-gibbous-6.bmp'),

        # Waning crescent phases (alt versions)
        ('wi-moon-alt-waning-crescent-1.svg', 'moon-waning-crescent-1.bmp'),
        ('wi-moon-alt-waning-crescent-2.svg', 'moon-waning-crescent-2.bmp'),
        ('wi-moon-alt-waning-crescent-3.svg', 'moon-waning-crescent-3.bmp'),
        ('wi-moon-alt-waning-crescent-4.svg', 'moon-waning-crescent-4.bmp'),
        ('wi-moon-alt-waning-crescent-5.svg', 'moon-waning-crescent-5.bmp'),
        ('wi-moon-alt-waning-crescent-6.svg', 'moon-waning-crescent-6.bmp'),

        # Special moon phases
        ('wi-moonrise.svg', 'moonrise.bmp'),
        ('wi-moonset.svg', 'moonset.bmp'),
        ('wi-lunar-eclipse.svg', 'lunar-eclipse.bmp'),
    ]

    print("Converting alt moon phase icons to 25x25px with clean names...")
    print("Using alt versions (with full moon outline circle)")
    print("")

    converted = 0
    failed = 0
    missing = 0

    for svg_file, bmp_name in moon_phases:
        if not os.path.exists(svg_file):
            print(f"Skipping missing: {svg_file}")
            missing += 1
            continue

        output_file = f"bmp/{bmp_name}"
        print(f"Converting {svg_file} -> {bmp_name} (25x25px)")

        if convert_svg_to_bmp_with_border(svg_file, output_file, size=(25, 25)):
            converted += 1
        else:
            failed += 1

    print(f"\nConversion complete!")
    print(f"Successfully converted: {converted}")
    print(f"Failed conversions: {failed}")
    print(f"Missing SVG files: {missing}")

    # List what was created
    if converted > 0:
        print(f"\nCreated moon phase BMP files in bmp/ with 25x25px versions:")
        bmp_files = sorted([f for f in os.listdir('bmp') if f.startswith('moon') or f in ['moonrise.bmp', 'moonset.bmp', 'lunar-eclipse.bmp']])
        for bmp_file in bmp_files:
            print(f"  {bmp_file} (25x25px)")

        print(f"\nThese icons use alt versions with full moon outline circle.")
        print(f"Sized for the 25px tall header - use in CircuitPython header display code.")

if __name__ == '__main__':
    main()
