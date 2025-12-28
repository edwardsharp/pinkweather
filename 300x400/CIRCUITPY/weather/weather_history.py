"""
weather history persistence module for storing yesterday's temperatures
Accepts injected filesystem for dependency injection pattern
"""

import json

from utils.logger import log, log_error

from weather.date_utils import _timestamp_to_components

# Global filesystem reference
_filesystem = None
WEATHER_HISTORY_FILENAME = "weather_history.json"


def set_filesystem(filesystem):
    """Set the filesystem to use for weather history (dependency injection)"""
    global _filesystem
    _filesystem = filesystem


def get_date_string(timestamp):
    """Convert timestamp to YYYY-MM-DD format"""
    year, month, day, _, _, _, _ = _timestamp_to_components(timestamp)
    return f"{year:04d}-{month:02d}-{day:02d}"


def _filesystem_available():
    """Check if filesystem is available for weather history"""
    return _filesystem is not None and _filesystem.is_available()


def load_weather_history():
    """Load weather history from filesystem"""
    if not _filesystem_available():
        # No storage available (e.g., preview without filesystem injection)
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
    """Save weather history to filesystem"""
    if not _filesystem_available():
        # No storage available
        return False

    if _filesystem.write_json(WEATHER_HISTORY_FILENAME, history_data):
        return True
    else:
        log_error("Error saving weather history")
        return False


def store_today_temperatures(current_timestamp, current_temp, high_temp, low_temp):
    """Store today's temperatures in history"""
    if not current_timestamp:
        return False

    today_date = get_date_string(current_timestamp)

    # Load existing history
    history = load_weather_history()

    # Store today's data
    history[today_date] = {"current": current_temp, "high": high_temp, "low": low_temp}

    # Keep only last 10 days to save space
    dates = sorted(history.keys())
    if len(dates) > 10:
        for old_date in dates[:-10]:
            del history[old_date]

    return save_weather_history(history)


def get_yesterday_temperatures(current_timestamp):
    """Get yesterday's temperatures"""
    if not current_timestamp:
        return None

    # Calculate yesterday's timestamp (subtract 24 hours)
    yesterday_timestamp = current_timestamp - 86400
    yesterday_date = get_date_string(yesterday_timestamp)

    # Load history
    history = load_weather_history()

    return history.get(yesterday_date)


def generate_temperature_comparison(current_temp, yesterday_current):
    """Generate temperature comparison text given current and yesterday temps"""
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
    yesterday_data = get_yesterday_temperatures(current_timestamp)

    if not yesterday_data:
        return None

    # Use the reusable comparison logic
    yesterday_current = yesterday_data.get("current")
    return generate_temperature_comparison(current_temp, yesterday_current)
