"""
Batch image renderer for historical weather narratives
Generates PNG files using simple_web_render.py for each narrative in the dataset
"""

import csv
import os
import sys
from datetime import datetime

# Add paths for imports
current_dir = os.path.dirname(os.path.abspath(__file__))  # web/static/
web_dir = os.path.dirname(current_dir)  # web/
project_root = os.path.dirname(web_dir)  # project root

# Add web directory to path for simple_web_render
if web_dir not in sys.path:
    sys.path.insert(0, web_dir)

from simple_web_render import render_400x300_display


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


def render_narrative_to_image(narrative_text, output_path):
    """Render narrative text to PNG image"""
    try:
        # Use the existing 400x300 render function
        image = render_400x300_display(narrative_text)

        # Save as PNG
        image.save(output_path, "PNG")
        return True

    except Exception as e:
        print(f"Error rendering {output_path}: {e}")
        return False


def batch_render_images(csv_path, images_dir, max_images=None):
    """Batch render images for all narratives in dataset"""

    # Ensure images directory exists
    os.makedirs(images_dir, exist_ok=True)

    # Load narrative data
    print(f"Loading narrative dataset from {csv_path}")
    narratives = load_narrative_dataset(csv_path)

    if not narratives:
        print("No narratives found in dataset!")
        return False

    # Limit number of images if specified
    if max_images:
        narratives = narratives[:max_images]

    print(f"Rendering {len(narratives)} images to {images_dir}")

    success_count = 0

    for i, record in enumerate(narratives):
        if i % 10 == 0:
            print(f"Rendering image {i + 1}/{len(narratives)}")

        # Generate filename
        filename = generate_filename_from_record(record)
        output_path = os.path.join(images_dir, filename)

        # Skip if image already exists
        if os.path.exists(output_path):
            print(f"Skipping existing image: {filename}")
            success_count += 1
            continue

        # Render narrative to image
        narrative_text = record["narrative_text"]

        if render_narrative_to_image(narrative_text, output_path):
            success_count += 1
        else:
            print(f"Failed to render: {filename}")

    print(f"\nImage rendering complete!")
    print(f"Successfully rendered: {success_count}/{len(narratives)} images")
    print(f"Images saved to: {images_dir}")

    return success_count > 0


def verify_images(csv_path, images_dir):
    """Verify that images exist for all narratives"""
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
    """Test rendering a single narrative"""
    print("Testing single narrative render...")

    # Test with simple narrative
    test_narrative = "Clear and cold. 5°C. Light winds from the west."
    test_output = "test_render.png"

    if render_narrative_to_image(test_narrative, test_output):
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
    if len(sys.argv) > 1:
        if sys.argv[1] == "test":
            test_single_render()
        elif sys.argv[1] == "verify":
            # Verify existing images
            csv_path = "narratives.csv"
            images_dir = "images"

            if os.path.exists(csv_path):
                verify_images(csv_path, images_dir)
            else:
                print(f"Error: CSV file {csv_path} not found")
        else:
            # Batch render from CSV
            csv_path = sys.argv[1]
            images_dir = sys.argv[2] if len(sys.argv) > 2 else "images"
            max_images = int(sys.argv[3]) if len(sys.argv) > 3 else None

            if not os.path.exists(csv_path):
                print(f"Error: CSV file {csv_path} not found")
                sys.exit(1)

            batch_render_images(csv_path, images_dir, max_images)
    else:
        print("Usage:")
        print(
            "  python batch_image_renderer.py test                           # Test single render"
        )
        print(
            "  python batch_image_renderer.py verify                        # Verify existing images"
        )
        print(
            "  python batch_image_renderer.py narratives.csv [images_dir]   # Batch render images"
        )
        print(
            "  python batch_image_renderer.py narratives.csv images 10      # Render first 10 images"
        )
