"""
weather data persistence module for saving/loading api data
Accepts injected filesystem for dependency injection pattern
"""

from utils.logger import log

# Global filesystem reference
_filesystem = None
WEATHER_DATA_FILENAME = "weather_data.json"


def set_filesystem(filesystem):
    """Set the filesystem to use for weather persistence (dependency injection)"""
    global _filesystem
    _filesystem = filesystem


def save_weather_data(weather_data, forecast_data, current_timestamp):
    """Save weather data and forecast with timestamp"""
    if not current_timestamp:
        log("No timestamp provided, skipping weather data save")
        return False

    if not _filesystem or not _filesystem.is_available():
        log("No filesystem available, skipping weather data save")
        return False

    data_to_save = {
        "timestamp": current_timestamp,
        "weather_data": weather_data,
        "forecast_data": forecast_data,
    }

    if _filesystem.write_json(WEATHER_DATA_FILENAME, data_to_save):
        log(f"Weather data saved at timestamp {current_timestamp}")
        return True
    else:
        log("Failed to save weather data")
        return False


def load_weather_data():
    """Load weather data from filesystem"""
    if not _filesystem or not _filesystem.is_available():
        log("No filesystem available for loading weather data")
        return None

    data = _filesystem.read_json(WEATHER_DATA_FILENAME)

    if not data:
        log("No saved weather data found")
        return None

    # Validate data structure
    if "timestamp" in data and "weather_data" in data and "forecast_data" in data:
        log(f"Weather data loaded, timestamp: {data['timestamp']}")
        return data
    else:
        log("Invalid weather data structure in saved file")
        return None


def is_weather_data_stale(saved_timestamp, current_timestamp, max_age_hours=1):
    """Check if saved weather data is older than max_age_hours"""
    if not saved_timestamp or not current_timestamp:
        return True

    age_seconds = current_timestamp - saved_timestamp
    max_age_seconds = max_age_hours * 3600

    is_stale = age_seconds >= max_age_seconds
    age_minutes = age_seconds // 60

    log(f"Weather data age: {age_minutes} minutes ({'stale' if is_stale else 'fresh'})")
    return is_stale


def should_refresh_weather():
    """Check if weather should be refreshed based on saved data age only"""
    # Load saved weather data
    saved_data = load_weather_data()
    if not saved_data:
        log("No saved weather data, needs refresh")
        return True

    # We can't check staleness without current time, so just check if we have data
    saved_timestamp = saved_data.get("timestamp")
    if not saved_timestamp:
        log("No timestamp in saved data, needs refresh")
        return True

    log("Saved weather data exists, will use until next scheduled refresh")
    return False
