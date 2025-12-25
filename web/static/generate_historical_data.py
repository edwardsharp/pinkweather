"""
Generate historical weather narrative dataset using shared weather engine
Simple script that loads CSV timestamps and calls shared engine for each one
"""

import csv
import os
import sys
from datetime import datetime

# Add paths for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
web_dir = os.path.dirname(current_dir)
if web_dir not in sys.path:
    sys.path.insert(0, web_dir)

from narrative_measurement import NarrativeMeasurer


def load_csv_timestamps(csv_file_path):
    """Load CSV file and extract timestamps for processing"""
    print(f"Loading CSV timestamps from: {csv_file_path}")

    if not os.path.exists(csv_file_path):
        raise FileNotFoundError(f"CSV file not found: {csv_file_path}")

    # Import after path setup
    from open_meteo_converter import OpenMeteoConverter

    converter = OpenMeteoConverter(csv_file_path)
    converter._parse_csv()

    timestamps = []
    for row in converter.hourly_data:
        timestamp = converter._parse_timestamp(row["time"])
        if timestamp:
            timestamps.append(int(timestamp))

    print(f"Loaded {len(timestamps)} timestamps from CSV")
    return timestamps


def generate_historical_dataset(csv_file_path, max_records=None):
    """Generate historical dataset using shared weather engine"""

    # Load CSV timestamps
    timestamps = load_csv_timestamps(csv_file_path)

    if not timestamps:
        raise Exception("No timestamps found in CSV")

    # Limit records if specified
    if max_records and max_records > 0:
        timestamps = timestamps[:max_records]
        print(f"Processing first {len(timestamps)} records (limited by count)...")
    else:
        print(f"Processing all {len(timestamps)} records...")

    # Import shared engine
    from shared_weather_engine import generate_complete_weather_display

    # Initialize text measurement
    measurer = NarrativeMeasurer()

    results = []

    for i, timestamp in enumerate(timestamps):
        if i % 100 == 0:
            print(f"Processing record {i + 1}/{len(timestamps)}")

        try:
            # Use shared engine - same logic as web server!
            image, narrative, metrics = generate_complete_weather_display(
                csv_file_path, timestamp
            )

            # Measure text dimensions
            text_metrics = measurer.measure_narrative_text(narrative)

            # Combine data for CSV output
            result = {
                **metrics,  # timestamp, date, hour, narrative_text, temp, weather_desc
                "text_length_px": text_metrics["text_width_px"],
                "text_height_px": text_metrics["text_height_px"],
                "line_count": text_metrics["line_count"],
                "fits_display": text_metrics["fits_display"],
                "char_count": text_metrics["char_count"],
                "overflow_lines": text_metrics["overflow_lines"],
            }

            results.append(result)

        except Exception as e:
            print(f"Error processing timestamp {timestamp}: {e}")
            # Fail fast as requested
            raise

    # Save to CSV
    output_file = os.path.join(current_dir, "narratives.csv")
    save_results_to_csv(results, output_file)

    # Generate HTML viewer
    generate_html_viewer(output_file)

    # Print summary
    total_records = len(results)
    overflow_count = sum(1 for r in results if not r["fits_display"])
    overflow_rate = (overflow_count / total_records) * 100 if total_records > 0 else 0

    print(f"\nDataset Generation Complete!")
    print(f"Total records: {total_records}")
    print(f"Records with overflow: {overflow_count}")
    print(f"Overflow rate: {overflow_rate:.1f}%")
    print(
        f"Average characters: {sum(r['char_count'] for r in results) / total_records:.0f}"
    )
    print(f"Average lines: {sum(r['line_count'] for r in results) / total_records:.1f}")

    return results, output_file


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
    if len(sys.argv) > 1:
        csv_path = sys.argv[1]
        max_records = None

        # Check for optional count parameter
        if len(sys.argv) > 2:
            try:
                max_records = int(sys.argv[2])
                print(f"Will process maximum {max_records} records")
            except ValueError:
                print(f"Error: Invalid count '{sys.argv[2]}' - must be a number")
                sys.exit(1)

        if not os.path.exists(csv_path):
            print(f"Error: CSV file {csv_path} not found")
            sys.exit(1)

        try:
            results, output_path = generate_historical_dataset(csv_path, max_records)
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)
    else:
        print("Usage:")
        print(
            "  python generate_historical_data.py path/to/weather.csv          # Generate full dataset"
        )
        print(
            "  python generate_historical_data.py path/to/weather.csv 10       # Generate first 10 records"
        )
