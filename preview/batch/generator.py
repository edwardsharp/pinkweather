"""
High-performance batch image generation
Replaces web/static/batch_image_renderer.py with major performance improvements
Uses real pygame rendering for accurate text measurement
"""

import csv
import os
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Set silent mode IMMEDIATELY before any hardware imports
from shared.logger import set_silent_mode
from shared.setup_filesystem import set_hardware_silent_mode

# Enable silent mode for bulk operations at module level
set_silent_mode(True)
set_hardware_silent_mode(True)

# Now import hardware-related modules with silent mode already active
from shared.data_loader import CSVWeatherLoader
from shared.image_renderer import WeatherImageRenderer
from shared.weather_history_manager import WeatherHistoryManager


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


def _get_dataset_info(csv_file, max_count=None):
    """Extract dataset information from CSV file path and parameters"""
    csv_path = Path(csv_file)

    # Try to extract location from filename (e.g., "open-meteo-40.65N73.98W25m.csv" -> "nyc")
    filename = csv_path.stem
    if "40.65N73.98W" in filename or "nyc" in filename.lower():
        location = "nyc"
    elif "43.70N79.40W" in filename or "toronto" in filename.lower():
        location = "toronto"
    else:
        location = "unknown"

    # Extract year from filename or use current year
    year = "2024"
    if "2023" in filename:
        year = "2023"
    elif "2025" in filename:
        year = "2025"

    dataset_name = f"{location}_{year}"

    # Add test suffix if limited count
    if max_count and max_count < 1000:
        dataset_name += f"_test{max_count}"

    return dataset_name, location, year


def _create_html_viewer(output_dir, dataset_name, narratives_file, image_count):
    """Create HTML viewer for the generated dataset"""
    batch_dir = Path(__file__).parent
    template_file = batch_dir / "template.html"
    viewer_file = batch_dir / "viewer.html"

    output_dir = Path(output_dir)
    target_viewer = output_dir / "viewer.html"

    if template_file.exists() and viewer_file.exists():
        # Copy viewer.html to output directory
        shutil.copy2(viewer_file, target_viewer)

        # Create index.html from template
        try:
            with open(template_file, "r") as f:
                template_content = f.read()

            # Replace template variables
            html_content = (
                template_content.replace("{{dataset_name}}", dataset_name)
                .replace("{{image_count}}", str(image_count))
                .replace(
                    "{{generation_time}}", datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                )
            )

            index_file = output_dir / "index.html"
            with open(index_file, "w") as f:
                f.write(html_content)

            print(f"   📄 HTML viewer created: {index_file}")

        except Exception as e:
            print(f"   ⚠️  Could not create HTML viewer: {e}")


def generate_narratives(csv_file, output_file=None, max_count=None):
    """Generate narratives.csv with real text measurements using pygame"""

    # Set logger to silent mode for bulk operations (silent mode already set at module level)
    set_silent_mode(True)
    set_hardware_silent_mode(True)

    # Determine dataset info and output structure
    dataset_name, location, year = _get_dataset_info(csv_file, max_count)

    if output_file is None:
        # Create organized output structure
        static_dir = Path(__file__).parent.parent / "static"
        dataset_dir = static_dir / dataset_name
        dataset_dir.mkdir(parents=True, exist_ok=True)
        output_file = dataset_dir / "narratives.csv"

    # Setup
    loader = CSVWeatherLoader(csv_file)
    history_manager = WeatherHistoryManager(loader)
    records = loader.get_records(limit=max_count)

    # Initialize centralized image renderer
    renderer = WeatherImageRenderer()

    results = []
    start_time = time.time()

    try:
        # Use batch mode for performance
        with renderer.batch_mode() as batch_renderer:
            for i, record in enumerate(records):
                try:
                    # Transform data to hardware format with historical context
                    weather_data = loader.transform_record(record, include_history=True)

                    # Get historical context for enhanced narrative generation
                    timestamp = int(record["timestamp"])
                    historical_context = weather_data.get("historical_context", [])

                    # Add efficient history data with enhanced context
                    history_data = history_manager.get_history_for_csv_record(
                        record, timestamp, historical_context
                    )
                    weather_data.update(history_data)

                    # Use centralized renderer for accurate text measurement
                    text_metrics = batch_renderer.measure_narrative_text(weather_data)

                    # Create human-readable date from timestamp
                    dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
                    readable_date = dt.strftime("%Y-%m-%d %H:%M:%S UTC")

                    # Store results with generated narrative text (captured from measurement)
                    results.append(
                        {
                            "timestamp": timestamp,
                            "date": readable_date,
                            "text": text_metrics.get("stripped_text", ""),
                            "narrative_text": text_metrics.get(
                                "narrative_text", "Weather narrative unavailable"
                            ),
                            "fits_in_space": text_metrics["fits_in_space"],
                            "line_count": text_metrics["line_count"],
                            "char_count": text_metrics.get("char_count", 0),
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
                    "date",
                    "text",
                    "narrative_text",
                    "fits_in_space",
                    "line_count",
                    "char_count",
                    "temperature",
                    "description",
                ]
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(results)

            print(f"\nNarratives CSV written to {output_file} ({len(results)} records)")
            return True
        else:
            print("\nNo results to write")
            return False

    finally:
        history_manager.clear_cache()
        # Restore normal logging
        set_silent_mode(False)
        set_hardware_silent_mode(False)


def generate_images(csv_file, output_dir=None, max_count=None):
    """Generate batch PNG images with centralized renderer"""

    # Set logger to silent mode for bulk operations (silent mode already set at module level)
    set_silent_mode(True)
    set_hardware_silent_mode(True)

    # Determine dataset info and output structure
    dataset_name, location, year = _get_dataset_info(csv_file, max_count)

    if output_dir is None:
        # Create organized output structure
        static_dir = Path(__file__).parent.parent / "static"
        dataset_dir = static_dir / dataset_name
        output_dir = dataset_dir / "images"

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Setup
    loader = CSVWeatherLoader(csv_file)
    history_manager = WeatherHistoryManager(loader)
    records = loader.get_records(limit=max_count)

    # Initialize centralized image renderer
    renderer = WeatherImageRenderer()

    start_time = time.time()
    successful_renders = 0

    try:
        # Use batch mode for performance
        with renderer.batch_mode() as batch_renderer:
            for i, record in enumerate(records):
                try:
                    # Transform data to hardware format with historical context
                    weather_data = loader.transform_record(record, include_history=True)

                    # Get historical context for enhanced narrative generation
                    timestamp = int(record["timestamp"])
                    historical_context = weather_data.get("historical_context", [])

                    # Add efficient history data with enhanced context
                    history_data = history_manager.get_history_for_csv_record(
                        record, timestamp, historical_context
                    )
                    weather_data.update(history_data)

                    # Generate output filename
                    output_file = output_path / f"weather_{timestamp}.png"

                    # Render image using centralized renderer
                    result = batch_renderer.render_weather_data_to_file(
                        weather_data,
                        output_file,
                        use_icons=True,
                        indoor_temp_humidity="20° 45%",
                    )

                    if not result:
                        raise Exception(f"Failed to render {output_file}")

                    successful_renders += 1

                    # Show progress
                    show_progress(i + 1, len(records), start_time)

                except Exception as e:
                    print(f"\nError processing record {i}: {e}")
                    continue

        print(
            f"\nBatch image generation complete. {successful_renders}/{len(records)} images saved to {output_dir}"
        )

        # Create HTML viewer for the dataset
        if successful_renders > 0:
            # Check for narratives file in same dataset directory
            dataset_dir = output_path.parent
            narratives_file = dataset_dir / "narratives.csv"
            _create_html_viewer(
                dataset_dir, dataset_name, narratives_file, successful_renders
            )

        return successful_renders > 0

    finally:
        history_manager.clear_cache()
        # Restore normal logging
        set_silent_mode(False)
        set_hardware_silent_mode(False)


def generate_complete_dataset(csv_file, max_count=None):
    """Generate both narratives and images for a complete dataset"""

    # Set logger to silent mode for bulk operations (silent mode already set at module level)
    set_silent_mode(True)
    set_hardware_silent_mode(True)

    try:
        dataset_name, location, year = _get_dataset_info(csv_file, max_count)

        # Create organized output structure
        static_dir = Path(__file__).parent.parent / "static"
        dataset_dir = static_dir / dataset_name
        dataset_dir.mkdir(parents=True, exist_ok=True)

        print(f"🎯 Generating complete dataset: {dataset_name}")
        print(f"   Location: {location}")
        print(f"   Year: {year}")
        print(f"   Output: {dataset_dir}")
        if max_count:
            print(f"   Max records: {max_count}")

        # Generate narratives first
        print(f"\n📝 Step 1: Generating narratives...")
        narratives_file = dataset_dir / "narratives.csv"
        narratives_success = generate_narratives(csv_file, narratives_file, max_count)

        if not narratives_success:
            print("❌ Narratives generation failed, aborting")
            return False

        # Generate images
        print(f"\n🖼️  Step 2: Generating images...")
        images_dir = dataset_dir / "images"
        images_success = generate_images(csv_file, images_dir, max_count)

        if images_success:
            print(f"\n✅ Complete dataset generated successfully!")
            print(f"   Dataset: {dataset_dir}")
            print(f"   View at: {dataset_dir}/index.html")
            return True
        else:
            print("❌ Image generation failed")
            return False

    finally:
        # Restore normal logging
        set_silent_mode(False)
        set_hardware_silent_mode(False)


def main():
    """Command line interface for batch operations"""
    import argparse

    parser = argparse.ArgumentParser(description="Batch weather data processing")
    parser.add_argument(
        "mode", choices=["narratives", "images", "complete"], help="Processing mode"
    )
    parser.add_argument("csv_file", help="Input CSV file path")
    parser.add_argument(
        "output",
        nargs="?",
        help="Output file/directory path (optional for auto organization)",
    )
    parser.add_argument(
        "--max-count", type=int, help="Maximum number of records to process"
    )

    args = parser.parse_args()

    print(f"Starting batch {args.mode} generation...")
    print(f"Input: {args.csv_file}")
    print(f"Output: {args.output}")
    if args.max_count:
        print(f"Max records: {args.max_count}")

    success = True
    if args.mode == "narratives":
        success = generate_narratives(args.csv_file, args.output, args.max_count)
    elif args.mode == "images":
        success = generate_images(args.csv_file, args.output, args.max_count)
    elif args.mode == "complete":
        success = generate_complete_dataset(args.csv_file, args.max_count)

    return success


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n🛑 Batch operation cancelled")
        sys.exit(1)
    except Exception as e:
        print(f"💥 Batch operation failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
