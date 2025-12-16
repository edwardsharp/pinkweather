#!/usr/bin/env python3
"""
Convert SVG weather icons to BMP format with borders
Generates 50x50 weather icons with 1px black borders (no postfix)
"""

import os
from PIL import Image
from io import BytesIO

def convert_svg_to_bmp_with_border(svg_file, output_file, size=(64, 64)):
    """Convert SVG to BMP using cairosvg with pure black/white conversion and 1px border"""
    try:
        import cairosvg

        # Convert SVG to PNG first
        png_data = cairosvg.svg2png(url=svg_file, output_width=size[0], output_height=size[1])

        # Convert PNG data to PIL Image
        png_image = Image.open(BytesIO(png_data))

        # Convert to RGB (BMP doesn't support RGBA)
        if png_image.mode in ('RGBA', 'LA'):
            # Create white background
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
    """Convert weather icons with pixel-based naming"""

    # Create output directory
    os.makedirs('bmp', exist_ok=True)

    # Manual mappings: (svg_filename, openweather_code_day, openweather_code_night)
    # Based on OpenWeather API documentation and common weather icons
    icon_mappings = [
        # Clear sky
        ('wi-day-sunny.svg', '01d'),
        ('wi-night-clear.svg', '01n'),

        # Few clouds
        ('wi-day-cloudy.svg', '02d'),
        ('wi-night-alt-cloudy.svg', '02n'),

        # Scattered clouds
        ('wi-cloudy.svg', '03d'),
        ('wi-cloudy.svg', '03n'),  # Same icon for day/night

        # Broken clouds
        ('wi-day-cloudy.svg', '04d'),
        ('wi-night-alt-cloudy.svg', '04n'),

        # Shower rain
        ('wi-day-showers.svg', '09d'),
        ('wi-night-alt-showers.svg', '09n'),

        # Rain
        ('wi-day-rain.svg', '10d'),
        ('wi-night-alt-rain.svg', '10n'),

        # Thunderstorm
        ('wi-day-thunderstorm.svg', '11d'),
        ('wi-night-alt-thunderstorm.svg', '11n'),

        # Snow
        ('wi-day-snow.svg', '13d'),
        ('wi-night-alt-snow.svg', '13n'),

        # Mist
        ('wi-day-fog.svg', '50d'),
        ('wi-night-fog.svg', '50n'),

        # Additional common codes
        # Thunderstorm variations (all use 11d/11n icons)
        ('wi-day-thunderstorm.svg', '200d'),
        ('wi-night-alt-thunderstorm.svg', '200n'),
        ('wi-day-thunderstorm.svg', '201d'),
        ('wi-night-alt-thunderstorm.svg', '201n'),
        ('wi-day-thunderstorm.svg', '202d'),
        ('wi-night-alt-thunderstorm.svg', '202n'),
        ('wi-day-thunderstorm.svg', '210d'),
        ('wi-night-alt-thunderstorm.svg', '210n'),
        ('wi-day-thunderstorm.svg', '211d'),
        ('wi-night-alt-thunderstorm.svg', '211n'),
        ('wi-day-thunderstorm.svg', '212d'),
        ('wi-night-alt-thunderstorm.svg', '212n'),
        ('wi-day-thunderstorm.svg', '221d'),
        ('wi-night-alt-thunderstorm.svg', '221n'),
        ('wi-day-thunderstorm.svg', '230d'),
        ('wi-night-alt-thunderstorm.svg', '230n'),
        ('wi-day-thunderstorm.svg', '231d'),
        ('wi-night-alt-thunderstorm.svg', '231n'),
        ('wi-day-thunderstorm.svg', '232d'),
        ('wi-night-alt-thunderstorm.svg', '232n'),

        # Drizzle (use shower/sprinkle icons)
        ('wi-day-sprinkle.svg', '300d'),
        ('wi-night-alt-sprinkle.svg', '300n'),
        ('wi-day-sprinkle.svg', '301d'),
        ('wi-night-alt-sprinkle.svg', '301n'),
        ('wi-day-showers.svg', '302d'),
        ('wi-night-alt-showers.svg', '302n'),
        ('wi-day-showers.svg', '310d'),
        ('wi-night-alt-showers.svg', '310n'),
        ('wi-day-showers.svg', '311d'),
        ('wi-night-alt-showers.svg', '311n'),
        ('wi-day-showers.svg', '312d'),
        ('wi-night-alt-showers.svg', '312n'),
        ('wi-day-showers.svg', '313d'),
        ('wi-night-alt-showers.svg', '313n'),
        ('wi-day-showers.svg', '314d'),
        ('wi-night-alt-showers.svg', '314n'),
        ('wi-day-sprinkle.svg', '321d'),
        ('wi-night-alt-sprinkle.svg', '321n'),

        # Rain variations
        ('wi-day-sprinkle.svg', '500d'),
        ('wi-night-alt-sprinkle.svg', '500n'),
        ('wi-day-rain.svg', '501d'),
        ('wi-night-alt-rain.svg', '501n'),
        ('wi-day-rain.svg', '502d'),
        ('wi-night-alt-rain.svg', '502n'),
        ('wi-day-rain.svg', '503d'),
        ('wi-night-alt-rain.svg', '503n'),
        ('wi-day-rain.svg', '504d'),
        ('wi-night-alt-rain.svg', '504n'),
        ('wi-day-sleet.svg', '511d'),
        ('wi-night-alt-sleet.svg', '511n'),
        ('wi-day-showers.svg', '520d'),
        ('wi-night-alt-showers.svg', '520n'),
        ('wi-day-showers.svg', '521d'),
        ('wi-night-alt-showers.svg', '521n'),
        ('wi-day-showers.svg', '522d'),
        ('wi-night-alt-showers.svg', '522n'),
        ('wi-day-storm-showers.svg', '531d'),
        ('wi-night-alt-storm-showers.svg', '531n'),

        # Snow variations
        ('wi-day-snow.svg', '600d'),
        ('wi-night-alt-snow.svg', '600n'),
        ('wi-day-snow.svg', '601d'),
        ('wi-night-alt-snow.svg', '601n'),
        ('wi-day-snow.svg', '602d'),
        ('wi-night-alt-snow.svg', '602n'),
        ('wi-day-sleet.svg', '611d'),
        ('wi-night-alt-sleet.svg', '611n'),
        ('wi-day-sleet.svg', '612d'),
        ('wi-night-alt-sleet.svg', '612n'),
        ('wi-day-sleet.svg', '613d'),
        ('wi-night-alt-sleet.svg', '613n'),
        ('wi-day-rain-mix.svg', '615d'),
        ('wi-night-alt-rain-mix.svg', '615n'),
        ('wi-day-rain-mix.svg', '616d'),
        ('wi-night-alt-rain-mix.svg', '616n'),
        ('wi-day-snow.svg', '620d'),
        ('wi-night-alt-snow.svg', '620n'),
        ('wi-day-snow.svg', '621d'),
        ('wi-night-alt-snow.svg', '621n'),
        ('wi-day-snow.svg', '622d'),
        ('wi-night-alt-snow.svg', '622n'),

        # Atmosphere
        ('wi-day-fog.svg', '701d'),
        ('wi-night-fog.svg', '701n'),
        ('wi-smoke.svg', '711d'),
        ('wi-smoke.svg', '711n'),
        ('wi-day-haze.svg', '721d'),
        ('wi-night-fog.svg', '721n'),
        ('wi-dust.svg', '731d'),
        ('wi-dust.svg', '731n'),
        ('wi-day-fog.svg', '741d'),
        ('wi-night-fog.svg', '741n'),
        ('wi-dust.svg', '751d'),
        ('wi-dust.svg', '751n'),
        ('wi-dust.svg', '761d'),
        ('wi-dust.svg', '761n'),
        ('wi-volcano.svg', '762d'),
        ('wi-volcano.svg', '762n'),
        ('wi-strong-wind.svg', '771d'),
        ('wi-strong-wind.svg', '771n'),
        ('wi-tornado.svg', '781d'),
        ('wi-tornado.svg', '781n'),

        # Clear (800)
        ('wi-day-sunny.svg', '800d'),
        ('wi-night-clear.svg', '800n'),

        # Clouds variations
        ('wi-day-cloudy.svg', '801d'),
        ('wi-night-alt-cloudy.svg', '801n'),
        ('wi-day-cloudy.svg', '802d'),
        ('wi-night-alt-cloudy.svg', '802n'),
        ('wi-day-cloudy.svg', '803d'),
        ('wi-night-alt-cloudy.svg', '803n'),
        ('wi-cloudy.svg', '804d'),
        ('wi-cloudy.svg', '804n'),

        # Special icons (sun/moon rise/set)
        ('wi-sunrise.svg', 'sunrise'),
        ('wi-sunset.svg', 'sunset'),
        ('wi-moonrise.svg', 'moonrise'),
        ('wi-moonset.svg', 'moonset'),
    ]

    print("Converting weather icons to 50x50 with borders...")

    # Single size: 50x50 with no suffix
    icon_size = (50, 50)

    converted = 0
    failed = 0
    missing = 0

    for svg_file, weather_code in icon_mappings:
        if not os.path.exists(svg_file):
            print(f"Missing SVG: {svg_file}")
            missing += 1
            continue

        # Generate single 50x50 version with no suffix
        output_file = f"bmp/{weather_code}.bmp"

        print(f"Converting {svg_file} -> {weather_code}.bmp (50x50)")

        if convert_svg_to_bmp_with_border(svg_file, output_file, icon_size):
            converted += 1
        else:
            failed += 1

    print(f"\nConversion complete!")
    print(f"Successfully converted: {converted}")
    print(f"Failed conversions: {failed}")
    print(f"Missing SVG files: {missing}")

    # List what was created
    if converted > 0:
        print(f"\nCreated BMP files in bmp/:")
        bmp_files = sorted([f for f in os.listdir('bmp') if f.endswith('.bmp')])
        print(f"Total files: {len(bmp_files)}")

        # Show examples
        print(f"\nExamples:")
        for i, bmp_file in enumerate(bmp_files[:6]):
            print(f"  {bmp_file}")
        if len(bmp_files) > 6:
            print(f"  ... and {len(bmp_files) - 6} more")

        print(f"\nExample usage in CircuitPython:")
        example_file = next((f for f in bmp_files if '01d.bmp' in f), bmp_files[0])
        print(f'pic = displayio.OnDiskBitmap("{example_file}")')
        print(f't = displayio.TileGrid(pic, pixel_shader=pic.pixel_shader)')

if __name__ == '__main__':
    main()
