"""
weather narrative generator - creates contextual weather description text string
"""

from utils import moon_phase
from utils.logger import log

from weather.date_utils import (
    get_day_from_timestamp,
    get_hour_from_timestamp,
    get_month_from_timestamp,
)
from weather.narrative.calendar_events import (
    get_calendar_events,
    get_seasonal_suggestions,
    get_weather_suggestions,
)
from weather.narrative.content_prioritizer import ContentPrioritizer
from weather.weather_history import compare_with_yesterday


def format_temp(temp):
    """Format temperature to avoid negative zero"""
    if temp is None:
        return "?"
    # Round to nearest integer
    rounded = round(temp)
    # If it rounds to zero, explicitly return "0"
    if rounded == 0:
        return "0"
    return f"{rounded:.0f}"


def get_weather_narrative(
    weather_data, forecast_data, current_timestamp=None, max_length=400
):
    """Generate enhanced weather narrative with priority system and improvements

    Args:
        weather_data: Current weather data dict with temp, feels_like, weather, etc.
        forecast_data: List of forecast items for next ~24 hours
        current_timestamp: Unix timestamp for current time (in local time)
        max_length: Maximum length for the narrative

    Returns:
        str: Enhanced contextual weather description
    """
    if not weather_data:
        return "Weather data unavailable."

    if not current_timestamp:
        return "Weather narrative unavailable - no timestamp provided"

    # Initialize content prioritizer
    prioritizer = ContentPrioritizer(max_length=max_length)

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
    air_quality = weather_data.get("air_quality")
    uv_index = weather_data.get("uv_index", 0)

    from utils.logger import log

    current_hour = get_hour_from_timestamp(current_timestamp)
    current_day = get_day_from_timestamp(current_timestamp)
    current_month = get_month_from_timestamp(current_timestamp)

    # Determine if it's daytime (before 9pm)
    is_daytime = current_hour < 21

    # 1. Current conditions (HIGHEST PRIORITY - always include)
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
    prioritizer.add_item(current_conditions, priority=10, category="current")

    # 2. Yesterday comparison (HIGH PRIORITY if significant)
    yesterday_comparison = compare_with_yesterday(
        current_temp, high_temp, low_temp, current_timestamp
    )
    if yesterday_comparison:
        priority = 9 if "much" in yesterday_comparison.lower() else 7
        prioritizer.add_item(
            yesterday_comparison, priority=priority, category="comparison"
        )

    # 3. Current precipitation status (HIGH PRIORITY)
    current_precip = _describe_current_precipitation(
        weather_desc, forecast_data, use_short_format=False
    )
    current_precip_short = _describe_current_precipitation(
        weather_desc, forecast_data, use_short_format=True
    )
    if current_precip:
        prioritizer.add_item(
            current_precip,
            priority=9,
            short_text=current_precip_short,
            category="current_weather",
        )

    # 4. Upcoming precipitation (MEDIUM-HIGH PRIORITY)
    current_has_precip = (
        any(
            precip in weather_desc.lower()
            for precip in ["rain", "snow", "storm", "drizzle", "shower"]
        )
        if weather_desc
        else False
    )

    # Only add upcoming precipitation if current precipitation didn't already handle timing
    precip_end_time = None
    if current_has_precip:
        precip_end_time = _find_when_precipitation_ends(
            forecast_data, ["rain", "snow", "storm"]
        )

    # Skip upcoming precip if current precip already mentioned timing
    if not current_precip or (
        "expected" not in current_precip.lower()
        and "return" not in current_precip.lower()
    ):
        upcoming_precip = _analyze_upcoming_precipitation(
            forecast_data, current_has_precip, precip_end_time
        )
        if upcoming_precip:
            prioritizer.add_item(
                upcoming_precip, priority=8, category="upcoming_weather"
            )

    # 5. Tomorrow's forecast (MEDIUM PRIORITY)
    tomorrow_info = _describe_tomorrow_outlook(
        forecast_data, weather_desc, current_timestamp
    )
    if tomorrow_info:
        prioritizer.add_item(tomorrow_info, priority=6, category="tomorrow")

    # 6. Calendar events (VARIABLE PRIORITY based on event)
    calendar_events = get_calendar_events(current_timestamp, priority_threshold=5)
    for event in calendar_events:
        prioritizer.add_item(
            event["text"],
            priority=event["priority"],
            short_text=event["short_text"],
            category="calendar",
        )

    # 7. Weather suggestions (MEDIUM PRIORITY)
    rain_chance = _estimate_rain_chance(forecast_data)
    suggestions = get_weather_suggestions(
        current_temp,
        weather_desc,
        is_daytime,
        rain_chance,
        wind_speed,
        air_quality,
        uv_index,
    )
    for suggestion in suggestions:
        # Give air quality suggestions their own category to avoid competition
        if "air quality" in suggestion.get("text", "").lower():
            suggestion["category"] = "air_quality"
        else:
            suggestion["category"] = "weather_suggestion"
    prioritizer.add_items(suggestions)

    # 8. Seasonal suggestions (MEDIUM PRIORITY)
    seasonal_suggestions = get_seasonal_suggestions(
        current_month, current_day, current_temp, weather_desc
    )
    for suggestion in seasonal_suggestions:
        suggestion["category"] = "seasonal"
    prioritizer.add_items(seasonal_suggestions)

    # 9. Moon phase (LOW-MEDIUM PRIORITY)
    moon_info = _describe_moon_phase(current_timestamp)
    if moon_info:
        # Shorter version for space constraints
        moon_short = moon_info.replace("tonight.", "!").replace("tonight", "!")
        prioritizer.add_item(
            moon_info, priority=4, short_text=moon_short, category="astronomy"
        )

    # Generate optimized narrative
    return prioritizer.optimize_narrative()


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
            temp_desc = f"<h>{format_temp(current_temp)}</h>° (<i>feels like</i> <h>{format_temp(feels_like)}</h>° {feels_like_reason})"
        else:
            temp_desc = f"<h>{format_temp(current_temp)}</h>° (<i>feels like</i> <h>{format_temp(feels_like)}</h>°)"
    else:
        temp_desc = f"<h>{format_temp(current_temp)}</h>°"

    # Add high/low more often - if there's a meaningful range or short text
    temp_range = high_temp - low_temp
    if temp_range >= 15:
        # Very large daily temperature swing - highlight in red
        temp_desc += f", l:<red><h>{format_temp(low_temp)}</h>° h:<h>{format_temp(high_temp)}</h>°</red>"
    elif temp_range >= 10:
        # Moderate swing - make it bold
        temp_desc += f", l:<b><h>{format_temp(low_temp)}</h>° h:<h>{format_temp(high_temp)}</h>°</b>"
    # elif temp_range >= 3:  # Lower threshold to show range more often
    #     temp_desc += f", ranging <h>{format_temp(low_temp)}</h>° to <h>{format_temp(high_temp)}</h>°"

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
            return f"Low of <h>{format_temp(min_temp)}</h>° overnight"
    else:
        # Daytime: focus on high or significant changes
        if max_temp > current_temp + 3:
            return f"Rising to <h>{format_temp(max_temp)}</h>°"
        elif temp_range > 5:
            return f"Ranging <h>{format_temp(min_temp)}</h>° to <h>{format_temp(max_temp)}</h>°"

    return None


def _describe_tomorrow_outlook(
    forecast_data, current_weather_desc="", current_timestamp=None
):
    """Generate upcoming weather outlook by analyzing next 24 hours of forecast data"""
    if not forecast_data:
        return None

    if current_timestamp is None:
        log("No current timestamp for upcoming forecast")
        return None

    # Look at next 24 hours from current time instead of strict "tomorrow" date
    end_timestamp = current_timestamp + (24 * 3600)  # Next 24 hours

    # Find all forecast items in the next 24 hours
    upcoming_items = []
    for item in forecast_data:
        item_timestamp = item.get("dt")
        if item_timestamp and current_timestamp < item_timestamp <= end_timestamp:
            description = item.get("description", "")

            upcoming_items.append(item)

    if not upcoming_items:
        log(f"No forecast items found for next 24 hours")
        return None

    # Get all temperatures for upcoming period
    upcoming_temps = [
        item.get("temp") for item in upcoming_items if item.get("temp") is not None
    ]
    upcoming_icons = [item.get("icon", "") for item in upcoming_items]
    upcoming_descriptions = [
        item.get("description", "").lower() for item in upcoming_items
    ]

    if not upcoming_temps:
        return None

    upcoming_high = max(upcoming_temps)
    upcoming_low = min(upcoming_temps)

    # Always show high/low temps for upcoming period since we have space
    temp_range = upcoming_high - upcoming_low
    if temp_range >= 15:
        # Very large temperature swing - highlight it
        temp_desc = f"<red>h:<h>{format_temp(upcoming_high)}</h>° l:<h>{format_temp(upcoming_low)}</h>°</red>"
    elif temp_range >= 10:
        # Moderate temperature swing
        temp_desc = f"<b>h:<h>{format_temp(upcoming_high)}</h>° l:<h>{format_temp(upcoming_low)}</h>°</b>"
    else:
        # Always show both high and low for upcoming period
        temp_desc = f"h:<h>{format_temp(upcoming_high)}</h>° l:<h>{format_temp(upcoming_low)}</h>°"

    # Analyze upcoming conditions from forecast data with time ranges
    rain_periods = _analyze_weather_periods(
        upcoming_items, ["rain", "drizzle"], ["09", "10"]
    )
    snow_periods = _analyze_weather_periods(upcoming_items, ["snow"], ["13"])
    storm_periods = _analyze_weather_periods(
        upcoming_items, ["storm", "thunder"], ["11"]
    )
    clear_periods = _analyze_weather_periods(upcoming_items, ["clear"], ["01"])
    cloud_periods = _analyze_weather_periods(
        upcoming_items, ["cloud"], ["02", "03", "04"]
    )

    # Analyze wind conditions
    wind_periods = _analyze_wind_periods(upcoming_items)

    has_rain = len(rain_periods) > 0
    has_snow = len(snow_periods) > 0
    has_storms = len(storm_periods) > 0
    has_clouds = len(cloud_periods) > 0
    has_clear = len(clear_periods) > 0
    has_wind = len(wind_periods) > 0

    # Generate contextual description based on actual forecast
    # Use newline for upcoming when there's space, but keep compact when needed
    upcoming_prefix = "<b>Tomorrow:</b>"

    # Build comprehensive description
    weather_parts = []

    if has_storms:
        storm_desc = _get_precipitation_description("thunderstorms", storm_periods)
        weather_parts.append(f"<red>{storm_desc}</red>")
    elif has_snow:
        snow_desc = _get_precipitation_description("snow", snow_periods)
        weather_parts.append(f"<red>{snow_desc}</red>")
    elif has_rain:
        rain_desc = _get_precipitation_description("rain", rain_periods)
        weather_parts.append(rain_desc)

    # Add clear periods if there's precipitation and clearing
    if (has_rain or has_snow) and has_clear:
        clear_desc = _get_clear_period_description(clear_periods)
        if clear_desc:
            weather_parts.append(clear_desc)
    elif has_clouds and has_clear:
        weather_parts.append("partly cloudy")
    elif has_clouds:
        weather_parts.append("mostly cloudy")
    elif has_clear:
        weather_parts.append("sunny skies")

    # Add wind if significant
    if has_wind:
        wind_desc = _get_wind_description(wind_periods)
        if wind_desc:
            weather_parts.append(wind_desc)

    # Combine all weather descriptions
    if weather_parts:
        weather_desc = ", ".join(weather_parts)
        return f"{upcoming_prefix} {weather_desc}, {temp_desc}"
    else:
        return f"{upcoming_prefix} {temp_desc}"


def _analyze_weather_periods(items, keywords, icon_codes):
    """Analyze forecast items to find periods of specific weather conditions"""
    periods = []
    current_period = None

    for item in items:
        timestamp = item.get("dt")
        description = item.get("description", "").lower()
        icon = item.get("icon", "")
        pop = item.get("pop", 0)

        # Check if this item matches the weather condition
        has_condition = any(keyword in description for keyword in keywords) or any(
            code in icon for code in icon_codes
        )

        if has_condition:
            if current_period is None:
                # Start new period
                current_period = {
                    "start": timestamp,
                    "end": timestamp,
                    "pop_values": [pop],
                    "descriptions": [description],
                }
            else:
                # Extend current period
                current_period["end"] = timestamp
                current_period["pop_values"].append(pop)
                current_period["descriptions"].append(description)
        else:
            if current_period is not None:
                # End current period
                periods.append(current_period)
                current_period = None

    # Don't forget the last period
    if current_period is not None:
        periods.append(current_period)

    return periods


def _get_precipitation_description(precip_type, periods):
    """Generate description for precipitation periods with timing and likelihood"""
    if not periods:
        return f"{precip_type} expected"

    # Calculate average POP across all periods
    all_pops = []
    for period in periods:
        all_pops.extend(period["pop_values"])

    avg_pop = sum(all_pops) / len(all_pops) if all_pops else 0

    # Choose likelihood word based on average POP
    if avg_pop >= 0.7:
        likelihood = "expected"
    elif avg_pop >= 0.4:
        likelihood = "likely"
    else:
        likelihood = "possible"

    # Handle multiple periods
    if len(periods) > 2:
        return f"{precip_type} {likelihood} off and on"
    elif len(periods) == 2:
        start1 = _format_time_for_narrative(periods[0]["start"])
        start2 = _format_time_for_narrative(periods[1]["start"])
        return f"{precip_type} {likelihood} {start1} and {start2}"
    else:
        # Single period
        start_time = _format_time_for_narrative(periods[0]["start"])
        return f"{precip_type} {likelihood} starting {start_time}"


def _get_clear_period_description(clear_periods):
    """Generate description for clear periods when there's mostly rain/clouds"""
    if not clear_periods:
        return ""

    if len(clear_periods) == 1:
        start_time = _format_time_for_narrative(clear_periods[0]["start"])
        return f"clearing {start_time}"
    else:
        return "with some clear breaks"


def _analyze_wind_periods(items):
    """Analyze forecast items to find periods of significant wind"""
    periods = []
    current_period = None

    for item in items:
        timestamp = item.get("dt")
        wind_speed = item.get("wind_speed", 0)
        wind_gust = item.get("wind_gust", 0)

        # Consider it windy if sustained winds > 15 mph or gusts > 25 mph
        is_windy = wind_speed > 15 or wind_gust > 25

        if is_windy:
            if current_period is None:
                current_period = {
                    "start": timestamp,
                    "end": timestamp,
                    "wind_speeds": [wind_speed],
                    "wind_gusts": [wind_gust],
                }
            else:
                current_period["end"] = timestamp
                current_period["wind_speeds"].append(wind_speed)
                current_period["wind_gusts"].append(wind_gust)
        else:
            if current_period is not None:
                periods.append(current_period)
                current_period = None

    if current_period is not None:
        periods.append(current_period)

    return periods


def _get_wind_description(wind_periods):
    """Generate description for windy periods"""
    if not wind_periods:
        return ""

    if len(wind_periods) == 1:
        start_time = _format_time_for_narrative(wind_periods[0]["start"])
        max_gust = (
            max(wind_periods[0]["wind_gusts"]) if wind_periods[0]["wind_gusts"] else 0
        )
        if max_gust > 35:
            return f"gusty winds {start_time}"
        else:
            return f"windy {start_time}"
    else:
        return "windy periods"


def _format_time_for_narrative(timestamp):
    """Format timestamp for narrative use (e.g., 'morning', 'afternoon', 'evening')"""
    if not timestamp:
        return ""

    hour = get_hour_from_timestamp(timestamp)

    if 6 <= hour <= 11:
        return "morning"
    elif 12 <= hour <= 17:
        return "afternoon"
    elif 18 <= hour <= 22:
        return "evening"
    else:
        return "overnight"


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


def _describe_current_precipitation(
    weather_desc, forecast_data, use_short_format=False
):
    """Describe current precipitation and when it will clear/return - with merged timing"""
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
        # Check when snow will end and when it returns
        clear_time = _find_when_precipitation_ends(forecast_data, ["snow"])
        if clear_time:
            # Find when snow returns after it clears
            end_timestamp = None
            for item in forecast_data:
                if (
                    item.get("weather_desc", "").lower().find("clear") != -1
                    or item.get("weather_desc", "").lower().find("overcast") != -1
                ):
                    if not any(
                        precip in item.get("weather_desc", "").lower()
                        for precip in ["snow", "rain", "storm"]
                    ):
                        end_timestamp = item.get("timestamp", 0)
                        break

            return_time = (
                _find_when_precipitation_returns(forecast_data, ["snow"], end_timestamp)
                if end_timestamp
                else None
            )

            if return_time:
                if use_short_format:
                    return f"<i>Exp</i> to stop ~{clear_time} and return ~{return_time}"
                else:
                    return f"<i>Expected</i> to stop around {clear_time} and return around {return_time}"
            else:
                if use_short_format:
                    return f"<i>Exp</i> to stop ~{clear_time}"
                else:
                    return f"<i>Expected</i> to stop around {clear_time}"
        else:
            return None  # Don't say "currently snowing" - it's redundant with weather condition
    elif is_raining:
        # Check when rain will end and return
        clear_time = _find_when_precipitation_ends(forecast_data, ["rain", "drizzle"])
        if clear_time:
            end_timestamp = None
            for item in forecast_data:
                if item.get("weather_desc", "").lower().find("clear") != -1:
                    if not any(
                        precip in item.get("weather_desc", "").lower()
                        for precip in ["rain", "snow", "storm"]
                    ):
                        end_timestamp = item.get("timestamp", 0)
                        break

            return_time = (
                _find_when_precipitation_returns(forecast_data, ["rain"], end_timestamp)
                if end_timestamp
                else None
            )

            if return_time:
                if use_short_format:
                    return f"<i>Exp</i> to end ~{clear_time} and return ~{return_time}"
                else:
                    return f"<i>Expected</i> to end around {clear_time} and return around {return_time}"
            else:
                if use_short_format:
                    return f"<i>Exp</i> to end ~{clear_time}"
                else:
                    return f"<i>Expected</i> to end around {clear_time}"
        else:
            return None
    elif is_stormy:
        clear_time = _find_when_precipitation_ends(
            forecast_data, ["storm", "thunder", "rain"]
        )
        if clear_time:
            if use_short_format:
                return f"<red>T-storms</red> <i>clearing</i> ~{clear_time}"
            else:
                return f"<red>T-storms</red> <i>clearing</i> around {clear_time}"
        else:
            return None

    return None


def _analyze_upcoming_precipitation(
    forecast_data, current_has_precip=False, avoid_end_time=None
):
    """Check for precipitation in the next few hours, accounting for current conditions"""
    if not forecast_data or len(forecast_data) < 3:
        return None

    # Check next 12-18 hours (more forecast items)
    near_term = forecast_data[:6]

    # If currently raining, look for significant gaps (at least 6+ hours) followed by new precipitation
    if current_has_precip:
        clear_period_start = None
        clear_period_hours = 0

        for i, item in enumerate(near_term):
            pop = item.get("pop", 0)
            description = item.get("description", "").lower()
            timestamp = item.get("dt")

            # Check if this period has precipitation
            has_precip = pop > 0.3 or any(
                precip in description for precip in ["rain", "snow", "storm"]
            )

            if not has_precip:
                # Clear period continues or starts
                if clear_period_start is None:
                    clear_period_start = i
                clear_period_hours = (i - clear_period_start + 1) * 3
            elif has_precip and clear_period_hours >= 3:
                # Found precipitation after a meaningful clear period (3+ hours)

                # Skip if this is too close to the reported end time
                if avoid_end_time and timestamp:
                    try:
                        end_hour = None
                        if "around " in avoid_end_time:
                            time_part = avoid_end_time.split("around ")[1]
                            if time_part.endswith("a"):
                                end_hour = int(time_part[:-1])
                                if end_hour == 12:
                                    end_hour = 0
                            elif time_part.endswith("p"):
                                end_hour = int(time_part[:-1])
                                if end_hour != 12:
                                    end_hour += 12

                        current_hour = get_hour_from_timestamp(timestamp)
                        if end_hour and abs(current_hour - end_hour) <= 1:
                            # Too close to end time (within 1 hour), skip to avoid contradiction
                            continue
                    except:
                        pass

                time_desc = "later"
                if timestamp:
                    try:
                        hour = get_hour_from_timestamp(timestamp)
                        if hour >= 0 and hour <= 8:
                            time_desc = "overnight"
                        elif hour == 12:
                            time_desc = "around noon"
                        elif hour < 12:
                            time_desc = f"around <h>{hour}</h>a"
                        else:
                            time_desc = f"around <h>{hour - 12}</h>p"
                    except:
                        hours = (i + 1) * 3
                        time_desc = f"within {hours} hours"

                if "snow" in description:
                    return f"<red>Snow</red> <i>likely</i> to return {time_desc}"
                elif "storm" in description or "thunder" in description:
                    return f"<red>Thunderstorms</red> <i>approaching</i> {time_desc}"
                elif "rain" in description or pop > 0.5:
                    return f"Rain <i>likely</i> to return {time_desc}"
            elif has_precip:
                # Reset clear period tracking
                clear_period_start = None
                clear_period_hours = 0

        return None
    else:
        # Not currently precipitating, look for any upcoming precipitation
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
                            time_desc = f"around <h>{hour}</h>a"
                        else:
                            time_desc = f"around <h>{hour - 12}</h>p"
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
                        return f"around <h>{hour}</h>a"
                    elif hour == 12:
                        return "around noon"
                    else:
                        return f"around <h>{hour - 12}</h>p"
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


def _estimate_rain_chance(forecast_data):
    """Estimate rain chance from forecast data"""
    if not forecast_data:
        return 0

    rain_count = 0
    total_items = min(8, len(forecast_data))  # Next 8 hours

    for item in forecast_data[:total_items]:
        weather_desc = item.get("weather_desc", "").lower()
        if "rain" in weather_desc or "storm" in weather_desc:
            rain_count += 1

    return int((rain_count / total_items) * 100) if total_items > 0 else 0


def _find_when_precipitation_returns(forecast_data, precip_types, after_timestamp):
    """Find when precipitation returns after it ends"""
    if not forecast_data or not after_timestamp:
        return None

    for item in forecast_data:
        timestamp = item.get("timestamp", 0)
        weather_desc = item.get("weather_desc", "").lower()

        # Look for precipitation after the end time
        if timestamp > after_timestamp:
            if any(precip in weather_desc for precip in precip_types):
                return _format_time_for_narrative(timestamp)

    return None


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
