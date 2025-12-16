"""
Centralized date/time utilities using adafruit_datetime
Provides consistent date handling for both CircuitPython hardware and web server
"""

import adafruit_datetime as datetime

# Constants
DAY_NAMES = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN']
MONTH_NAMES = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN',
               'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']

def utc_to_local(utc_timestamp, timezone_offset_hours=-5):
    """Convert UTC timestamp to local timestamp

    Args:
        utc_timestamp: Unix timestamp in UTC
        timezone_offset_hours: Hours offset from UTC (e.g., -5 for EST)

    Returns:
        Unix timestamp adjusted to local time
    """
    return utc_timestamp + (timezone_offset_hours * 3600)

def format_timestamp_to_date(timestamp):
    """Convert Unix timestamp to formatted date components
    NOTE: timestamp should already be in local time

    Args:
        timestamp: Unix timestamp (seconds since epoch) in LOCAL TIME

    Returns:
        dict: {
            'day_name': str,     # e.g. 'MON'
            'day_num': int,      # e.g. 15
            'month_name': str,   # e.g. 'DEC'
            'year': int,         # e.g. 2025
            'weekday': int       # 0=Monday, 6=Sunday
        }
    """
    # Manual time calculation to avoid datetime timezone issues
    year, month, day, hour, minute, second, weekday = _timestamp_to_components(timestamp)

    return {
        'day_name': DAY_NAMES[weekday],
        'day_num': day,
        'month_name': MONTH_NAMES[month - 1],
        'year': year,
        'weekday': weekday
    }

def format_timestamp_to_time(timestamp, format_12h=True):
    """Convert Unix timestamp to formatted time string
    NOTE: timestamp should already be in local time

    Args:
        timestamp: Unix timestamp (seconds since epoch) in LOCAL TIME
        format_12h: If True, use 12-hour format (3p), if False use 24-hour (15:00)

    Returns:
        str: Formatted time string
    """
    # Manual time calculation to avoid datetime timezone issues
    year, month, day, hour, minute, second, weekday = _timestamp_to_components(timestamp)

    if format_12h:
        if hour == 0:
            hour_12 = 12
            suffix = 'a'
        elif hour < 12:
            hour_12 = hour
            suffix = 'a'
        elif hour == 12:
            hour_12 = 12
            suffix = 'p'
        else:
            hour_12 = hour - 12
            suffix = 'p'

        # Include minutes if not zero, like original format: "9:36p"
        if minute == 0:
            return f"{hour_12}{suffix}"
        else:
            return f"{hour_12}:{minute:02d}{suffix}"
    else:
        return f"{hour:02d}:{minute:02d}"

def format_timestamp_to_hhmm(timestamp):
    """Convert Unix timestamp to HH:MM format (24-hour)
    NOTE: timestamp should already be in local time

    Args:
        timestamp: Unix timestamp (seconds since epoch) in LOCAL TIME

    Returns:
        str: Time in HH:MM format (e.g. "15:30")
    """
    # Manual time calculation to avoid datetime timezone issues
    year, month, day, hour, minute, second, weekday = _timestamp_to_components(timestamp)
    return f"{hour:02d}:{minute:02d}"

def get_hour_from_timestamp(timestamp):
    """Get hour (0-23) from Unix timestamp
    NOTE: timestamp should already be in local time

    Args:
        timestamp: Unix timestamp (seconds since epoch) in LOCAL TIME

    Returns:
        int: Hour in 24-hour format (0-23)
    """
    # Manual time calculation to avoid datetime timezone issues
    year, month, day, hour, minute, second, weekday = _timestamp_to_components(timestamp)
    return hour

def is_nighttime(timestamp):
    """Check if timestamp represents nighttime hours (6pm - 6am)
    NOTE: timestamp should already be in local time

    Args:
        timestamp: Unix timestamp (seconds since epoch) in LOCAL TIME

    Returns:
        bool: True if nighttime
    """
    hour = get_hour_from_timestamp(timestamp)
    return hour >= 18 or hour <= 6

def format_date_header(timestamp):
    """Format timestamp for header display (e.g. "MON 15 DEC")
    NOTE: timestamp should already be in local time

    Args:
        timestamp: Unix timestamp (seconds since epoch) in LOCAL TIME

    Returns:
        str: Formatted date string for header
    """
    date_info = format_timestamp_to_date(timestamp)
    return f"{date_info['day_name']} {date_info['day_num']} {date_info['month_name']}"

def categorize_time_for_narrative(timestamp):
    """Categorize timestamp for weather narrative descriptions
    NOTE: timestamp should already be in local time

    Args:
        timestamp: Unix timestamp (seconds since epoch) in LOCAL TIME

    Returns:
        str: Time category ('overnight', 'morning', 'afternoon', 'evening')
    """
    hour = get_hour_from_timestamp(timestamp)

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

def _timestamp_to_components(timestamp):
    """Convert Unix timestamp to date/time components using manual calculation

    This avoids all datetime library timezone issues by doing the math ourselves.
    Assumes timestamp is already adjusted to local time.

    Returns:
        tuple: (year, month, day, hour, minute, second, weekday)
        weekday: 0=Monday, 1=Tuesday, ..., 6=Sunday
    """
    # Constants
    SECONDS_PER_MINUTE = 60
    SECONDS_PER_HOUR = 3600
    SECONDS_PER_DAY = 86400

    # Days in each month (non-leap year)
    DAYS_IN_MONTH = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

    # Extract time of day
    days_since_epoch = int(timestamp // SECONDS_PER_DAY)
    seconds_today = int(timestamp % SECONDS_PER_DAY)

    hour = seconds_today // SECONDS_PER_HOUR
    minute = (seconds_today % SECONDS_PER_HOUR) // SECONDS_PER_MINUTE
    second = seconds_today % SECONDS_PER_MINUTE

    # Calculate weekday (Jan 1, 1970 was a Thursday, we want Monday = 0)
    # Thursday = 3, so we need offset to make Thursday = 3
    weekday = (days_since_epoch + 3) % 7

    # Calculate date (simplified algorithm)
    # Start from Unix epoch: January 1, 1970
    year = 1970

    # Handle years
    while True:
        days_in_year = 366 if _is_leap_year(year) else 365
        if days_since_epoch >= days_in_year:
            days_since_epoch -= days_in_year
            year += 1
        else:
            break

    # Handle months
    month = 1
    days_in_month = DAYS_IN_MONTH[:]
    if _is_leap_year(year):
        days_in_month[1] = 29  # February has 29 days in leap year

    for m in range(12):
        if days_since_epoch >= days_in_month[m]:
            days_since_epoch -= days_in_month[m]
            month += 1
        else:
            break

    day = days_since_epoch + 1  # +1 because days start at 1, not 0

    return year, month, day, hour, minute, second, weekday

def _is_leap_year(year):
    """Check if year is a leap year"""
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
