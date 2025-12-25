"""
Simple converter that uses shared weather engine for CSV record processing
No more custom logic - just calls to working shared functions
"""

import os
import sys


def add_web_path():
    """Add web directory to path for imports"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    web_dir = os.path.dirname(current_dir)
    if web_dir not in sys.path:
        sys.path.insert(0, web_dir)


def render_csv_record_to_image(record, output_path, csv_data_list=None):
    """
    Render CSV record to weather display image using shared engine

    Args:
        record: Dict from CSV with timestamp, narrative_text, etc.
        output_path: Path to save PNG file
        csv_data_list: Not used - engine finds its own historical data

    Returns:
        bool: Success/failure
    """
    try:
        add_web_path()
        from shared_weather_engine import generate_complete_weather_display

        # Get CSV path (shared engine handles loading historical data)
        csv_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "misc",
            "open-meteo-40.65N73.98W25m.csv",
        )

        timestamp = int(record["timestamp"])

        # Use shared engine to generate image - this gives us the same output as web server
        image, narrative, metrics = generate_complete_weather_display(
            csv_path, timestamp
        )

        # Save image
        image.save(output_path, "PNG")
        return True

    except Exception as e:
        print(f"Error rendering {output_path}: {e}")
        return False
