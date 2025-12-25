"""
Batch image renderer for historical weather narratives
Simple script that loads narrative CSV and generates images using shared engine
"""

import csv
import os
import sys


def load_narrative_timestamps(csv_path):
    """Load timestamps from narrative CSV file"""
    timestamps = []

    with open(csv_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            timestamps.append(int(row["timestamp"]))

    return timestamps


def generate_filename_from_timestamp(timestamp):
    """Generate PNG filename from timestamp"""
    from datetime import datetime

    dt = datetime.fromtimestamp(timestamp)
    # Format: 2024-01-01-00-00.png
    return f"{dt.strftime('%Y-%m-%d-%H-%M')}.png"


def batch_render_images(max_images=None):
    """Batch render images using shared weather engine"""

    # Fixed paths
    current_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(current_dir, "narratives.csv")
    images_dir = os.path.join(current_dir, "images")
    weather_csv_path = os.path.join(
        current_dir, "..", "..", "misc", "open-meteo-40.65N73.98W25m.csv"
    )

    # Ensure images directory exists
    os.makedirs(images_dir, exist_ok=True)

    # Check if CSV exists
    if not os.path.exists(csv_path):
        print(f"Error: No narratives.csv found - run generate_historical_data.py first")
        return False

    # Load timestamps from narrative dataset
    print(f"Loading timestamps from {csv_path}")
    timestamps = load_narrative_timestamps(csv_path)

    if not timestamps:
        print("No timestamps found in dataset!")
        return False

    # Limit number of images if specified
    if max_images and max_images > 0:
        timestamps = timestamps[:max_images]
        print(
            f"Rendering first {len(timestamps)} images to {images_dir} (limited by count)"
        )
    else:
        print(f"Rendering all {len(timestamps)} images to {images_dir}")

    # Add web path for shared engine
    web_dir = os.path.dirname(current_dir)
    if web_dir not in sys.path:
        sys.path.insert(0, web_dir)

    from shared_weather_engine import generate_complete_weather_display

    success_count = 0

    for i, timestamp in enumerate(timestamps):
        if i % 10 == 0:
            print(f"Rendering image {i + 1}/{len(timestamps)}")

        filename = generate_filename_from_timestamp(timestamp)
        output_path = os.path.join(images_dir, filename)

        try:
            # Use shared engine - same as web server and dataset generation
            image, narrative, metrics = generate_complete_weather_display(
                weather_csv_path, timestamp
            )

            # Save image
            image.save(output_path, "PNG")
            success_count += 1

        except Exception as e:
            print(f"Failed to render {filename}: {e}")

    print(f"\nImage rendering complete!")
    print(f"Successfully rendered: {success_count}/{len(timestamps)} images")
    print(f"Images saved to: {images_dir}")

    return success_count > 0


def verify_images():
    """Verify that images exist for all narratives"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(current_dir, "narratives.csv")
    images_dir = os.path.join(current_dir, "images")

    if not os.path.exists(csv_path):
        print(f"Error: No narratives.csv found")
        return False

    timestamps = load_narrative_timestamps(csv_path)
    missing_images = []
    existing_images = []

    for timestamp in timestamps:
        filename = generate_filename_from_timestamp(timestamp)
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


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # Simple test - just try to render first image
        current_dir = os.path.dirname(os.path.abspath(__file__))
        csv_path = os.path.join(current_dir, "narratives.csv")

        if os.path.exists(csv_path):
            timestamps = load_narrative_timestamps(csv_path)
            if timestamps:
                batch_render_images(max_images=1)
            else:
                print("No timestamps found for testing")
        else:
            print("No narratives.csv found for testing")
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
