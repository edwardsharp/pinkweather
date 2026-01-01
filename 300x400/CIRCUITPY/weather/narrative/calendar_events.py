"""Calendar events and special days for weather narratives

This module handles special calendar events like holidays, awareness days,
and seasonal celebrations that should be included in weather narratives.
"""

from weather.date_utils import get_day_from_timestamp, get_month_from_timestamp


def get_calendar_events(timestamp, priority_threshold=5):
    """Get calendar events for a given timestamp

    Args:
        timestamp: Unix timestamp (local time)
        priority_threshold: Minimum priority level to include (higher = more important)

    Returns:
        list: List of event dicts with 'text', 'priority', 'short_text' keys
    """
    if not timestamp:
        return []

    month = get_month_from_timestamp(timestamp)
    day = get_day_from_timestamp(timestamp)

    events = []

    # Check all calendar events
    for event in CALENDAR_EVENTS:
        if _matches_date(event, month, day, timestamp):
            if event["priority"] >= priority_threshold:
                events.append(event)

    # Sort by priority (highest first)
    events.sort(key=lambda x: x["priority"], reverse=True)
    return events


def _matches_date(event, month, day, timestamp):
    """Check if an event matches the given date"""
    event_type = event.get("type", "fixed")

    if event_type == "fixed":
        return event["month"] == month and event["day"] == day
    elif event_type == "range":
        start_month, start_day = event["start_month"], event["start_day"]
        end_month, end_day = event["end_month"], event["end_day"]

        if start_month == end_month:
            return month == start_month and start_day <= day <= end_day
        elif start_month < end_month:
            return (
                (month == start_month and day >= start_day)
                or (start_month < month < end_month)
                or (month == end_month and day <= end_day)
            )
        else:  # crosses year boundary
            return (
                (month == start_month and day >= start_day)
                or (month > start_month)
                or (month < end_month)
                or (month == end_month and day <= end_day)
            )
    elif event_type == "nth_weekday":
        # TODO: Implement for events like "second Wednesday in April"
        return False
    elif event_type == "relative":
        # TODO: Implement for events like Chinese New Year
        return False

    return False


def get_seasonal_suggestions(month, day, temperature, conditions):
    """Get seasonal suggestions based on date and weather

    Args:
        month: Month number (1-12)
        day: Day number (1-31)
        temperature: Current temperature
        conditions: Weather conditions string

    Returns:
        list: List of suggestion dicts with 'text', 'priority', 'short_text'
    """
    suggestions = []

    # Spring suggestions (March 20 - June 20 roughly)
    if (month == 3 and day >= 20) or month in [4, 5] or (month == 6 and day <= 20):
        if temperature >= 20 and "clear" in conditions.lower():
            suggestions.append(
                {
                    "text": "Spring vibes! Get outside 'n touch grass!",
                    "short_text": "Spring vibes!",
                    "priority": 6,
                }
            )
        elif temperature >= 15:
            suggestions.append(
                {
                    "text": "Get yr shortyz out today?!",
                    "short_text": "Get yr shortyz!",
                    "priority": 7,
                }
            )

    # Summer suggestions (June 21 - September 22 roughly)
    elif (month == 6 and day >= 21) or month in [7, 8] or (month == 9 and day <= 22):
        if temperature >= 31:
            suggestions.append(
                {"text": "It's too hot!", "short_text": "Too hot!", "priority": 8}
            )
            suggestions.append(
                {"text": "Wear sunscreen!", "short_text": "Sunscreen!", "priority": 7}
            )

    return suggestions


# Calendar events database
CALENDAR_EVENTS = [
    # New Year
    {
        "month": 1,
        "day": 1,
        "text": "Happy New Year!",
        "short_text": "New Year!",
        "priority": 9,
        "type": "fixed",
    },
    # Pi Day
    {
        "month": 3,
        "day": 14,
        "text": "Pi Day! Time for π!",
        "short_text": "Pi Day!",
        "priority": 6,
        "type": "fixed",
    },
    # International Transgender Day of Visibility
    {
        "month": 3,
        "day": 31,
        "text": "Trans Day of Visibility!",
        "short_text": "TDOV!",
        "priority": 8,
        "type": "fixed",
    },
    # Sapphic Visibility Day
    {
        "month": 4,
        "day": 9,
        "text": "Sapphic Visibility Day!",
        "short_text": "Sapphic Day!",
        "priority": 7,
        "type": "fixed",
    },
    # Yoda Day
    {
        "month": 5,
        "day": 4,
        "text": "May the fourth be with you!",
        "short_text": "May the 4th!",
        "priority": 6,
        "type": "fixed",
    },
    # Talk Like Yoda Day
    {
        "month": 5,
        "day": 21,
        "text": "Talk like Yoda, you must!",
        "short_text": "Yoda Day!",
        "priority": 6,
        "type": "fixed",
    },
    # Harvey Milk Day
    {
        "month": 5,
        "day": 22,
        "text": "Harvey Milk Day!",
        "short_text": "Milk Day!",
        "priority": 7,
        "type": "fixed",
    },
    # Pride Month
    {
        "month": 6,
        "day": 1,
        "text": "Pride Month begins!",
        "short_text": "Pride!",
        "priority": 8,
        "type": "fixed",
    },
    # Stonewall Anniversary
    {
        "month": 6,
        "day": 28,
        "text": "Stonewall Anniversary!",
        "short_text": "Stonewall!",
        "priority": 8,
        "type": "fixed",
    },
    # Talk Like a Pirate Day
    {
        "month": 9,
        "day": 19,
        "text": "Arrr! Talk Like a Pirate Day!",
        "short_text": "Arrr!",
        "priority": 7,
        "type": "fixed",
    },
    # Coming Out Day
    {
        "month": 10,
        "day": 11,
        "text": "Coming Out Day!",
        "short_text": "Coming Out Day!",
        "priority": 8,
        "type": "fixed",
    },
    # Treat Yo Self Day
    {
        "month": 10,
        "day": 13,
        "text": "Treat yo self!",
        "short_text": "Treat yo self!",
        "priority": 6,
        "type": "fixed",
    },
    # Halloween
    {
        "month": 10,
        "day": 31,
        "text": "Get Spook'd!",
        "short_text": "Spooky!",
        "priority": 9,
        "type": "fixed",
    },
    # 11/11
    {
        "month": 11,
        "day": 11,
        "text": "11/11!",
        "short_text": "11/11!",
        "priority": 6,
        "type": "fixed",
    },
    # World AIDS Day
    {
        "month": 12,
        "day": 1,
        "text": "World AIDS Day",
        "short_text": "AIDS Day",
        "priority": 8,
        "type": "fixed",
    },
    # Solstices (approximate - would need astronomical calculation for exact)
    {
        "month": 6,
        "day": 21,
        "text": "Summer Solstice!",
        "short_text": "Solstice!",
        "priority": 7,
        "type": "fixed",
    },
    {
        "month": 12,
        "day": 21,
        "text": "Winter Solstice!",
        "short_text": "Solstice!",
        "priority": 7,
        "type": "fixed",
    },
    # Equinoxes (approximate)
    {
        "month": 3,
        "day": 20,
        "text": "Spring Equinox!",
        "short_text": "Spring!",
        "priority": 7,
        "type": "fixed",
    },
    {
        "month": 9,
        "day": 22,
        "text": "Fall Equinox!",
        "short_text": "Fall!",
        "priority": 7,
        "type": "fixed",
    },
]


# Conditional weather suggestions
def get_weather_suggestions(
    temperature,
    conditions,
    is_daytime=True,
    rain_chance=0,
    wind_speed=0,
    air_quality=None,
    uv_index=0,
):
    """Get weather-based suggestions

    Args:
        temperature: Current temperature in Celsius
        conditions: Weather conditions string
        is_daytime: Whether it's daytime (before 9pm)
        rain_chance: Chance of rain percentage (0-100)
        wind_speed: Wind speed
        air_quality: Air quality dict with 'aqi', 'raw_aqi', 'description'
        uv_index: UV index value

    Returns:
        list: List of suggestion dicts with 'text', 'priority', 'short_text'
    """
    suggestions = []

    # Cold weather suggestions
    if temperature <= -5:
        suggestions.extend(
            [
                {
                    "text": "Stay inside!",
                    "short_text": "Stay inside!",
                    "priority": 9,
                },
                {"text": "Dress warm!", "short_text": "Dress warm!", "priority": 8},
            ]
        )
    elif temperature <= 0:
        suggestions.extend(
            [
                {
                    "text": "Bundle up!",
                    "short_text": "Bundle up!",
                    "priority": 8,
                },
                {
                    "text": "Wear gloves outside!",
                    "short_text": "Wear gloves!",
                    "priority": 7,
                },
            ]
        )
    elif temperature <= 5:
        if wind_speed > 15:
            suggestions.append(
                {
                    "text": "Cold and windy, yuck!",
                    "short_text": "Cold & windy!",
                    "priority": 8,
                }
            )
        else:
            suggestions.append(
                {
                    "text": "Chilly; Wear a jacket!",
                    "short_text": "Wear jacket!",
                    "priority": 7,
                }
            )

    # Rain suggestions
    if (
        rain_chance > 40
        and temperature >= 20
        and is_daytime
        and "rain" not in conditions.lower()
    ):
        suggestions.append(
            {"text": "Pack an umbrella?", "short_text": "Pack umbrella?", "priority": 7}
        )

    # Nice weather suggestions
    if (
        temperature >= 20
        and temperature <= 25
        and "clear" in conditions.lower()
        and is_daytime
    ):
        suggestions.extend(
            [
                {"text": "Lovely day!", "short_text": "Lovely day!", "priority": 6},
                {
                    "text": "Get outside today!",
                    "short_text": "Get outside!",
                    "priority": 6,
                },
                {"text": "Splendid day!", "short_text": "Splendid!", "priority": 5},
                {"text": "Right nice, innit?", "short_text": "Nice!", "priority": 5},
            ]
        )

    # Hot weather suggestions
    if temperature >= 31:
        suggestions.extend(
            [
                {"text": "It's too hot!", "short_text": "Too hot!", "priority": 8},
                {"text": "Wear sunscreen!", "short_text": "Sunscreen!", "priority": 7},
            ]
        )

    # Sunny weather
    if "clear" in conditions.lower() and "sun" in conditions.lower() and is_daytime:
        suggestions.append(
            {
                "text": "Wear yr sunnyz out!",
                "short_text": "Wear yr sunnyz!",
                "priority": 6,
            }
        )

    # Air quality warnings (when AQI is not good - level 2+, which is 51+ US AQI)
    if air_quality and air_quality.get("aqi", 1) >= 2:
        raw_aqi = air_quality.get("raw_aqi", 0)
        aqi_level = air_quality.get("aqi", 1)

        if aqi_level >= 5 or raw_aqi >= 301:  # Hazardous
            suggestions.append(
                {
                    "text": "Air quality hazardous! Stay indoors!",
                    "short_text": "Hazardous AQ!",
                    "priority": 10,
                }
            )
        elif aqi_level >= 4 or raw_aqi >= 201:  # Very Unhealthy
            suggestions.append(
                {
                    "text": "Air quality very poor! Limit outdoor time",
                    "short_text": "Very poor AQ",
                    "priority": 9,
                }
            )
        elif aqi_level >= 4 or raw_aqi >= 151:  # Unhealthy
            suggestions.append(
                {
                    "text": "Air not good! Sensitive people stay inside",
                    "short_text": "Poor AQ",
                    "priority": 8,
                }
            )
        elif aqi_level >= 3 or raw_aqi >= 101:  # Moderate/Unhealthy for Sensitive
            suggestions.append(
                {
                    "text": "Air quality moderate",
                    "short_text": "Moderate AQ",
                    "priority": 7,
                }
            )
        elif aqi_level >= 2 or raw_aqi >= 51:  # Fair/Moderate
            suggestions.append(
                {
                    "text": "Air quality fair",
                    "short_text": "Fair AQ",
                    "priority": 4,
                }
            )

    # UV index warnings (daytime only)
    if is_daytime and uv_index > 0:
        if uv_index >= 11:
            suggestions.append(
                {
                    "text": f"Extreme UV ({uv_index})! avoid midday sun!",
                    "short_text": f"XTREME UV {uv_index}!",
                    "priority": 9,
                }
            )
        elif uv_index >= 8:
            suggestions.append(
                {
                    "text": f"Very high UV ({uv_index})",
                    "short_text": f"High UV {uv_index}",
                    "priority": 8,
                }
            )
        elif uv_index >= 6:
            suggestions.append(
                {
                    "text": "High UV - sunscreen essential!",
                    "short_text": "High UV!",
                    "priority": 7,
                }
            )
        elif uv_index >= 3:
            suggestions.append(
                {
                    "text": "Moderate UV",
                    "short_text": "Mod UV",
                    "priority": 5,
                }
            )

    # Wind conditions
    if wind_speed >= 40:
        suggestions.append(
            {
                "text": "Very windy! Hold onto yr buttz!",
                "short_text": "Very windy!",
                "priority": 8,
            }
        )
    elif wind_speed >= 25:
        suggestions.append(
            {
                "text": "Windy!",
                "short_text": "windy!",
                "priority": 6,
            }
        )
    elif wind_speed >= 15:
        suggestions.append(
            {
                "text": "Breezy day!",
                "short_text": "Breezy!",
                "priority": 5,
            }
        )

    return suggestions


def get_text_alternatives():
    """Get dictionary of text alternatives for shortening

    Returns:
        dict: Mapping of long text to shorter alternatives
    """
    return {
        "Tomorrow": "Tmrrw",
        "tomorrow": "tmrrw",
        "expected": "exp",
        "around": "~",
        "afternoon": "PM",
        "morning": "AM",
        "evening": "eve",
        "overnight": "o/n",
        "currently": "now",
        "likely": "prob",
        "possible": "poss",
        "thunderstorms": "t-storms",
        "Thunderstorms": "T-storms",
        "precipitation": "precip",
        "temperature": "temp",
        "New moon tonight.": "New moon!",
        "Full moon tonight.": "Full moon!",
        "clearing": "clear",
        "starting": "start",
        "expected to": "exp to",
    }
