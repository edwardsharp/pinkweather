"""
weather history persistence module for storing yesterday's temperatures
handles both sd card storage (hardware) and cache file storage (web preview)
"""

import json
import os

from date_utils import _timestamp_to_components
from logger import log, log_error


def get_date_string(timestamp):
    """Convert timestamp to YYYY-MM-DD format"""
    year, month, day, _, _, _, _ = _timestamp_to_components(timestamp)
    return f"{year:04d}-{month:02d}-{day:02d}"


def get_history_file_path():
    """Get the appropriate path for weather history file"""
    try:
        # Try SD card path for hardware
        try:
            os.stat("/sd")
            return "/sd/weather_history.json"
        except OSError:
            pass
    except:
        pass

    # Fallback to cache directory for web preview
    # Find the web/.cache directory regardless of current working directory
    current_dir = os.getcwd()
    if "web" in current_dir:
        # Running from web directory
        cache_dir = ".cache"
    else:
        # Running from project root
        cache_dir = "web/.cache"

    try:
        os.stat(cache_dir)
    except OSError:
        os.makedirs(cache_dir)
    return cache_dir + "/weather_history.json"


def load_weather_history():
    """Load weather history from file"""
    history_path = get_history_file_path()

    try:
        with open(history_path, "r") as f:
            return json.load(f)
    except OSError:
        # File doesn't exist, create it
        log(f"Weather history file not found, creating: {history_path}")
        empty_history = {}
        if save_weather_history(empty_history):
            log("Weather history file created successfully")
        else:
            log("Failed to create weather history file")
        return empty_history
    except Exception as e:
        log(f"Error loading weather history: {e}")

    return {}


def save_weather_history(history_data):
    """Save weather history to file"""
    history_path = get_history_file_path()

    try:
        with open(history_path, "w") as f:
            json.dump(history_data, f, indent=2)
        return True
    except Exception as e:
        log_error(f"Error saving weather history: {e}")
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

    # Keep only last 7 days to save space
    dates = sorted(history.keys())
    if len(dates) > 7:
        for old_date in dates[:-7]:
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


def compare_with_yesterday(current_temp, high_temp, low_temp, current_timestamp):
    """Compare today's temperatures with yesterday and return comparison text"""
    yesterday_data = get_yesterday_temperatures(current_timestamp)

    if not yesterday_data:
        return None

    # Use current temp for primary comparison
    yesterday_current = yesterday_data.get("current")
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
