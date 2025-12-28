"""
High-performance batch image generation
Replaces web/static/batch_image_renderer.py with major performance improvements
Uses real pygame rendering for accurate text measurement
"""

import csv
import sys
import time
from pathlib import Path

from data_loader import CSVWeatherLoader
from pygame_manager import PersistentPygameDisplay
from weather_history_manager import WeatherHistoryManager


def show_progress(current, total, start_time):
    """Progress display that updates same line (avoids terminal spam)"""
    elapsed = time.time() - start_time
    rate = current / elapsed if elapsed > 0 else 0
    eta = (total - current) / rate if rate > 0 else 0
    progress_pct = (current / total) * 100

    progress_text = f"\rProgress: {current}/{total} ({progress_pct:.1f}%) - {rate:.1f} img/sec - ETA: {eta:.0f}s"

    # Always use same line update to avoid spam
    print(progress_text, end="", flush=True)

    # Add newline only when complete
    if current == total:
        print()  # Final newline


def batch_generate_narratives_csv(csv_file, output_file, max_count=None):
    """Generate narratives.csv with real text measurements using pygame"""

    # Setup
    loader = CSVWeatherLoader(csv_file)
    history_manager = WeatherHistoryManager(loader)
    records = loader.get_records(limit=max_count)

    # Initialize persistent pygame for measurements
    pygame_display = PersistentPygameDisplay()
    pygame_display.start()

    results = []
    start_time = time.time()

    try:
        for i, record in enumerate(records):
            try:
                # Transform data to hardware format
                weather_data = loader.transform_record(record)

                # Add efficient history data
                timestamp = int(record["timestamp"])
                history_data = history_manager.get_history_for_csv_record(
                    record, timestamp
                )
                weather_data.update(history_data)

                # Use real pygame rendering for accurate text measurement
                text_metrics = pygame_display.measure_narrative_text(weather_data)

                # Store results
                results.append(
                    {
                        "timestamp": timestamp,
                        "fits_in_space": text_metrics["fits_in_space"],
                        "line_count": text_metrics["line_count"],
                        "height": text_metrics["height"],
                        "width": text_metrics["width"],
                        "temperature": record.get("temperature", 0),
                        "description": record.get("description", ""),
                    }
                )

                # Show progress
                show_progress(i + 1, len(records), start_time)

            except Exception as e:
                print(f"\nError processing record {i}: {e}")
                continue

        # Write results to CSV
        if results:
            with open(output_file, "w", newline="") as f:
                fieldnames = [
                    "timestamp",
                    "fits_in_space",
                    "line_count",
                    "height",
                    "width",
                    "temperature",
                    "description",
                ]
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(results)

            print(f"\nNarratives CSV written to {output_file} ({len(results)} records)")
        else:
            print("\nNo results to write")

    finally:
        pygame_display.shutdown()
        history_manager.clear_cache()


def batch_generate_images(csv_file, output_dir, max_count=None):
    """Generate batch PNG images with persistent pygame instance"""

    # Setup
    loader = CSVWeatherLoader(csv_file)
    history_manager = WeatherHistoryManager(loader)
    records = loader.get_records(limit=max_count)

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Initialize persistent pygame for rendering
    pygame_display = PersistentPygameDisplay()
    pygame_display.start()

    start_time = time.time()

    try:
        for i, record in enumerate(records):
            try:
                # Transform data to hardware format
                weather_data = loader.transform_record(record)

                # Add efficient history data
                timestamp = int(record["timestamp"])
                history_data = history_manager.get_history_for_csv_record(
                    record, timestamp
                )
                weather_data.update(history_data)

                # Generate output filename
                output_file = output_path / f"weather_{timestamp}.png"

                # Render image
                pygame_display.render_weather_data(weather_data, output_file)

                # Show progress
                show_progress(i + 1, len(records), start_time)

            except Exception as e:
                print(f"\nError processing record {i}: {e}")
                continue

        print(f"\nBatch image generation complete. Images saved to {output_dir}")

    finally:
        pygame_display.shutdown()
        history_manager.clear_cache()


def main():
    """Command line interface for batch operations"""
    import argparse

    parser = argparse.ArgumentParser(description="Batch weather data processing")
    parser.add_argument(
        "mode", choices=["narratives", "images"], help="Processing mode"
    )
    parser.add_argument("csv_file", help="Input CSV file path")
    parser.add_argument("output", help="Output file/directory path")
    parser.add_argument(
        "--max-count", type=int, help="Maximum number of records to process"
    )

    args = parser.parse_args()

    print(f"Starting batch {args.mode} generation...")
    print(f"Input: {args.csv_file}")
    print(f"Output: {args.output}")
    if args.max_count:
        print(f"Max records: {args.max_count}")

    if args.mode == "narratives":
        batch_generate_narratives_csv(args.csv_file, args.output, args.max_count)
    elif args.mode == "images":
        batch_generate_images(args.csv_file, args.output, args.max_count)


if __name__ == "__main__":
    main()
