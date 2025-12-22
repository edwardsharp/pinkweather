"""
weather data persistence module for saving/loading api data to sd card
"""

import json


def get_weather_data_path():
    """Get the path for weather data file on SD card"""
    return "/sd/weather_data.json"


def save_weather_data(weather_data, forecast_data, current_timestamp):
    """Save weather data and forecast to SD card with timestamp"""
    if not current_timestamp:
        print("No timestamp provided, skipping weather data save")
        return False

    data_to_save = {
        "timestamp": current_timestamp,
        "weather_data": weather_data,
        "forecast_data": forecast_data,
    }

    try:
        with open(get_weather_data_path(), "w") as f:
            json.dump(data_to_save, f)
        print(f"Weather data saved to SD card at timestamp {current_timestamp}")
        return True
    except Exception as e:
        print(f"Failed to save weather data: {e}")
        return False


def load_weather_data():
    """Load weather data from SD card"""
    weather_path = get_weather_data_path()

    try:
        with open(weather_path, "r") as f:
            data = json.load(f)

        # Validate data structure
        if "timestamp" in data and "weather_data" in data and "forecast_data" in data:
            print(f"Weather data loaded from SD card, timestamp: {data['timestamp']}")
            return data
        else:
            print("Invalid weather data structure in saved file")
            return None

    except OSError:
        print("No saved weather data found on SD card")
        return None
    except Exception as e:
        print(f"Error loading weather data: {e}")
        return None


def is_weather_data_stale(saved_timestamp, current_timestamp, max_age_hours=1):
    """Check if saved weather data is older than max_age_hours"""
    if not saved_timestamp or not current_timestamp:
        return True

    age_seconds = current_timestamp - saved_timestamp
    max_age_seconds = max_age_hours * 3600

    is_stale = age_seconds >= max_age_seconds
    age_minutes = age_seconds // 60

    print(
        f"Weather data age: {age_minutes} minutes ({'stale' if is_stale else 'fresh'})"
    )
    return is_stale


def should_refresh_weather():
    """Check if weather should be refreshed based on saved data age only"""
    # Load saved weather data
    saved_data = load_weather_data()
    if not saved_data:
        print("No saved weather data, needs refresh")
        return True

    # We can't check staleness without current time, so just check if we have data
    saved_timestamp = saved_data.get("timestamp")
    if not saved_timestamp:
        print("No timestamp in saved data, needs refresh")
        return True

    print("Saved weather data exists, will use until next scheduled refresh")
    return False
