"""
Moon phase calculation module
Shared between hardware and web server for consistent moon phase display
"""

import time

def calculate_moon_phase(unix_timestamp=None, year=None, month=None, day=None):
    """Calculate moon phase for a given date (simplified version for CircuitPython)"""
    # Use unix timestamp if provided, convert manually without using gmtime/localtime
    if unix_timestamp is not None:
        # Convert Unix timestamp to date manually (days since Unix epoch)
        days_since_epoch = unix_timestamp // 86400
        # Approximate calculation: January 1, 1970 was day 719163 in astronomical calculations
        # This is a simplified approach for moon phase calculation
        year = 1970 + (days_since_epoch // 365)
        # Simple approximation for month/day - good enough for moon phase
        days_in_year = days_since_epoch % 365
        if days_in_year < 31:
            month = 1
            day = days_in_year + 1
        elif days_in_year < 59:
            month = 2
            day = days_in_year - 30
        elif days_in_year < 90:
            month = 3
            day = days_in_year - 58
        elif days_in_year < 120:
            month = 4
            day = days_in_year - 89
        elif days_in_year < 151:
            month = 5
            day = days_in_year - 119
        elif days_in_year < 181:
            month = 6
            day = days_in_year - 150
        elif days_in_year < 212:
            month = 7
            day = days_in_year - 180
        elif days_in_year < 243:
            month = 8
            day = days_in_year - 211
        elif days_in_year < 273:
            month = 9
            day = days_in_year - 242
        elif days_in_year < 304:
            month = 10
            day = days_in_year - 272
        elif days_in_year < 334:
            month = 11
            day = days_in_year - 303
        else:
            month = 12
            day = days_in_year - 333
    else:
        # If no timestamp provided, use reasonable defaults
        year = year or 2024
        month = month or 12
        day = day or 14

    # Julian day calculation
    if month <= 2:
        year -= 1
        month += 12

    A = year // 100
    B = 2 - A + A // 4

    JD = int(365.25 * (year + 4716)) + int(30.6001 * (month + 1)) + day + B - 1524.5

    # Days since J2000.0
    days_since_j2000 = JD - 2451545.0

    # Moon's age in days (approximate)
    # Average lunar month is about 29.53059 days
    lunar_month = 29.53059
    moon_age = (days_since_j2000 % lunar_month) / lunar_month

    return moon_age

def phase_to_icon_name(phase):
    """Convert moon phase (0.0-1.0) to icon name"""
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
    print(f"Moon phase calculation for timestamp: {unix_timestamp}")
    phase = calculate_moon_phase(unix_timestamp, year, month, day)
    print(f"Calculated moon phase value: {phase}")
    icon_name = phase_to_icon_name(phase)

    # Convert phase to percentage
    percentage = int(phase * 100)

    # Phase name
    if phase < 0.03 or phase >= 0.97:
        name = "New Moon"
    elif phase < 0.25:
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

    print(f"Moon phase name: {name}")

    return {
        'phase': phase,
        'name': name,
        'icon': icon_name,
        'percentage': percentage
    }
