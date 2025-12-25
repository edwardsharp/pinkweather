"""
Generate historical weather narrative dataset with measurements
Processes CSV weather data to create narratives and measure text dimensions
Uses existing OpenMeteoConverter for proper CSV parsing
"""

import csv
import os
import sys
from datetime import datetime, timedelta

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

# Try to import real weather narrative generator and history
try:
    import weather_narrative
    from mock_history import _mock_history_cache

    USE_REAL_NARRATIVES = True
    print("Using real weather narrative generator")
except ImportError:
    USE_REAL_NARRATIVES = False
    print("Warning: Could not import weather_narrative, using simple narratives")


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
                "uv_index": converter._safe_float(row["uv_index ()"], 0.0),
                "dew_point": converter._safe_float(row["dew_point_2m (°C)"], 0.0),
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
        "high_temp": record.get("daily_high", record["temp_c"] + 2),
        "low_temp": record.get("daily_low", record["temp_c"] - 3),
        "weather_desc": wmo_code_to_description(record["weather_code"]),
        "humidity": record["humidity"],
        "wind_speed": record["wind_speed"],
        "wind_gust": record["wind_gust"],
        "dew_point": record["dew_point"],
        "sunset_timestamp": record["timestamp"] + (18 * 3600),  # Rough sunset estimate
        "weather": wmo_code_to_description(
            record["weather_code"]
        ),  # For real generator
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


def setup_weather_history(current_record, weather_records):
    """Setup weather history for narrative generation"""
    if not USE_REAL_NARRATIVES:
        return

    try:
        current_timestamp = int(current_record["timestamp"])
        current_date = datetime.fromtimestamp(current_timestamp)

        # Clear cache and setup historical data
        _mock_history_cache.clear()

        for days_back in range(1, 11):
            historical_date = current_date - timedelta(days=days_back)
            target_timestamp = int(historical_date.timestamp())

            # Find closest record
            closest_record = None
            min_diff = float("inf")

            for record in weather_records:
                record_timestamp = int(record["timestamp"])
                diff = abs(record_timestamp - target_timestamp)
                if diff < min_diff:
                    min_diff = diff
                    closest_record = record

            if closest_record and min_diff < 86400:
                temp = float(closest_record["temp_c"])
                date_key = historical_date.strftime("%Y-%m-%d")
                _mock_history_cache[date_key] = {
                    "current": temp,
                    "high": float(closest_record.get("daily_high", temp)),
                    "low": float(closest_record.get("daily_low", temp)),
                }
    except Exception:
        pass


def find_future_weather_data(current_record, weather_records):
    """Find weather data for tomorrow's forecast"""
    current_timestamp = int(current_record["timestamp"])
    tomorrow_timestamp = current_timestamp + 86400  # 24 hours later

    # Find records for the next 24 hours
    future_records = []
    for record in weather_records:
        record_timestamp = int(record["timestamp"])
        if current_timestamp < record_timestamp <= tomorrow_timestamp + 3600:
            future_records.append(record)

    # If we have future data, use it. Otherwise, generate reasonable forecast
    if future_records:
        return future_records[:24]  # Up to 24 hours
    else:
        # Generate basic forecast if no future data
        base_temp = current_record["temp_c"]
        return [
            {
                "temp_c": base_temp + (i * 0.1),
                "weather_desc": current_record.get("weather_desc", "partly cloudy"),
                "feels_like": current_record.get("feels_like", base_temp - 2),
                "humidity": current_record.get("humidity", 60),
                "wind_speed": current_record.get("wind_speed", 10),
                "wind_gust": current_record.get("wind_gust", 15),
            }
            for i in range(24)
        ]


def generate_real_narrative(weather_data, current_timestamp, future_data):
    """Generate narrative using the real weather narrative generator with proper forecast"""
    try:
        # Create proper forecast data for narrative generator
        forecast_data = []
        for i, future_record in enumerate(future_data):
            if isinstance(future_record, dict):
                forecast_data.append(
                    {
                        "dt": current_timestamp + (i * 3600),
                        "weather": [
                            {
                                "description": future_record.get(
                                    "weather_desc", "partly cloudy"
                                )
                            }
                        ],
                        "main": {
                            "temp": future_record.get(
                                "temp_c", weather_data["current_temp"]
                            ),
                            "feels_like": future_record.get(
                                "feels_like", weather_data["feels_like"]
                            ),
                            "temp_max": weather_data["high_temp"],
                            "temp_min": weather_data["low_temp"],
                        },
                        "wind": {
                            "speed": future_record.get(
                                "wind_speed", weather_data["wind_speed"]
                            ),
                            "gust": future_record.get(
                                "wind_gust", weather_data["wind_gust"]
                            ),
                        },
                        "rain": {"3h": future_record.get("precipitation", 0)},
                        "snow": {},
                        "clouds": {"all": future_record.get("cloud_cover", 50)},
                    }
                )

        return weather_narrative.get_weather_narrative(
            weather_data, forecast_data, current_timestamp
        )
    except Exception as e:
        print(f"Error generating real narrative: {e}")
        # Fall back to simple narrative
        return generate_simple_narrative(weather_data)


def calculate_daily_extremes(weather_records):
    """Calculate daily high/low temperatures from hourly data"""
    daily_extremes = {}

    for record in weather_records:
        date = record["date"]
        temp = record["temp_c"]

        if date not in daily_extremes:
            daily_extremes[date] = {"high": temp, "low": temp}
        else:
            daily_extremes[date]["high"] = max(daily_extremes[date]["high"], temp)
            daily_extremes[date]["low"] = min(daily_extremes[date]["low"], temp)

    return daily_extremes


def generate_historical_dataset(csv_file_path, max_records=None):
    """Generate historical dataset with narratives and measurements"""
    print(f"Loading weather data from {csv_file_path}")
    weather_records = load_historical_csv(csv_file_path)

    if not weather_records:
        print("No weather records found!")
        return []

    # Calculate daily temperature extremes from all data
    print("Calculating daily temperature extremes...")
    daily_extremes = calculate_daily_extremes(weather_records)

    # Add daily extremes to each record
    for record in weather_records:
        date = record["date"]
        if date in daily_extremes:
            record["daily_high"] = daily_extremes[date]["high"]
            record["daily_low"] = daily_extremes[date]["low"]

    if max_records and max_records > 0:
        weather_records = weather_records[:max_records]
        print(f"Processing first {len(weather_records)} records (limited by count)...")
    else:
        print(f"Processing all {len(weather_records)} records...")

    # Initialize measurement system
    measurer = NarrativeMeasurer()

    results = []

    for i, record in enumerate(weather_records):
        if i % 100 == 0:
            print(f"Processing record {i + 1}/{len(weather_records)}")

        # Setup weather history for this record
        setup_weather_history(record, weather_records)

        # Convert to weather data format
        weather_data = convert_to_weather_format(record)

        # Generate narrative using real or simple generator
        if USE_REAL_NARRATIVES:
            # Find future weather data for proper tomorrow forecast
            future_data = find_future_weather_data(record, weather_records)
            narrative = generate_real_narrative(
                weather_data, record["timestamp"], future_data
            )
        else:
            narrative = generate_simple_narrative(weather_data)

        # Measure text
        metrics = measurer.measure_narrative_text(narrative)

        # Collect result with all real weather data
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
            "feels_like": record["feels_like"],
            "humidity": record["humidity"],
            "weather_desc": weather_data["weather_desc"],
            "weather_code": record["weather_code"],
            "wind_speed": record["wind_speed"],
            "wind_gust": record["wind_gust"],
            "cloud_cover": record["cloud_cover"],
            "precipitation": record["precipitation"],
            "visibility": record["visibility"],
            "uv_index": record.get("uv_index", 0),
            "dew_point": record.get("dew_point", 0),
            "is_day": record["is_day"],
            "char_count": metrics["char_count"],
            "overflow_lines": metrics["overflow_lines"],
        }

        results.append(result)

    # Save to CSV in static directory
    output_file = os.path.join(current_dir, "narratives.csv")
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
        "feels_like",
        "humidity",
        "weather_desc",
        "weather_code",
        "wind_speed",
        "wind_gust",
        "cloud_cover",
        "precipitation",
        "visibility",
        "uv_index",
        "dew_point",
        "is_day",
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

    return results, output_file


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


def generate_html_viewer(csv_path):
    """Generate HTML viewer using template and injection script"""
    template_path = os.path.join(current_dir, "template.html")
    inject_script = os.path.join(current_dir, "inject_data.py")
    output_html = os.path.join(current_dir, "viewer.html")

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
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        test_single_narrative()
    elif len(sys.argv) > 1:
        # Use CSV path from argument
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

        results, output_path = generate_historical_dataset(csv_path, max_records)

        # Also generate HTML viewer
        if results:
            generate_html_viewer(output_path)
    else:
        print("Usage:")
        print(
            "  python generate_historical_data.py test                          # Test single narrative"
        )
        print(
            "  python generate_historical_data.py path/to/weather.csv          # Generate full dataset"
        )
        print(
            "  python generate_historical_data.py path/to/weather.csv 10       # Generate first 10 records"
        )
