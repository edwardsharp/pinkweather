"""
Batch image renderer for historical weather narratives
Generates PNG files using simple_web_render.py for each narrative in the dataset
"""

import csv
import os
import sys
from datetime import datetime

# Set environment variable to reduce logging noise
os.environ["PINKWEATHER_QUIET"] = "1"

# Add paths for imports
current_dir = os.path.dirname(os.path.abspath(__file__))  # web/static/
web_dir = os.path.dirname(current_dir)  # web/
project_root = os.path.dirname(web_dir)  # project root

# Add web directory to path for simple_web_render
if web_dir not in sys.path:
    sys.path.insert(0, web_dir)

from weather_data_converter import render_csv_record_to_image


def load_narrative_dataset(csv_path):
    """Load narrative dataset from CSV file"""
    narratives = []

    with open(csv_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            narratives.append(row)

    return narratives


def generate_filename_from_record(record):
    """Generate PNG filename from narrative record"""
    # Format: 2024-01-01-00-00.png
    date = record["date"]
    hour = record["hour"].replace(":", "-")
    return f"{date}-{hour}.png"


def render_weather_to_image(record, output_path, csv_data_list=None):
    """Render full weather display to PNG image using shared converter"""
    return render_csv_record_to_image(record, output_path, csv_data_list)


def batch_render_images(max_images=None):
    """Batch render images for narratives in dataset"""

    # Use fixed paths in same directory as script
    current_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(current_dir, "narratives.csv")
    images_dir = os.path.join(current_dir, "images")

    # Ensure images directory exists
    os.makedirs(images_dir, exist_ok=True)

    # Check if CSV exists
    if not os.path.exists(csv_path):
        print(f"Error: No narratives.csv found - run generate_historical_data.py first")
        return False

    # Load narrative data
    print(f"Loading narrative dataset from {csv_path}")
    narratives = load_narrative_dataset(csv_path)

    if not narratives:
        print("No narratives found in dataset!")
        return False

    # Limit number of images if specified
    if max_images and max_images > 0:
        narratives = narratives[:max_images]
        print(
            f"Rendering first {len(narratives)} images to {images_dir} (limited by count)"
        )
    else:
        print(f"Rendering all {len(narratives)} images to {images_dir}")

    success_count = 0

    for i, record in enumerate(narratives):
        if i % 10 == 0:
            print(f"Rendering image {i + 1}/{len(narratives)}")

        # Generate filename
        filename = generate_filename_from_record(record)
        output_path = os.path.join(images_dir, filename)

        # Always render (don't skip existing files to avoid stale images)
        if os.path.exists(output_path):
            print(f"Overwriting existing image: {filename}")

        # Render full weather display to image
        if render_weather_to_image(record, output_path, narratives):
            success_count += 1
        else:
            print(f"Failed to render: {filename}")

    print(f"\nImage rendering complete!")
    print(f"Successfully rendered: {success_count}/{len(narratives)} images")
    print(f"Images saved to: {images_dir}")

    return success_count > 0


def verify_images():
    """Verify that images exist for all narratives"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(current_dir, "narratives.csv")
    images_dir = os.path.join(current_dir, "images")

    if not os.path.exists(csv_path):
        print(f"Error: No narratives.csv found - run generate_historical_data.py first")
        return False

    narratives = load_narrative_dataset(csv_path)
    missing_images = []
    existing_images = []

    for record in narratives:
        filename = generate_filename_from_record(record)
        image_path = os.path.join(images_dir, filename)

        if os.path.exists(image_path):
            existing_images.append(filename)
        else:
            missing_images.append(filename)

    print(f"Image verification results:")
    print(f"  Existing images: {len(existing_images)}")
    print(f"  Missing images: {len(missing_images)}")

    if missing_images:
        print(f"  First few missing: {missing_images[:5]}")

    return len(missing_images) == 0


def test_single_render():
    """Test rendering a single weather display"""
    print("Testing single weather display render...")

    # Test with sample record
    test_record = {
        "timestamp": "1704067200",
        "date": "2023-12-31",
        "hour": "19:00",
        "narrative_text": "Clear and cold, 5°C. Light winds from the west.",
        "temp": "5.0",
        "weather_desc": "clear sky",
    }
    test_output = "test_render.png"

    if render_weather_to_image(test_record, test_output, None):
        print(f"Successfully rendered test image: {test_output}")

        # Check file size
        if os.path.exists(test_output):
            size = os.path.getsize(test_output)
            print(f"Test image size: {size} bytes")

        return True
    else:
        print("Failed to render test image")
        return False


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        test_single_render()
    else:
        # Check for optional count parameter
        max_count = None
        if len(sys.argv) > 1:
            try:
                max_count = int(sys.argv[1])
                print(f"Will render maximum {max_count} images")
            except ValueError:
                print(
                    f"Error: Invalid count '{sys.argv[1]}' - must be a number or 'test'"
                )
                print("Usage:")
                print("  python batch_image_renderer.py        # Render all images")
                print(
                    "  python batch_image_renderer.py 10     # Render first 10 images"
                )
                print("  python batch_image_renderer.py test   # Test single render")
                sys.exit(1)

        batch_render_images(max_count)
