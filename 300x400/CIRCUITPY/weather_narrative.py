"""
weather narrative generator - creates contextual weather description text string
"""

import moon_phase
from date_utils import get_hour_from_timestamp
from logger import log
from weather_history import compare_with_yesterday


def get_weather_narrative(weather_data, forecast_data, current_timestamp=None):
    """Generate dynamic weather narrative based on current conditions and forecast

    Args:
        weather_data: Current weather data dict with temp, feels_like, weather, etc.
        forecast_data: List of forecast items for next ~24 hours
        current_timestamp: Unix timestamp for current time (in local time)

    Returns:
        String: contextual weather description
    """
    if not weather_data:
        return "Weather data unavailable."

    # Get current local time info using centralized utilities
    if not current_timestamp:
        return "Weather narrative unavailable - no timestamp provided"

    current_hour = get_hour_from_timestamp(current_timestamp)

    # Extract key current conditions
    current_temp = weather_data.get("current_temp", 0)
    feels_like = weather_data.get("feels_like", current_temp)
    high_temp = weather_data.get("high_temp", current_temp)
    low_temp = weather_data.get("low_temp", current_temp)
    weather_desc = weather_data.get("weather_desc", "").lower()
    sunset_timestamp = weather_data.get("sunset_timestamp")
    humidity = weather_data.get("humidity", 0)
    wind_speed = weather_data.get("wind_speed", 0)
    wind_gust = weather_data.get("wind_gust", 0)

    # Determine if it's evening by comparing current time to sunset timestamp
    if sunset_timestamp:
        sunset_hour = get_hour_from_timestamp(sunset_timestamp)
        is_evening = current_hour >= sunset_hour
    else:
        is_evening = False  # Can't determine, assume not evening

    # Build narrative components
    narrative_parts = []

    # 1. Current conditions with temperature context
    current_conditions = _describe_current_conditions(
        weather_desc,
        current_temp,
        feels_like,
        high_temp,
        low_temp,
        humidity,
        wind_speed,
        wind_gust,
    )

    # Add yesterday comparison if available
    yesterday_comparison = compare_with_yesterday(
        current_temp, high_temp, low_temp, current_timestamp
    )
    if yesterday_comparison:
        current_conditions += f", {yesterday_comparison}"

    narrative_parts.append(current_conditions)

    # 2. Current precipitation status
    current_precip = _describe_current_precipitation(weather_desc, forecast_data)
    if current_precip:
        narrative_parts.append(current_precip)

    # 3. Upcoming precipitation in next few hours
    upcoming_precip = _analyze_upcoming_precipitation(forecast_data)
    if upcoming_precip:
        narrative_parts.append(upcoming_precip)

    # 4. Tomorrow's forecast (include more often, not just evenings)
    if forecast_data:
        tomorrow_info = _describe_tomorrow_outlook(
            forecast_data, weather_desc, current_timestamp
        )
        if tomorrow_info:
            narrative_parts.append(tomorrow_info)

    # 5. Moon phase if notable
    if current_timestamp:
        moon_info = _describe_moon_phase(current_timestamp)
        if moon_info:
            narrative_parts.append(moon_info)

    # Join parts and ensure it fits display constraints
    full_narrative = ". ".join(narrative_parts) + "."

    # If narrative is short and we have tomorrow's forecast, make sure to include it
    if (
        len(full_narrative) < 200
        and forecast_data
        and not any("Tomorrow:" in part for part in narrative_parts)
    ):
        tomorrow_info = _describe_tomorrow_outlook(
            forecast_data, weather_desc, current_timestamp
        )
        if tomorrow_info:
            full_narrative = full_narrative[:-1] + tomorrow_info + "."

    return _truncate_for_display(full_narrative)


def _describe_current_conditions(
    weather_desc,
    current_temp,
    feels_like,
    high_temp,
    low_temp,
    humidity=0,
    wind_speed=0,
    wind_gust=0,
):
    """Generate opening statement about current conditions with temperature context"""
    # Clean up weather description
    if "overcast" in weather_desc:
        condition = "Overcast"
    elif "clear" in weather_desc:
        condition = "Clear"
    elif "partly" in weather_desc or "scattered" in weather_desc:
        condition = "Partly cloudy"
    elif "cloudy" in weather_desc or "clouds" in weather_desc:
        condition = "Cloudy"
    elif "rain" in weather_desc:
        condition = "Rainy"
    elif "snow" in weather_desc:
        condition = "Snowy"
    elif "fog" in weather_desc or "mist" in weather_desc:
        condition = "Foggy"
    else:
        condition = weather_desc.title()

    # Add temperature context
    temp_context = _get_temperature_context(current_temp)

    # Build temperature description with feels-like explanation
    temp_diff = abs(feels_like - current_temp)
    if temp_diff >= 3:
        feels_like_reason = _explain_feels_like(
            current_temp, feels_like, humidity, wind_speed, wind_gust
        )
        if feels_like_reason:
            temp_desc = f"<h>{current_temp:g}</h>° (<i>feels like</i> <h>{feels_like:g}</h>° {feels_like_reason})"
        else:
            temp_desc = (
                f"<h>{current_temp:g}</h>° (<i>feels like</i> <h>{feels_like:g}</h>°)"
            )
    else:
        temp_desc = f"<h>{current_temp:g}</h>°"

    # Add high/low more often - if there's a meaningful range or short text
    temp_range = high_temp - low_temp
    if temp_range >= 15:
        # Very large daily temperature swing - highlight in red
        temp_desc += (
            f", ranging <red><h>{low_temp:g}</h>° to <h>{high_temp:g}</h>°</red>"
        )
    elif temp_range >= 10:
        # Moderate swing - make it bold
        temp_desc += f", ranging <b><h>{low_temp:g}</h>° to <h>{high_temp:g}</h>°</b>"
    elif temp_range >= 3:  # Lower threshold to show range more often
        temp_desc += f", ranging <h>{low_temp:g}</h>° to <h>{high_temp:g}</h>°"

    # Highlight extreme temperature contexts
    if temp_context:
        if temp_context in ["bitterly cold", "freezing", "extremely hot"]:
            return (
                f"{condition} and <red>{temp_context},</red> {temp_desc}"
                if temp_desc
                else f"{condition} and <red>{temp_context}</red>"
            )
        elif temp_context in ["chilly", "very hot"]:
            return (
                f"{condition} and <b>{temp_context},</b> {temp_desc}"
                if temp_desc
                else f"{condition} and <b>{temp_context}</b>"
            )
        else:
            return f"{condition} and {temp_context}, {temp_desc}"
    else:
        return f"{condition}, {temp_desc}"


def _analyze_precipitation(weather_data, forecast_data, is_evening):
    """Analyze current and near-term precipitation"""
    if not forecast_data:
        return None

    # Check current conditions
    current_desc = weather_data.get("weather_desc", "").lower()
    currently_precipitating = any(
        word in current_desc for word in ["rain", "snow", "drizzle", "shower"]
    )

    # Look at next 24 hours for significant precipitation chances
    next_24h = forecast_data[:8]  # Assuming 3-hour intervals
    significant_precip = []

    for item in next_24h:
        pop = item.get("pop", 0)  # Probability of precipitation (0-1)
        has_rain = item.get("rain", {}).get("3h", 0) > 0
        has_snow = item.get("snow", {}).get("3h", 0) > 0

        if pop >= 0.25 or has_rain or has_snow:  # 25% chance or actual precipitation
            if has_snow or "snow" in item.get("weather", {}).get("description", ""):
                significant_precip.append(("snow", pop))
            elif has_rain or "rain" in item.get("weather", {}).get("description", ""):
                significant_precip.append(("rain", pop))

    # Generate precipitation message
    if currently_precipitating:
        if significant_precip:
            return "Continuing through the night" if is_evening else "Continuing today"
        else:
            return "Clearing soon"

    elif significant_precip:
        # Find most likely type
        precip_types = [p[0] for p in significant_precip]
        max_prob = max([p[1] for p in significant_precip])

        if precip_types.count("snow") > precip_types.count("rain"):
            precip_type = "snow"
        else:
            precip_type = "rain"

        if max_prob >= 0.7:
            return f"{precip_type.title()} likely"
        elif max_prob >= 0.5:
            return f"{precip_type.title()} possible"
        else:
            return f"Chance of {precip_type}"

    return None


def _analyze_temperature_trends(current_temp, feels_like, forecast_data, is_evening):
    """Analyze temperature trends and extremes"""
    if not forecast_data:
        return None

    # Get next 8-12 hours of temperatures
    temps = [item.get("temp", current_temp) for item in forecast_data[:4]]

    if not temps:
        return None

    min_temp = min(temps)
    max_temp = max(temps)

    # Focus on significant temperature changes
    temp_range = max_temp - min_temp

    if is_evening:
        # Evening: focus on overnight low
        if min_temp < current_temp - 3:
            return f"Low of <h>{min_temp:g}</h>° overnight"
    else:
        # Daytime: focus on high or significant changes
        if max_temp > current_temp + 3:
            return f"Rising to <h>{max_temp:g}</h>°"
        elif temp_range > 5:
            return f"Ranging <h>{min_temp:g}</h>° to <h>{max_temp:g}</h>°"

    return None


def _describe_tomorrow_outlook(
    forecast_data, current_weather_desc="", current_timestamp=None
):
    """Generate tomorrow's outlook by analyzing actual forecast data"""
    if not forecast_data:
        return None

    from date_utils import _timestamp_to_components

    # Use the current timestamp passed to the function (already in local time)
    if current_timestamp is None:
        return None

    # Calculate tomorrow's timestamp (add 24 hours)
    tomorrow_timestamp = current_timestamp + 86400

    # Get tomorrow's date in YYYY-MM-DD format using existing utilities
    year, month, day, hour, minute, second, weekday = _timestamp_to_components(
        tomorrow_timestamp
    )
    tomorrow_date = f"{year:04d}-{month:02d}-{day:02d}"

    # Find all forecast items that are for tomorrow
    tomorrow_items = []
    for item in forecast_data:
        item_timestamp = item.get("dt")
        if item_timestamp:
            # Get item's date in YYYY-MM-DD format using existing utilities
            item_year, item_month, item_day, _, _, _, _ = _timestamp_to_components(
                item_timestamp
            )
            item_date = f"{item_year:04d}-{item_month:02d}-{item_day:02d}"
            if item_date == tomorrow_date:
                tomorrow_items.append(item)

    if not tomorrow_items:
        log(f"No forecast items found for tomorrow ({tomorrow_date})")
        return None

    # Get all temperatures for tomorrow
    tomorrow_temps = [
        item.get("temp") for item in tomorrow_items if item.get("temp") is not None
    ]
    tomorrow_icons = [item.get("icon", "") for item in tomorrow_items]
    tomorrow_descriptions = [
        item.get("description", "").lower() for item in tomorrow_items
    ]

    if not tomorrow_temps:
        return None

    tomorrow_high = max(tomorrow_temps)
    tomorrow_low = min(tomorrow_temps)

    # Always show high/low temps for tomorrow since we have space
    temp_range = tomorrow_high - tomorrow_low
    if temp_range >= 15:
        # Very large temperature swing - highlight it
        temp_desc = (
            f"<red>high <h>{tomorrow_high:g}</h>° low <h>{tomorrow_low:g}</h>°</red>"
        )
    elif temp_range >= 10:
        # Moderate temperature swing
        temp_desc = (
            f"<b>high <h>{tomorrow_high:g}</h>° low <h>{tomorrow_low:g}</h>°</b>"
        )
    else:
        # Always show both high and low for tomorrow
        temp_desc = f"high <h>{tomorrow_high:g}</h>° low <h>{tomorrow_low:g}</h>°"

    # Analyze tomorrow's conditions from forecast data
    has_snow = any(
        "13" in icon or "snow" in desc
        for icon, desc in zip(tomorrow_icons, tomorrow_descriptions)
    )
    has_rain = any(
        "09" in icon or "10" in icon or "rain" in desc
        for icon, desc in zip(tomorrow_icons, tomorrow_descriptions)
    )
    has_storms = any(
        "11" in icon or "storm" in desc or "thunder" in desc
        for icon, desc in zip(tomorrow_icons, tomorrow_descriptions)
    )
    has_clouds = any(
        "02" in icon or "03" in icon or "04" in icon or "cloud" in desc
        for icon, desc in zip(tomorrow_icons, tomorrow_descriptions)
    )
    has_clear = any(
        "01" in icon or "clear" in desc
        for icon, desc in zip(tomorrow_icons, tomorrow_descriptions)
    )

    # Generate contextual description based on actual forecast
    # Use newline for tomorrow when there's space, but keep compact when needed
    tomorrow_prefix = "\n\n<b>Tomorrow:</b>"

    if has_storms:
        return f"{tomorrow_prefix} <red>thunderstorms expected,</red> {temp_desc}"
    elif has_snow:
        return f"{tomorrow_prefix} <red>snow likely,</red> {temp_desc}"
    elif has_rain:
        return f"{tomorrow_prefix} rain expected, {temp_desc}"
    elif has_clouds and has_clear:
        return f"{tomorrow_prefix} partly cloudy, {temp_desc}"
    elif has_clouds:
        return f"{tomorrow_prefix} mostly cloudy, {temp_desc}"
    elif has_clear:
        return f"{tomorrow_prefix} sunny skies, {temp_desc}"
    else:
        return f"{tomorrow_prefix} {temp_desc}"


def _explain_feels_like(actual_temp, feels_like, humidity, wind_speed, wind_gust):
    """Explain why the feels-like temperature differs from actual"""
    temp_diff = feels_like - actual_temp

    # Wind chill (feels colder)
    if temp_diff < -3 and wind_gust > 15:  # Strong gusts
        return "due to wind gusts"
    elif temp_diff < -3 and wind_speed > 10:  # Steady wind
        return "due to wind"

    # Heat index (feels hotter)
    elif (
        temp_diff > 3 and actual_temp > 20 and humidity > 70
    ):  # High humidity when warm
        return "due to humidity"
    elif temp_diff > 5 and actual_temp > 25 and humidity > 60:  # Very humid when hot
        return "due to high humidity"

    return None  # No clear explanation, just show feels-like without reason


def _get_temperature_context(temp):
    """Get contextual temperature description"""
    if temp <= -10:
        return "bitterly cold"
    elif temp <= 0:
        return "freezing"
    elif temp <= 5:
        return "cold"
    elif temp <= 10:
        return "chilly"
    elif temp >= 35:
        return "extremely hot"
    elif temp >= 30:
        return "very hot"
    elif temp >= 25:
        return "hot"
    elif temp >= 20:
        return "warm"
    else:
        return None


def _describe_current_precipitation(weather_desc, forecast_data):
    """Describe current precipitation and when it will clear"""
    current_desc_lower = weather_desc.lower()

    # Also check forecast data for current conditions (first item shows current weather icons)
    current_forecast = forecast_data[0] if forecast_data else None
    current_icon = current_forecast.get("icon", "") if current_forecast else ""

    # Check for snow in current conditions or forecast
    is_snowing = "snow" in current_desc_lower or "13" in current_icon
    is_raining = (
        "rain" in current_desc_lower
        or "drizzle" in current_desc_lower
        or "09" in current_icon
        or "10" in current_icon
    )
    is_stormy = (
        "storm" in current_desc_lower
        or "thunder" in current_desc_lower
        or "11" in current_icon
    )

    if is_snowing:
        # Check when snow will end
        clear_time = _find_when_precipitation_ends(forecast_data, ["snow"])
        if clear_time:
            return f"<red>Currently snowing,</red> <i>expected</i> to stop {clear_time}"
        else:
            return "<red>Currently snowing</red>"
    elif is_raining:
        # Check when rain will end
        clear_time = _find_when_precipitation_ends(forecast_data, ["rain", "drizzle"])
        if clear_time:
            return f"Currently raining, <i>expected</i> to end {clear_time}"
        else:
            return "Currently raining"
    elif is_stormy:
        clear_time = _find_when_precipitation_ends(
            forecast_data, ["storm", "thunder", "rain"]
        )
        if clear_time:
            return f"<red>Thunderstorms ongoing,</red> <i>clearing</i> {clear_time}"
        else:
            return "<red>Thunderstorms ongoing</red>"

    return None


def _analyze_upcoming_precipitation(forecast_data):
    """Check for precipitation in the next few hours"""
    if not forecast_data or len(forecast_data) < 3:
        return None

    # Check next 12 hours (first 4 forecast items)
    near_term = forecast_data[:4]

    for i, item in enumerate(near_term):
        pop = item.get("pop", 0)
        description = item.get("description", "").lower()
        timestamp = item.get("dt")

        if pop > 0.5 or any(
            precip in description for precip in ["rain", "snow", "storm"]
        ):
            time_desc = "later"
            if timestamp:
                try:
                    hour = get_hour_from_timestamp(timestamp)

                    # Generalize overnight hours (midnight to 8am)
                    if hour >= 0 and hour <= 8:
                        time_desc = "overnight"
                    elif hour == 12:
                        time_desc = "around noon"
                    elif hour < 12:
                        time_desc = f"around {hour}a"
                    else:
                        time_desc = f"around {hour - 12}p"
                except:
                    hours = (i + 1) * 3
                    time_desc = f"within {hours} hours"

            if "snow" in description:
                return f"<red>Snow</red> <i>likely</i> to start {time_desc}"
            elif "storm" in description or "thunder" in description:
                return f"<red>Thunderstorms</red> <i>approaching</i> {time_desc}"
            elif "rain" in description or pop > 0.5:
                return f"Rain <i>likely</i> to start {time_desc}"

    return None


def _find_when_precipitation_ends(forecast_data, precip_types):
    """Find when current precipitation is expected to end"""
    if not forecast_data:
        return None

    for i, item in enumerate(forecast_data):
        description = item.get("description", "").lower()
        pop = item.get("pop", 0)
        timestamp = item.get("dt")
        icon = item.get("icon", "")

        # Check both description and icon for precipitation indicators
        has_precip_desc = any(precip in description for precip in precip_types)
        has_precip_icon = (
            ("snow" in precip_types and "13" in icon)
            or ("rain" in precip_types and ("09" in icon or "10" in icon))
            or ("storm" in precip_types and "11" in icon)
        )

        # If no precipitation indicators, it's clearing
        if pop < 0.3 and not has_precip_desc and not has_precip_icon:
            if timestamp:
                try:
                    hour = get_hour_from_timestamp(timestamp)
                    if hour == 0:
                        return "around midnight"
                    elif hour < 12:
                        return f"around {hour}a"
                    elif hour == 12:
                        return "around noon"
                    else:
                        return f"around {hour - 12}p"
                except:
                    pass

            hours = (i + 1) * 3
            if hours <= 3:
                return "within 3 hours"
            elif hours <= 6:
                return "by evening"
            else:
                return "by tomorrow"

    return None


def _describe_moon_phase(current_timestamp):
    """Describe notable moon phases"""
    try:
        moon_info = moon_phase.get_moon_info(current_timestamp)

        if moon_info is None:
            return None

        phase_name = moon_info.get("name", "").lower()

        if "full" in phase_name:
            return "<i>Full moon tonight</i>"
        elif "new" in phase_name:
            return "<i>New moon tonight</i>"
        # Only mention other phases if they're particularly notable
        # Most phases aren't worth the text space

    except (ImportError, Exception):
        pass

    return None


# Removed time string parsing - now using sunset timestamp directly


def _truncate_for_display(text, max_length=400):
    """Truncate text to fit display constraints while preserving meaning"""
    if len(text) <= max_length:
        return text

    # Try to truncate at sentence boundaries
    sentences = text.split(". ")
    truncated = sentences[0]

    for sentence in sentences[1:]:
        test_length = len(truncated + ". " + sentence)
        if test_length <= max_length:
            truncated += ". " + sentence
        else:
            break

    # If still too long, truncate the last sentence
    if len(truncated) > max_length:
        truncated = truncated[: max_length - 3] + "..."

    return truncated
