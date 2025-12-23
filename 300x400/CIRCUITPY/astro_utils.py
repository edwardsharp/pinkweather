"""
astronomical utilities for zodiac signs and celestial calculations
"""

from bisect import bisect


def get_zodiac_sign(month, day):
    """Get zodiac sign for given month and day

    Args:
        month: Month number (1-12)
        day: Day number (1-31)

    Returns:
        str: Three-letter zodiac sign abbreviation
    """
    # Zodiac sign boundaries with end dates (month, day, sign)
    # Based on astronomical dates, not astrological
    signs = [
        (1, 20, "Cap"),  # Capricorn ends Jan 20
        (2, 18, "Aqu"),  # Aquarius ends Feb 18
        (3, 20, "Pis"),  # Pisces ends Mar 20
        (4, 20, "Ari"),  # Aries ends Apr 20
        (5, 21, "Tau"),  # Taurus ends May 21
        (6, 21, "Gem"),  # Gemini ends Jun 21
        (7, 22, "Can"),  # Cancer ends Jul 22
        (8, 23, "Leo"),  # Leo ends Aug 23
        (9, 23, "Vir"),  # Virgo ends Sep 23
        (10, 23, "Lib"),  # Libra ends Oct 23
        (11, 22, "Sco"),  # Scorpio ends Nov 22
        (12, 22, "Sag"),  # Sagittarius ends Dec 22
        (12, 31, "Cap"),  # Capricorn starts Dec 23
    ]

    return signs[bisect(signs, (month, day))][2]


def get_zodiac_sign_from_timestamp(timestamp):
    """Get zodiac sign from Unix timestamp

    Args:
        timestamp: Unix timestamp (seconds since epoch)

    Returns:
        str: Three-letter zodiac sign abbreviation
    """
    from date_utils import _timestamp_to_components

    year, month, day, hour, minute, second, weekday = _timestamp_to_components(
        timestamp
    )
    return get_zodiac_sign(month, day)


# Test cases
if __name__ == "__main__":
    # Test some known dates
    test_cases = [
        (3, 9, "Pis"),  # March 9 = Pisces
        (6, 30, "Can"),  # June 30 = Cancer
        (1, 15, "Cap"),  # January 15 = Capricorn
        (12, 25, "Cap"),  # December 25 = Capricorn
        (7, 4, "Can"),  # July 4 = Cancer
        (9, 15, "Vir"),  # September 15 = Virgo
    ]

    for month, day, expected in test_cases:
        result = get_zodiac_sign(month, day)
        print(
            f"{month}/{day}: {result} (expected: {expected}) {'✓' if result == expected else '✗'}"
        )
