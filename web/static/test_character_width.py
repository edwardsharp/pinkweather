#!/usr/bin/env python3
"""
Narrative overflow testing script to measure actual display capacity
Generates test images with realistic narrative structures to find real limits
"""

import os
import sys
from datetime import datetime

# Add paths for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
web_dir = os.path.dirname(current_dir)
if web_dir not in sys.path:
    sys.path.insert(0, web_dir)

# Import shared engine
from shared_weather_engine import generate_weather_display_for_timestamp


def test_narrative_overflow():
    """Test realistic narrative overflow with just two test cases for iteration"""

    # Get a sample timestamp and CSV path for testing
    from generate_historical_data import load_csv_timestamps

    timestamps, csv_file_path = load_csv_timestamps()
    test_timestamp = timestamps[0]  # Use first timestamp

    # Generate base weather data for structure
    weather_data, original_narrative, display_vars, current_weather = (
        generate_weather_display_for_timestamp(csv_file_path, test_timestamp)
    )

    # Two test cases - adjust these character counts as needed
    import re

    # Test case 1: Known short narrative that should fit
    short_narrative = "Overcast and cold, <h>4</h>° (<i>feels like</i> <h>1</h>°). <b>Tomorrow:</b> rain expected, high <h>7</h>° low <h>3</h>°."

    # Test case 2: Longer narrative that might overflow - adjust this length
    long_narrative = "Currently overcast and cold with thick gray clouds covering the area. Temperature is <h>4</h>° (<i>feels like</i> <h>1</h>°) making it quite chilly outside. Light winds from the west at about 5 mph. <b>Tomorrow:</b> rain expected, high <h>7</h>° low <h>3</h>°. The barometric pressure is steady and humidity levels are moderate. This weather pattern suggests a stable system moving through the area."

    test_narratives = [("short", short_narrative), ("long", long_narrative)]

    for desc, narrative in test_narratives:
        plain_text = re.sub(r"<[^>]+>", "", narrative)
        plain_char_count = len(plain_text)

        print(f"\nTesting {desc} narrative:")
        print(f"  Plain text characters: {plain_char_count}")
        print(f"  Preview: {plain_text[:80]}{'...' if len(plain_text) > 80 else ''}")

        try:
            # Generate image using the shared engine
            from shared_weather_engine import render_weather_to_image

            image = render_weather_to_image(
                weather_data, narrative, display_vars, current_weather
            )

            # Save test image
            test_filename = f"test_{desc}_{plain_char_count}_chars.png"
            test_path = os.path.join(current_dir, "test_images", test_filename)
            os.makedirs(os.path.dirname(test_path), exist_ok=True)
            image.save(test_path)

            print(f"  Generated: {test_filename}")

        except Exception as e:
            print(f"  ERROR: {e}")

    print(f"\n" + "=" * 60)
    print("Next steps:")
    print("1. Open test_images/ directory and examine the two images")
    print("2. If both fit, increase the long_narrative length in this script")
    print("3. If the long one overflows, try a shorter version")
    print("4. Iterate until you find the exact overflow point")
    print("5. Use that character count for fits_display calibration")


if __name__ == "__main__":
    print("Narrative Overflow Testing")
    print(
        "This will generate test images with realistic narratives to measure actual display capacity"
    )
    print("-" * 80)

    try:
        test_narrative_overflow()
    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
