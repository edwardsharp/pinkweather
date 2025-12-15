"""
Centralized date/time utilities using adafruit_datetime
Provides consistent date handling for both CircuitPython hardware and web server
"""

import adafruit_datetime as datetime

# Constants
DAY_NAMES = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN']
MONTH_NAMES = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN',
               'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']

def format_timestamp_to_date(timestamp, timezone_offset_hours=-5):
    """Convert Unix timestamp to formatted date components

    Args:
        timestamp: Unix timestamp (seconds since epoch)
        timezone_offset_hours: Timezone offset from UTC (default: -5 for EST)

    Returns:
        dict: {
            'day_name': str,     # e.g. 'MON'
            'day_num': int,      # e.g. 15
            'month_name': str,   # e.g. 'DEC'
            'year': int,         # e.g. 2025
            'weekday': int       # 0=Monday, 6=Sunday
        }
    """
    local_timestamp = timestamp + (timezone_offset_hours * 3600)
    dt = datetime.datetime.fromtimestamp(local_timestamp)

    return {
        'day_name': DAY_NAMES[dt.weekday()],
        'day_num': dt.day,
        'month_name': MONTH_NAMES[dt.month - 1],
        'year': dt.year,
        'weekday': dt.weekday()
    }

def format_timestamp_to_time(timestamp, timezone_offset_hours=-5, format_12h=True):
    """Convert Unix timestamp to formatted time string

    Args:
        timestamp: Unix timestamp (seconds since epoch)
        timezone_offset_hours: Timezone offset from UTC (default: -5 for EST)
        format_12h: If True, use 12-hour format (3p), if False use 24-hour (15:00)

    Returns:
        str: Formatted time string
    """
    local_timestamp = timestamp + (timezone_offset_hours * 3600)
    dt = datetime.datetime.fromtimestamp(local_timestamp)

    if format_12h:
        if dt.hour == 0:
            hour_12 = 12
            suffix = 'a'
        elif dt.hour < 12:
            hour_12 = dt.hour
            suffix = 'a'
        elif dt.hour == 12:
            hour_12 = 12
            suffix = 'p'
        else:
            hour_12 = dt.hour - 12
            suffix = 'p'

        # Include minutes if not zero, like original format: "9:36p"
        if dt.minute == 0:
            return f"{hour_12}{suffix}"
        else:
            return f"{hour_12}:{dt.minute:02d}{suffix}"
    else:
        return f"{dt.hour:02d}:{dt.minute:02d}"

def format_timestamp_to_hhmm(timestamp, timezone_offset_hours=-5):
    """Convert Unix timestamp to HH:MM format (24-hour)

    Args:
        timestamp: Unix timestamp (seconds since epoch)
        timezone_offset_hours: Timezone offset from UTC (default: -5 for EST)

    Returns:
        str: Time in HH:MM format (e.g. "15:30")
    """
    local_timestamp = timestamp + (timezone_offset_hours * 3600)
    dt = datetime.datetime.fromtimestamp(local_timestamp)
    return f"{dt.hour:02d}:{dt.minute:02d}"

def get_hour_from_timestamp(timestamp, timezone_offset_hours=-5):
    """Get hour (0-23) from Unix timestamp

    Args:
        timestamp: Unix timestamp (seconds since epoch)
        timezone_offset_hours: Timezone offset from UTC (default: -5 for EST)

    Returns:
        int: Hour in 24-hour format (0-23)
    """
    local_timestamp = timestamp + (timezone_offset_hours * 3600)
    dt = datetime.datetime.fromtimestamp(local_timestamp)
    return dt.hour

def is_nighttime(timestamp, timezone_offset_hours=-5):
    """Check if timestamp represents nighttime hours (6pm - 6am)

    Args:
        timestamp: Unix timestamp (seconds since epoch)
        timezone_offset_hours: Timezone offset from UTC (default: -5 for EST)

    Returns:
        bool: True if nighttime
    """
    hour = get_hour_from_timestamp(timestamp, timezone_offset_hours)
    return hour >= 18 or hour <= 6

def format_date_header(timestamp, timezone_offset_hours=-5):
    """Format timestamp for header display (e.g. "MON 15 DEC")

    Args:
        timestamp: Unix timestamp (seconds since epoch)
        timezone_offset_hours: Timezone offset from UTC (default: -5 for EST)

    Returns:
        str: Formatted date string for header
    """
    date_info = format_timestamp_to_date(timestamp, timezone_offset_hours)
    return f"{date_info['day_name']} {date_info['day_num']} {date_info['month_name']}"

def categorize_time_for_narrative(timestamp, timezone_offset_hours=-5):
    """Categorize timestamp for weather narrative descriptions

    Args:
        timestamp: Unix timestamp (seconds since epoch)
        timezone_offset_hours: Timezone offset from UTC (default: -5 for EST)

    Returns:
        str: Time category ('overnight', 'morning', 'afternoon', 'evening')
    """
    hour = get_hour_from_timestamp(timestamp, timezone_offset_hours)

    if 0 <= hour <= 8:
        return 'overnight'
    elif 9 <= hour <= 11:
        return 'morning'
    elif 12 <= hour <= 17:
        return 'afternoon'
    else:
        return 'evening'


def parse_time_string_to_hour(time_str):
    """Parse time string to hour (24-hour format)

    Args:
        time_str: Time string in formats like "4:28p", "17:28", "4:28pm"

    Returns:
        int: Hour in 24-hour format (0-23), or None if parsing fails
    """
    if not time_str:
        return None

    try:
        # Handle formats like "4:28p", "17:28", "4:28pm"
        time_str = time_str.lower().strip()

        if 'p' in time_str and ':' in time_str:
            # PM format like "4:28p"
            hour_part = time_str.split(':')[0]
            hour = int(hour_part)
            if hour != 12:
                hour += 12
            return hour
        elif 'a' in time_str and ':' in time_str:
            # AM format like "7:31a"
            hour_part = time_str.split(':')[0]
            hour = int(hour_part)
            if hour == 12:
                hour = 0
            return hour
        elif ':' in time_str:
            # 24-hour format like "17:28"
            return int(time_str.split(':')[0])
        else:
            # No recognizable format
            return None
    except:
        return None  # Parse failure
