"""
moon phase calculation module with leap year handling

shared between hardware and web preview server

uses november 20, 2025 new moon as reference point for better accuracy
"""

from utils.logger import log


def is_leap_year(year):
    """Check if a year is a leap year"""
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def days_in_month(year, month):
    """Get number of days in a given month, accounting for leap years"""
    days = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    if month == 2 and is_leap_year(year):
        return 29
    return days[month - 1]


def timestamp_to_date(unix_timestamp):
    """Convert Unix timestamp to (year, month, day) with proper leap year handling"""
    # Convert to days since Unix epoch
    days_since_epoch = unix_timestamp // 86400

    # Start from Unix epoch: January 1, 1970
    year = 1970
    month = 1
    day = 1

    # Add days one year at a time for accuracy
    remaining_days = days_since_epoch

    while True:
        days_this_year = 366 if is_leap_year(year) else 365
        if remaining_days >= days_this_year:
            remaining_days -= days_this_year
            year += 1
        else:
            break

    # Now add months
    month = 1
    while True:
        days_this_month = days_in_month(year, month)
        if remaining_days >= days_this_month:
            remaining_days -= days_this_month
            month += 1
        else:
            break

    # Remaining days is the day of month (0-based, so add 1)
    day = remaining_days + 1

    return year, month, day


def date_to_julian_day(year, month, day):
    """Convert date to Julian Day Number using the standard algorithm"""
    # Handle January and February as months 13 and 14 of the previous year
    if month <= 2:
        year -= 1
        month += 12

    # Gregorian calendar correction
    A = year // 100
    B = 2 - A + A // 4

    # Julian Day Number calculation
    JD = int(365.25 * (year + 4716)) + int(30.6001 * (month + 1)) + day + B - 1524.5

    return JD


def calculate_moon_phase(unix_timestamp=None, year=None, month=None, day=None):
    """
    Calculate moon phase for a given date using accurate lunar cycle calculation

    Returns phase as float 0.0-1.0 where:
    0.0 = New Moon, 0.25 = First Quarter, 0.5 = Full Moon, 0.75 = Third Quarter

    Uses November 20, 2025 06:47 UTC as reference new moon for accuracy
    """

    # Use unix timestamp if provided, otherwise use supplied date
    if unix_timestamp is not None:
        year, month, day = timestamp_to_date(unix_timestamp)
    else:
        # No date provided - cannot calculate moon phase
        return None

    # Convert to Julian Day Number
    current_jd = date_to_julian_day(year, month, day)

    # Reference: November 20, 2025 06:47 UTC is a new moon
    # Convert to Julian Day Number: November 20, 2025
    reference_jd = date_to_julian_day(2025, 11, 20)

    # Add the time portion: 06:47 UTC = 6.783 hours = 0.283 days
    reference_jd += 0.283

    # Days since reference new moon
    days_since_reference = current_jd - reference_jd

    # Average lunar month (synodic month) is 29.530588853 days
    # This is more accurate than the commonly used 29.53059
    lunar_month = 29.530588853

    # Calculate phase (0.0 to 1.0)
    phase = (days_since_reference % lunar_month) / lunar_month

    # Ensure phase is in 0.0-1.0 range
    phase = phase % 1.0
    return phase


def phase_to_icon_name(phase):
    """Convert moon phase (0.0-1.0) to icon name"""
    if phase is None:
        return "moon-new"  # Default icon if phase calculation failed

    # Normalize phase to 0.0-1.0 range
    phase = phase % 1.0

    # Define phase ranges and corresponding icons
    if phase < 0.03 or phase >= 0.97:
        return "moon-new"
    elif phase < 0.22:
        # Waxing crescent
        crescent_phase = int((phase - 0.03) / 0.19 * 6) + 1
        return f"moon-waxing-crescent-{min(crescent_phase, 6)}"
    elif phase < 0.28:
        return "moon-first-quarter"
    elif phase < 0.47:
        # Waxing gibbous
        gibbous_phase = int((phase - 0.28) / 0.19 * 6) + 1
        return f"moon-waxing-gibbous-{min(gibbous_phase, 6)}"
    elif phase < 0.53:
        return "moon-full"
    elif phase < 0.72:
        # Waning gibbous
        gibbous_phase = int((phase - 0.53) / 0.19 * 6) + 1
        return f"moon-waning-gibbous-{min(gibbous_phase, 6)}"
    elif phase < 0.78:
        return "moon-third-quarter"
    else:
        # Waning crescent
        crescent_phase = int((phase - 0.78) / 0.19 * 6) + 1
        return f"moon-waning-crescent-{min(crescent_phase, 6)}"


def get_moon_info(unix_timestamp=None, year=None, month=None, day=None):
    """Get complete moon phase information"""
    log(f"Moon phase calculation for timestamp: {unix_timestamp}")
    phase = calculate_moon_phase(unix_timestamp, year, month, day)
    log(f"Calculated moon phase value: {phase}")

    if phase is None:
        log("Moon phase calculation failed - no valid date provided")
        return None

    icon_name = phase_to_icon_name(phase)

    # Convert phase to percentage
    percentage = int(phase * 100)

    # Phase name with more precise thresholds
    if phase < 0.03 or phase >= 0.97:
        name = "New Moon"
    elif phase < 0.22:
        name = "Waxing Crescent"
    elif phase < 0.28:
        name = "First Quarter"
    elif phase < 0.47:
        name = "Waxing Gibbous"
    elif phase < 0.53:
        name = "Full Moon"
    elif phase < 0.72:
        name = "Waning Gibbous"
    elif phase < 0.78:
        name = "Third Quarter"
    else:
        name = "Waning Crescent"

    log(f"Moon phase name: {name}")

    return {"phase": phase, "name": name, "icon": icon_name, "percentage": percentage}
