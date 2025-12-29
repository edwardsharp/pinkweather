"""
weather history persistence module for storing yesterday's temperatures
Refactored to use dependency injection for data sources
"""

import json

from utils.logger import log, log_error

from weather.date_utils import _timestamp_to_components

# Global filesystem reference (for hardware SD card storage)
_filesystem = None
WEATHER_HISTORY_FILENAME = "weather_history.json"

# Global history data source (for dependency injection)
_history_data_source = None


def set_filesystem(filesystem):
    """Set the filesystem to use for weather history (hardware SD card mode)"""
    global _filesystem
    _filesystem = filesystem


def set_history_data_source(data_source):
    """Set a custom data source for weather history (dependency injection)

    The data_source should have methods:
    - get_yesterday_data(current_timestamp) -> dict or None
    - store_today_data(timestamp, current_temp, high_temp, low_temp) -> bool
    """
    global _history_data_source
    _history_data_source = data_source


def get_date_string(timestamp):
    """Convert timestamp to YYYY-MM-DD format"""
    year, month, day, _, _, _, _ = _timestamp_to_components(timestamp)
    return f"{year:04d}-{month:02d}-{day:02d}"


def _filesystem_available():
    """Check if filesystem is available for weather history"""
    return _filesystem is not None and _filesystem.is_available()


def load_weather_history():
    """Load weather history from filesystem (hardware mode only)"""
    if not _filesystem_available():
        return {}

    data = _filesystem.read_json(WEATHER_HISTORY_FILENAME)

    if data is None:
        # File doesn't exist, create it
        log(f"Weather history file not found, creating: {WEATHER_HISTORY_FILENAME}")
        empty_history = {}
        if save_weather_history(empty_history):
            log("Weather history file created successfully")
        else:
            log("Failed to create weather history file")
        return empty_history

    return data


def save_weather_history(history_data):
    """Save weather history to filesystem (hardware mode only)"""
    if not _filesystem_available():
        return False

    if _filesystem.write_json(WEATHER_HISTORY_FILENAME, history_data):
        return True
    else:
        log_error("Error saving weather history")
        return False


def store_today_temperatures(current_timestamp, current_temp, high_temp, low_temp):
    """Store today's temperatures in history (using injected data source if available)"""
    # Use injected data source if available (preview mode)
    if _history_data_source:
        return _history_data_source.store_today_data(
            current_timestamp, current_temp, high_temp, low_temp
        )

    # Fall back to filesystem storage (hardware mode)
    if not current_timestamp:
        return False

    today_date = get_date_string(current_timestamp)
    history = load_weather_history()
    history[today_date] = {"current": current_temp, "high": high_temp, "low": low_temp}

    # Keep only last 10 days to save space
    dates = sorted(history.keys())
    if len(dates) > 10:
        for old_date in dates[:-10]:
            del history[old_date]

    return save_weather_history(history)


def get_yesterday_temperatures(current_timestamp):
    """Get yesterday's temperatures (using injected data source if available)"""
    # Use injected data source if available (preview mode)
    if _history_data_source:
        # print(f"DEBUG: Using injected data source for timestamp {current_timestamp}")
        result = _history_data_source.get_yesterday_data(current_timestamp)
        # print(f"DEBUG: Injected data source returned: {result}")
        return result

    # Fall back to filesystem lookup (hardware mode)
    # print(f"DEBUG: Using filesystem lookup for timestamp {current_timestamp}")
    if not current_timestamp:
        return None

    yesterday_timestamp = current_timestamp - 86400
    yesterday_date = get_date_string(yesterday_timestamp)
    history = load_weather_history()
    result = history.get(yesterday_date)
    # print(f"DEBUG: Filesystem lookup returned: {result}")
    return result


def generate_temperature_comparison(current_temp, yesterday_current):
    """Generate temperature comparison text given current and yesterday temps (pure function)"""
    if yesterday_current is None or current_temp is None:
        return None

    temp_diff = current_temp - yesterday_current

    if temp_diff >= 5:
        return "<red><bi>much</bi> warmer than yesterday.</red>"
    elif temp_diff >= 3:
        return "<red>warmer than yesterday.</red>"
    elif temp_diff >= 1:
        return "<red><i>lil'</i> warmer than yesterday.</red>"
    elif temp_diff <= -5:
        return "<red><bi>much</bi> colder than yesterday.</red>"
    elif temp_diff <= -3:
        return "<red>colder than yesterday.</red>"
    elif temp_diff <= -1:
        return "<red><i>lil'</i> colder than yesterday.</red>"
    else:
        return "about the same as yesterday."


def compare_with_yesterday(current_temp, high_temp, low_temp, current_timestamp):
    """Compare today's temperatures with yesterday and return comparison text"""
    # print(
    #     f"DEBUG: compare_with_yesterday called with temp {current_temp}, timestamp {current_timestamp}"
    # )
    yesterday_data = get_yesterday_temperatures(current_timestamp)

    if not yesterday_data:
        # print("DEBUG: No yesterday data available for comparison")
        return None

    # Use the reusable comparison logic
    yesterday_current = yesterday_data.get("current")
    # print(f"DEBUG: Comparing {current_temp} vs {yesterday_current}")
    comparison = generate_temperature_comparison(current_temp, yesterday_current)
    # print(f"DEBUG: Generated comparison: {comparison}")
    return comparison
