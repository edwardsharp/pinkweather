"""
Web-specific weather history manager
Handles both real API data (with file storage) and mock data (in-memory)
"""

import json
import os
import sys
from datetime import datetime

# Global in-memory history for mock data
_mock_history_cache = {}


def get_date_string(timestamp):
    """Convert timestamp to YYYY-MM-DD format"""
    dt = datetime.fromtimestamp(timestamp)
    return dt.strftime("%Y-%m-%d")


def get_web_history_file_path():
    """Get history file path for web preview (real API data only)"""
    cache_dir = ".cache"
    try:
        os.stat(cache_dir)
    except OSError:
        os.makedirs(cache_dir)
    return os.path.join(cache_dir, "weather_history.json")


def load_web_history():
    """Load weather history from web cache file"""
    history_path = get_web_history_file_path()
    try:
        with open(history_path, "r") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def save_web_history(history_data):
    """Save weather history to web cache file"""
    history_path = get_web_history_file_path()
    try:
        with open(history_path, "w") as f:
            json.dump(history_data, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving web history: {e}")
        return False


def store_real_weather_history(current_timestamp, current_temp, high_temp, low_temp):
    """Store real weather data to file for web preview"""
    if not current_timestamp:
        return False

    today_date = get_date_string(current_timestamp)
    history = load_web_history()

    # Store today's data
    history[today_date] = {"current": current_temp, "high": high_temp, "low": low_temp}

    # Keep only last 10 days
    dates = sorted(history.keys())
    if len(dates) > 10:
        for old_date in dates[:-10]:
            del history[old_date]

    return save_web_history(history)


def compute_mock_history(mock_data):
    """Compute mock history from CSV data (in-memory only)"""
    global _mock_history_cache
    from datetime import timedelta

    print(f"DEBUG: compute_mock_history called with mock_data type: {type(mock_data)}")

    if not mock_data:
        print("DEBUG: No mock_data provided")
        return {}

    try:
        # Extract forecast data
        forecast_data = mock_data.get("forecast", mock_data)
        print(f"DEBUG: Extracted forecast_data type: {type(forecast_data)}")
        if isinstance(forecast_data, dict):
            print(f"DEBUG: forecast_data keys: {list(forecast_data.keys())}")
        if not isinstance(forecast_data, dict) or "list" not in forecast_data:
            print("DEBUG: forecast_data is not valid dict or missing 'list' key")
            return {}

        print(f"DEBUG: forecast_data['list'] has {len(forecast_data['list'])} items")

        # Group forecast items by date
        daily_temps = {}

        for i, item in enumerate(forecast_data["list"]):
            if "dt" not in item or "main" not in item:
                continue

            item_timestamp = item["dt"]
            date_str = get_date_string(item_timestamp)
            temp = item["main"]["temp"]

            # Debug first few items to see timestamp range
            if i < 5:
                from datetime import datetime

                readable_time = datetime.fromtimestamp(item_timestamp)
                print(
                    f"DEBUG: Item {i}: {item_timestamp} -> {readable_time} -> {date_str}, temp={temp}"
                )

            if date_str not in daily_temps:
                daily_temps[date_str] = {
                    "temps": [temp],
                    "first_temp": temp,
                }
            else:
                daily_temps[date_str]["temps"].append(temp)

        # Calculate daily high/low
        mock_history = {}
        for date_str, day_data in daily_temps.items():
            temps = day_data["temps"]
            if len(temps) > 0:
                mock_history[date_str] = {
                    "current": day_data["first_temp"],
                    "high": max(temps),
                    "low": min(temps),
                }

        # Add historical days from actual CSV data to enable yesterday comparisons
        print(
            f"DEBUG: Attempting to add historical data. mock_history has {len(mock_history)} days"
        )
        if mock_history and isinstance(forecast_data, dict) and "list" in forecast_data:
            # Get the raw CSV data by importing open_meteo_converter
            try:
                print("DEBUG: Importing OpenMeteoConverter...")
                from open_meteo_converter import OpenMeteoConverter

                # Find the CSV file - try to determine scenario
                csv_file = None
                print("DEBUG: Looking for CSV files...")
                for scenario_file in [
                    "../misc/open-meteo-40.65N73.98W25m.csv",
                    "../misc/open-meteo-43.70N79.40W165m.csv",
                ]:
                    print(f"DEBUG: Checking if {scenario_file} exists...")
                    if os.path.exists(scenario_file):
                        csv_file = scenario_file
                        print(f"DEBUG: Found CSV file: {csv_file}")
                        break
                    else:
                        print(f"DEBUG: File {scenario_file} does not exist")

                if csv_file:
                    print(f"DEBUG: Creating converter for {csv_file}")
                    # Create converter to read raw CSV data
                    converter = OpenMeteoConverter(csv_file)
                    converter._parse_csv()
                    print(
                        f"DEBUG: CSV parsed, hourly_data has {len(converter.hourly_data)} rows"
                    )

                    # Get the date range we need (10 days before earliest forecast date)
                    earliest_date_str = min(mock_history.keys())
                    earliest_date = datetime.fromisoformat(earliest_date_str).date()
                    print(
                        f"DEBUG: Earliest forecast date: {earliest_date_str}, looking back 10 days"
                    )

                    # Add historical days from CSV data
                    for days_back in range(1, 11):  # Look back up to 10 days
                        historical_date = earliest_date - timedelta(days=days_back)
                        historical_date_str = historical_date.strftime("%Y-%m-%d")
                        print(
                            f"DEBUG: Looking for historical data for {historical_date_str}"
                        )

                        if historical_date_str not in mock_history:
                            # Find hourly data for this historical date
                            historical_temps = []
                            rows_found = 0
                            for hourly_row in converter.hourly_data:
                                if hourly_row.get("time", "").startswith(
                                    historical_date_str
                                ):
                                    rows_found += 1
                                    temp_str = hourly_row.get("temperature_2m (°C)", "")
                                    if temp_str and temp_str != "NaN":
                                        try:
                                            temp = float(temp_str)
                                            historical_temps.append(temp)
                                        except ValueError:
                                            pass

                            print(
                                f"DEBUG: Found {rows_found} CSV rows for {historical_date_str}, {len(historical_temps)} valid temps"
                            )

                            # If we found historical temperature data for this date
                            if historical_temps:
                                mock_history[historical_date_str] = {
                                    "current": historical_temps[
                                        0
                                    ],  # First temp of day as "current"
                                    "high": max(historical_temps),
                                    "low": min(historical_temps),
                                }
                                print(
                                    f"DEBUG: Added historical day {historical_date_str} from CSV: current={historical_temps[0]:.1f}°, high={max(historical_temps):.1f}°, low={min(historical_temps):.1f}°"
                                )

                        # Stop if we have enough historical data
                        if len(mock_history) >= 10:
                            print("DEBUG: Reached 10 days of history, stopping")
                            break
                else:
                    print("DEBUG: No CSV file found")

            except Exception as e:
                print(f"DEBUG: Failed to load historical CSV data: {e}")
                import traceback

                traceback.print_exc()
        else:
            print("DEBUG: Conditions not met for historical data loading")

        # Keep only last 10 days
        dates = sorted(mock_history.keys())
        if len(dates) > 10:
            mock_history = {date: mock_history[date] for date in dates[-10:]}

        _mock_history_cache = mock_history
        print(f"DEBUG: Computed mock history with {len(mock_history)} days")
        print(f"DEBUG: Mock history dates: {sorted(mock_history.keys())}")
        for date, data in sorted(mock_history.items()):
            print(
                f"DEBUG:   {date}: current={data['current']:.1f}°, high={data['high']:.1f}°, low={data['low']:.1f}°"
            )
        return mock_history

    except Exception as e:
        print(f"Error computing mock history: {e}")
        return {}


def get_yesterday_for_web(current_timestamp, use_mock=False):
    """Get yesterday's data for web preview"""
    if not current_timestamp:
        print("DEBUG: No current_timestamp provided")
        return None

    yesterday_timestamp = current_timestamp - 86400
    yesterday_date = get_date_string(yesterday_timestamp)
    print(f"DEBUG: Looking for yesterday_date = {yesterday_date}, use_mock={use_mock}")

    if use_mock:
        # Use in-memory mock history
        result = _mock_history_cache.get(yesterday_date)
        print(
            f"DEBUG: Mock history cache has {len(_mock_history_cache)} days: {sorted(_mock_history_cache.keys())}"
        )
        print(f"DEBUG: Mock result for {yesterday_date}: {result}")
        return result
    else:
        # Use real file-based history
        history = load_web_history()
        print(f"DEBUG: Web history file contents: {history}")
        result = history.get(yesterday_date)
        print(f"DEBUG: File result for {yesterday_date}: {result}")
        return result


def compare_with_yesterday_web(
    current_temp, high_temp, low_temp, current_timestamp, use_mock=False
):
    """Web-specific yesterday comparison that handles both mock and real data"""
    print(
        f"DEBUG: compare_with_yesterday_web called with current_temp={current_temp}, timestamp={current_timestamp}, use_mock={use_mock}"
    )

    yesterday_data = get_yesterday_for_web(current_timestamp, use_mock)
    print(f"DEBUG: yesterday_data = {yesterday_data}")

    if not yesterday_data:
        print("DEBUG: No yesterday data found, returning None")
        return None

    # Import and use the core comparison logic from weather_history
    circuitpy_path = os.path.join(
        os.path.dirname(__file__), "..", "300x400", "CIRCUITPY"
    )
    if circuitpy_path not in sys.path:
        sys.path.insert(0, circuitpy_path)

    from weather_history import generate_temperature_comparison

    # Use the reusable core comparison logic
    yesterday_current = yesterday_data.get("current")
    print(f"DEBUG: current_temp={current_temp}, yesterday_current={yesterday_current}")

    result = generate_temperature_comparison(current_temp, yesterday_current)
    print(f"DEBUG: comparison result = {result}")
    return result
