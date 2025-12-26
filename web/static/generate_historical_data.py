"""
Generate historical weather narrative dataset using shared weather engine
Simple script that loads CSV timestamps and calls shared engine for each one
"""

import csv
import os
import sys
import time
from datetime import datetime


def show_progress(current, total, start_time):
    """Simple progress display that works in terminals and redirected output"""
    elapsed = time.time() - start_time
    rate = current / elapsed if elapsed > 0 else 0
    eta = (total - current) / rate if rate > 0 else 0
    progress_pct = (current / total) * 100

    progress_text = f"Progress: {current}/{total} ({progress_pct:.1f}%) - {rate:.1f} rec/sec - ETA: {eta:.0f}s"

    if sys.stdout.isatty():
        # Terminal: use single line that updates
        print(f"\r{progress_text}", end="", flush=True)
    else:
        # Redirected: use newlines every 50 records to avoid spam
        if current % 50 == 0 or current == total:
            print(progress_text)


# Add paths for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
web_dir = os.path.dirname(current_dir)
if web_dir not in sys.path:
    sys.path.insert(0, web_dir)

# Enable silent mode for centralized web logger to reduce verbose output during batch processing
import logger

logger.set_silent_mode(True)

import re

from narrative_measurement import NarrativeMeasurer


def load_csv_timestamps(dataset_name=None):
    """Load CSV file and extract timestamps for processing"""
    from csv_config import DEFAULT_DATASET, get_dataset_info
    from open_meteo_converter import get_converter

    if dataset_name is None:
        dataset_name = DEFAULT_DATASET

    print(f"Loading timestamps from dataset: {dataset_name}")

    dataset_info = get_dataset_info(dataset_name)
    csv_file_path = dataset_info["csv_path"]

    # Use existing converter cache
    converter = get_converter(dataset_name)
    if not converter:
        raise Exception(f"Failed to get converter for dataset: {dataset_name}")

    timestamps = []
    for row in converter.hourly_data:
        timestamp = converter._parse_timestamp(row["time"])
        if timestamp:
            timestamps.append(int(timestamp))

    print(f"Loaded {len(timestamps)} timestamps from {dataset_name}")
    return timestamps, csv_file_path


def remove_markup_tags(text):
    """Remove markup tags like <h>, <i>, <b> from narrative text"""
    # Remove tags like <h>text</h>, <i>text</i>, <b>text</b>
    clean_text = re.sub(r"<[^>]+>", "", text)
    return clean_text


def generate_historical_dataset(dataset_name=None, max_records=None, csv_only=False):
    """Generate historical dataset using two-pass approach: CSV first, then images"""

    if csv_only:
        # Just do CSV generation
        return _generate_csv_data(dataset_name, max_records)
    else:
        # Two-pass approach: CSV first, then images
        print("Step 1/2: Generating CSV data...")
        results, output_file = _generate_csv_data(dataset_name, max_records)

        print("Step 2/2: Generating images...")
        _generate_images_from_csv(output_file, max_records)

        return results, output_file


def _generate_csv_data(dataset_name=None, max_records=None):
    """Generate CSV data quickly without images"""

    # Load CSV timestamps
    timestamps, csv_file_path = load_csv_timestamps(dataset_name)

    if not timestamps:
        raise Exception("No timestamps found in CSV")

    # Limit records if specified
    if max_records and max_records > 0:
        timestamps = timestamps[:max_records]
        print(f"Processing first {len(timestamps)} records...")
    else:
        print(f"Processing all {len(timestamps)} records...")

    # Import shared engine for data generation only
    from shared_weather_engine import generate_weather_display_for_timestamp

    # Initialize text measurement
    measurer = NarrativeMeasurer()

    results = []
    start_time = time.time()

    # Generate CSV data only (fast)
    for i, timestamp in enumerate(timestamps):
        show_progress(i + 1, len(timestamps), start_time)

        try:
            # Generate weather data and narrative (no image)
            weather_data, narrative, display_vars, current_weather = (
                generate_weather_display_for_timestamp(csv_file_path, timestamp)
            )

            # Remove markup tags from narrative for plain text version
            plain_narrative = remove_markup_tags(narrative)

            # Measure text dimensions
            text_metrics = measurer.measure_narrative_text(narrative)

            # Create CSV record
            dt = datetime.fromtimestamp(timestamp)
            result = {
                "timestamp": timestamp,
                "date": dt.strftime("%Y-%m-%d"),
                "hour": dt.strftime("%H:%M"),
                "narrative_text": narrative,
                "narrative_text_plain": text_metrics["narrative_text_plain_wrapped"],
                "line_count": text_metrics["line_count"],
                "fits_display": text_metrics["fits_display"],
                "char_count": len(plain_narrative),
                "overflow_lines": text_metrics["overflow_lines"],
                "temp": current_weather.get("current_temp"),
                "weather_desc": current_weather.get("weather_desc"),
            }
            results.append(result)

        except Exception as e:
            print(f"Error processing timestamp {timestamp}: {e}")
            raise

    # Save to CSV
    output_file = os.path.join(current_dir, "narratives.csv")
    save_csv_only_results(results, output_file)

    # Generate HTML viewer
    generate_html_viewer(output_file)

    # Final progress line and completion message
    if sys.stdout.isatty():
        print()  # Add newline after progress line
    print(f"CSV Generation Complete!")

    total_records = len(results)
    overflow_count = sum(1 for r in results if not r["fits_display"])
    overflow_rate = (overflow_count / total_records) * 100 if total_records > 0 else 0

    print(f"Summary:")
    print(f"  Total records: {total_records}")
    print(f"  Records with overflow: {overflow_count} ({overflow_rate:.1f}%)")
    print(
        f"  Average characters: {sum(r['char_count'] for r in results) / total_records:.0f}"
    )
    print(
        f"  Average lines: {sum(r['line_count'] for r in results) / total_records:.1f}"
    )
    print(f"Files created:")
    print(f"  {output_file}")

    return results, output_file


def _generate_images_from_csv(csv_file_path, max_records=None):
    """Generate images from existing CSV file"""

    import csv

    from shared_weather_engine import (
        generate_weather_display_for_timestamp,
        render_weather_to_image,
    )

    # Create images directory
    images_dir = os.path.join(current_dir, "images")
    os.makedirs(images_dir, exist_ok=True)

    # Load CSV data
    records = []
    with open(csv_file_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append(row)

    # Limit if specified
    if max_records and max_records > 0:
        records = records[:max_records]

    print(f"Generating {len(records)} images...")
    start_time = time.time()

    # Generate images
    for i, record in enumerate(records):
        show_progress(i + 1, len(records), start_time)

        try:
            timestamp = int(record["timestamp"])

            # Load CSV timestamps to get csv_file_path
            timestamps, csv_file_path = load_csv_timestamps()

            # Generate weather data and narrative
            weather_data, narrative, display_vars, current_weather = (
                generate_weather_display_for_timestamp(csv_file_path, timestamp)
            )

            # Render image
            image = render_weather_to_image(
                weather_data, narrative, display_vars, current_weather
            )

            # Save image
            dt = datetime.fromtimestamp(timestamp)
            image_filename = f"{dt.strftime('%Y%m%d_%H%M%S')}.png"
            image_path = os.path.join(images_dir, image_filename)
            image.save(image_path)

        except Exception as e:
            print(f"Error generating image for timestamp {timestamp}: {e}")
            raise

    if sys.stdout.isatty():
        print()  # Add newline after progress line
    print(
        f"Image generation complete! Generated {len(records)} images in {images_dir}/"
    )


def save_csv_only_results(results, output_file):
    """Save CSV-only results to file"""
    print(f"Saving results to {output_file}")

    fieldnames = [
        "timestamp",
        "date",
        "hour",
        "narrative_text",
        "narrative_text_plain",
        "line_count",
        "fits_display",
        "char_count",
        "overflow_lines",
        "temp",
        "weather_desc",
    ]

    with open(output_file, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)


def save_results_to_csv(results, output_file):
    """Save results to CSV file"""
    print(f"Saving results to {output_file}")

    fieldnames = [
        "timestamp",
        "date",
        "hour",
        "narrative_text",
        "text_length_px",
        "text_height_px",
        "line_count",
        "fits_display",
        "temp",
        "weather_desc",
        "char_count",
        "overflow_lines",
        "image_filename",
    ]

    with open(output_file, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)


def generate_html_viewer(csv_path):
    """Generate HTML viewer using inject_data.py"""
    inject_script = os.path.join(current_dir, "inject_data.py")

    import subprocess

    result = subprocess.run(
        [sys.executable, inject_script], cwd=current_dir, capture_output=True, text=True
    )

    if result.returncode == 0:
        output_html = os.path.join(current_dir, "viewer.html")
        print(f"Generated HTML viewer: {output_html}")
    else:
        print(f"Error generating HTML viewer: {result.stderr}")


if __name__ == "__main__":
    from csv_config import DEFAULT_DATASET, list_available_datasets

    dataset_name = None
    max_records = None
    csv_only_mode = False

    if len(sys.argv) > 1:
        first_arg = sys.argv[1]

        # Check for CSV-only mode flag
        if first_arg == "--csv-only":
            csv_only_mode = True
            # Shift arguments
            if len(sys.argv) > 2:
                first_arg = sys.argv[2]
            else:
                first_arg = None

        if first_arg:
            # Check if first arg is a dataset name, CSV path, or count
            if first_arg.endswith(".csv"):
                # Legacy CSV path support - convert to dataset name
                from csv_config import find_dataset_for_csv_path

                dataset_name = find_dataset_for_csv_path(first_arg)
                if not dataset_name:
                    print(
                        f"Error: CSV file not recognized as a known dataset: {first_arg}"
                    )
                    print("Available datasets:")
                    for name, desc in list_available_datasets().items():
                        print(f"  {name}: {desc}")
                    sys.exit(1)
            elif first_arg.isdigit():
                # First arg is a count, use default dataset
                dataset_name = None
                max_records = int(first_arg)
            elif first_arg in list_available_datasets():
                # First arg is a dataset name
                dataset_name = first_arg
            else:
                print(f"Error: Unknown dataset '{first_arg}'. Available datasets:")
                for name, desc in list_available_datasets().items():
                    print(f"  {name}: {desc}")
                print("Or provide a number for record count.")
                print("Use --csv-only flag to skip image generation.")
                sys.exit(1)

        # Check for optional count parameter
        next_arg_idx = 3 if csv_only_mode else 2
        if len(sys.argv) > next_arg_idx and max_records is None:
            try:
                max_records = int(sys.argv[next_arg_idx])
                print(f"Will process maximum {max_records} records")
            except ValueError:
                print(
                    f"Error: Invalid count '{sys.argv[next_arg_idx]}' - must be a number"
                )
                sys.exit(1)

        try:
            if csv_only_mode:
                print("Running in CSV-only mode (no images)")
                results, output_path = generate_historical_dataset(
                    dataset_name, max_records, csv_only=True
                )
            else:
                results, output_path = generate_historical_dataset(
                    dataset_name, max_records
                )
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)
    else:
        # No arguments - show usage
        print("Usage:")
        print(
            "  python generate_historical_data.py [--csv-only] [dataset_name] [count]"
        )
        print("  python generate_historical_data.py [--csv-only] [count]")
        print("")
        print("Options:")
        print("  --csv-only    Generate CSV without images (fast)")
        print("")
        print("Available datasets:")
        for name, desc in list_available_datasets().items():
            print(f"  {name}: {desc}")
        print("")
        print("Examples:")
        print("  python generate_historical_data.py --csv-only 10")
        print("  python generate_historical_data.py ny_2024 100")
        print("  python generate_historical_data.py --csv-only ny_2024 50")

        try:
            # Default: process all records
            print("Running default: processing all records")
            results, output_path = generate_historical_dataset(None, None)
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)
