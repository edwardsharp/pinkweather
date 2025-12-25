"""
Generate historical weather narrative dataset with measurements
Processes CSV weather data to create narratives and measure text dimensions
Uses existing OpenMeteoConverter for proper CSV parsing
"""

import csv
import os
import sys
from datetime import datetime

# Add paths for imports
current_dir = os.path.dirname(os.path.abspath(__file__))  # web/static/
web_dir = os.path.dirname(current_dir)  # web/
project_root = os.path.dirname(web_dir)  # project root
circuitpy_400x300_path = os.path.join(project_root, "300x400", "CIRCUITPY")

# Add web directory to path for OpenMeteoConverter
if web_dir not in sys.path:
    sys.path.insert(0, web_dir)

# Add CIRCUITPY to path for narrative generation
if circuitpy_400x300_path not in sys.path:
    sys.path.insert(0, circuitpy_400x300_path)

from narrative_measurement import NarrativeMeasurer
from open_meteo_converter import OpenMeteoConverter


def load_historical_csv(csv_file_path):
    """Load historical weather data using existing OpenMeteoConverter"""
    print(f"Loading and parsing CSV: {csv_file_path}")

    converter = OpenMeteoConverter(csv_file_path)
    converter._parse_csv()

    weather_records = []

    for row in converter.hourly_data:
        try:
            # Parse timestamp
            timestamp = converter._parse_timestamp(row["time"])
            if not timestamp:
                continue

            dt = datetime.fromtimestamp(timestamp)

            # Extract weather data using converter's safe methods
            record = {
                "timestamp": timestamp,
                "date": dt.strftime("%Y-%m-%d"),
                "hour": dt.strftime("%H:%M"),
                "temp_c": converter._safe_float(row["temperature_2m (°C)"], 0.0),
                "feels_like": converter._safe_float(
                    row["apparent_temperature (°C)"], 0.0
                ),
                "humidity": converter._safe_float(
                    row["relative_humidity_2m (%)"], 50.0
                ),
                "weather_code": converter._safe_int(row["weather_code (wmo code)"], 1),
                "wind_speed": converter._safe_float(row["wind_speed_10m (km/h)"], 0.0),
                "wind_gust": converter._safe_float(row["wind_gusts_10m (km/h)"], 0.0),
                "cloud_cover": converter._safe_float(row["cloud_cover (%)"], 50.0),
                "precipitation": converter._safe_float(row["precipitation (mm)"], 0.0),
                "visibility": converter._safe_float(row["visibility (m)"], 10000.0),
                "is_day": converter._safe_int(row["is_day ()"], 1),
            }

            weather_records.append(record)

        except Exception as e:
            print(f"Skipping row due to error: {e}")
            continue

    print(f"Successfully parsed {len(weather_records)} weather records")
    return weather_records


def wmo_code_to_description(code):
    """Convert WMO weather code to description"""
    wmo_codes = {
        0: "clear sky",
        1: "mainly clear",
        2: "partly cloudy",
        3: "overcast",
        45: "fog",
        48: "depositing rime fog",
        51: "light drizzle",
        53: "moderate drizzle",
        55: "dense drizzle",
        56: "light freezing drizzle",
        57: "dense freezing drizzle",
        61: "slight rain",
        63: "moderate rain",
        65: "heavy rain",
        66: "light freezing rain",
        67: "heavy freezing rain",
        71: "slight snow fall",
        73: "moderate snow fall",
        75: "heavy snow fall",
        77: "snow grains",
        80: "slight rain showers",
        81: "moderate rain showers",
        82: "violent rain showers",
        85: "slight snow showers",
        86: "heavy snow showers",
        95: "thunderstorm",
        96: "thunderstorm with slight hail",
        99: "thunderstorm with heavy hail",
    }
    return wmo_codes.get(code, f"unknown weather (code {code})")


def convert_to_weather_format(record):
    """Convert CSV record to weather data format expected by narrative generator"""
    return {
        "current_temp": record["temp_c"],
        "feels_like": record["feels_like"],
        "high_temp": record["temp_c"] + 2,  # Rough estimate for testing
        "low_temp": record["temp_c"] - 3,  # Rough estimate for testing
        "weather_desc": wmo_code_to_description(record["weather_code"]),
        "humidity": record["humidity"],
        "wind_speed": record["wind_speed"],
        "wind_gust": record["wind_gust"],
        "sunset_timestamp": record["timestamp"] + (18 * 3600),  # Rough sunset estimate
    }


def generate_simple_narrative(weather_data):
    """Generate a simple narrative for testing (simplified version)"""
    temp = weather_data["current_temp"]
    desc = weather_data["weather_desc"]
    feels_like = weather_data["feels_like"]
    humidity = weather_data["humidity"]
    wind_speed = weather_data["wind_speed"]

    # Create a simple narrative
    narrative_parts = []

    # Temperature description
    if temp < 0:
        temp_desc = "freezing"
    elif temp < 10:
        temp_desc = "cold"
    elif temp < 20:
        temp_desc = "cool"
    elif temp < 25:
        temp_desc = "mild"
    elif temp < 30:
        temp_desc = "warm"
    else:
        temp_desc = "hot"

    # Basic conditions
    narrative_parts.append(f"{desc.capitalize()} and {temp_desc}")
    narrative_parts.append(f"{temp:.1f}°C")

    # Feels like difference
    if abs(feels_like - temp) > 2:
        if feels_like > temp:
            narrative_parts.append(f"feels like {feels_like:.1f}°C due to humidity")
        else:
            narrative_parts.append(f"feels like {feels_like:.1f}°C with wind chill")

    # Wind conditions
    if wind_speed > 20:
        narrative_parts.append("windy conditions")
    elif wind_speed > 10:
        narrative_parts.append("breezy")

    # Humidity
    if humidity > 80:
        narrative_parts.append("very humid")
    elif humidity < 30:
        narrative_parts.append("dry air")

    return ". ".join(narrative_parts) + "."


def generate_historical_dataset(csv_file_path, output_file, max_records=100):
    """Generate historical dataset with narratives and measurements"""
    print(f"Loading weather data from {csv_file_path}")
    weather_records = load_historical_csv(csv_file_path)

    if not weather_records:
        print("No weather records found!")
        return []

    print(f"Processing {min(len(weather_records), max_records)} records...")

    # Initialize measurement system
    measurer = NarrativeMeasurer()

    results = []

    for i, record in enumerate(weather_records[:max_records]):
        if i % 10 == 0:
            print(f"Processing record {i + 1}/{min(len(weather_records), max_records)}")

        # Convert to weather data format
        weather_data = convert_to_weather_format(record)

        # Generate narrative
        narrative = generate_simple_narrative(weather_data)

        # Measure text
        metrics = measurer.measure_narrative_text(narrative)

        # Collect result
        result = {
            "timestamp": record["timestamp"],
            "date": record["date"],
            "hour": record["hour"],
            "narrative_text": narrative,
            "text_length_px": metrics["text_width_px"],
            "text_height_px": metrics["text_height_px"],
            "line_count": metrics["line_count"],
            "fits_display": metrics["fits_display"],
            "temp": record["temp_c"],
            "weather_desc": weather_data["weather_desc"],
            "char_count": metrics["char_count"],
            "overflow_lines": metrics["overflow_lines"],
        }

        results.append(result)

    # Save to CSV
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

    return results


def test_single_narrative():
    """Test narrative generation and measurement with a single record"""
    print("Testing single narrative generation...")

    # Create a test weather record
    test_record = {
        "timestamp": 1704067200,
        "date": "2024-01-01",
        "hour": "00:00",
        "temp_c": 2.5,
        "feels_like": -1.2,
        "humidity": 75,
        "weather_code": 3,  # overcast
        "wind_speed": 15,
        "wind_gust": 20,
        "cloud_cover": 95,
        "precipitation": 0,
        "visibility": 10000,
        "is_day": 0,
    }

    # Convert and generate narrative
    weather_data = convert_to_weather_format(test_record)
    narrative = generate_simple_narrative(weather_data)

    print(f"Weather data: {weather_data}")
    print(f"Generated narrative: {narrative}")

    # Measure it
    measurer = NarrativeMeasurer()
    metrics = measurer.measure_narrative_text(narrative)

    print(f"Metrics: {metrics}")
    print(f"Fits display: {metrics['fits_display']}")


def generate_html_viewer(csv_path, output_html="viewer.html"):
    """Generate HTML viewer using template and injection script"""
    template_path = os.path.join(current_dir, "template.html")
    inject_script = os.path.join(current_dir, "inject_data.py")

    # Use the injection script
    import subprocess

    result = subprocess.run(
        [sys.executable, inject_script, csv_path, output_html, template_path],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        print(f"Generated HTML viewer: {output_html}")
    else:
        print(f"Error generating HTML viewer: {result.stderr}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "test":
            test_single_narrative()
        else:
            # Generate dataset from specified CSV
            csv_path = sys.argv[1]
            output_path = "narratives.csv"
            max_records = 50  # Start with small dataset

            if not os.path.exists(csv_path):
                print(f"Error: CSV file {csv_path} not found")
                sys.exit(1)

            results = generate_historical_dataset(csv_path, output_path, max_records)

            # Also generate HTML viewer
            if results:
                generate_html_viewer(output_path)
    else:
        print("Usage:")
        print(
            "  python generate_historical_data.py test                    # Test single record"
        )
        print(
            "  python generate_historical_data.py path/to/weather.csv    # Generate dataset and HTML viewer"
        )
