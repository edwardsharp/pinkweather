"""
weather api module for pinkweather - provider-agnostic interface
works on both circuitpython hardware and standard python web server
"""

import config
from utils import moon_phase
from utils.astro_utils import get_zodiac_sign_from_timestamp
from utils.logger import log

from weather import open_meteo, openweathermap, weatherbit
from weather.date_utils import (
    format_timestamp_to_date,
    format_timestamp_to_time,
    get_hour_from_timestamp,
)
from weather.weather_models import WeatherData

# Optional imports that may fail on different platforms
try:
    import wifi
except ImportError:
    wifi = None


def parse_current_weather_from_forecast(weather_data):
    """Parse current weather from provider data format"""
    if not weather_data or "current" not in weather_data:
        return None

    current = weather_data["current"]
    # Add formatted sunrise/sunset times
    if current.get("sunrise_timestamp") and current.get("sunset_timestamp"):
        current["sunrise_time"] = format_timestamp_to_time(
            current["sunrise_timestamp"], format_12h=True
        )
        current["sunset_time"] = format_timestamp_to_time(
            current["sunset_timestamp"], format_12h=True
        )
    return current


def parse_forecast_data(weather_data):
    """Parse forecast data from provider data format"""
    if not weather_data or "forecast" not in weather_data:
        return []
    return weather_data["forecast"]


def interpolate_temperature(target_timestamp, forecast_items):
    """Calculate interpolated temperature for a target timestamp based on surrounding forecast data"""
    if not forecast_items or len(forecast_items) < 2:
        return None

    # Find the two forecast items that bracket the target timestamp
    before_item = None
    after_item = None

    for item in forecast_items:
        if item["dt"] <= target_timestamp:
            before_item = item
        elif item["dt"] > target_timestamp and after_item is None:
            after_item = item
            break

    # If we can't bracket the time, use the closest available
    if before_item is None and after_item is not None:
        return after_item["temp"]
    elif after_item is None and before_item is not None:
        return before_item["temp"]
    elif before_item is None and after_item is None:
        return forecast_items[0]["temp"]  # Fallback to first item

    # Linear interpolation between before and after temperatures
    time_diff = after_item["dt"] - before_item["dt"]
    if time_diff == 0:
        return before_item["temp"]

    temp_diff = after_item["temp"] - before_item["temp"]
    target_offset = target_timestamp - before_item["dt"]
    interpolated_temp = before_item["temp"] + (temp_diff * target_offset / time_diff)

    return round(interpolated_temp)


def create_enhanced_forecast_data(weather_data):
    """Create enhanced forecast with current weather as 'NOW' plus consolidated cells and night periods"""
    enhanced_items = []

    # Parse current weather
    current_weather = parse_current_weather_from_forecast(weather_data)
    if not current_weather:
        return []

    current_timestamp = current_weather["current_timestamp"]  # Already in local time

    # Get forecast items for temperature interpolation
    forecast_items = parse_forecast_data(weather_data)

    # Create "NOW" cell - get pop and aqi from first forecast item
    current_pop = 0
    current_aqi = None

    if forecast_items:
        first_item = forecast_items[0]
        current_pop = first_item.get("pop", 0)
        current_aqi = first_item.get("aqi")

    now_item = {
        "dt": current_timestamp,  # Use actual current timestamp (already local)
        "temp": current_weather["current_temp"],
        "feels_like": current_weather["feels_like"],
        "icon": current_weather["weather_icon"],
        "description": "Current conditions",
        "pop": current_pop,
        "aqi": current_aqi,
        "is_now": True,
    }
    enhanced_items.append(now_item)

    # Get sunrise/sunset times for NIGHT cell logic
    sunrise_ts = None
    sunset_ts = None
    if "city" in weather_data and weather_data["city"]:
        city_data = weather_data["city"]
        if "sunrise" in city_data and "sunset" in city_data:
            sunrise_ts = city_data["sunrise"]
            sunset_ts = city_data["sunset"]
            # Calculate tomorrow's sunrise (add 24 hours)
            tomorrow_sunrise_ts = sunrise_ts + 86400

    # Filter future forecast items
    future_items = []
    if forecast_items:
        for item in forecast_items:
            if item["dt"] > current_timestamp:
                future_items.append(item)

    # Apply consolidation and NIGHT logic
    consolidated_items = consolidate_forecast_items(
        future_items, sunrise_ts, tomorrow_sunrise_ts, current_timestamp
    )

    # Add consolidated items to enhanced items
    enhanced_items.extend(consolidated_items)

    # Add sunrise/sunset special events with proximity merging
    enhanced_items = add_sunrise_sunset_events(
        enhanced_items, weather_data, current_weather, forecast_items, current_timestamp
    )

    # Sort items: NOW first, then chronological order by timestamp
    def sort_key(item):
        if item.get("is_now", False):
            return (0, 0)  # NOW always first
        else:
            return (1, item["dt"])  # Everything else by timestamp

    enhanced_items.sort(key=sort_key)

    # Return up to 20 items for display (8 cells max)
    return enhanced_items[:20]


def consolidate_forecast_items(
    items, sunrise_ts, tomorrow_sunrise_ts, current_timestamp
):
    """Consolidate similar adjacent cells and create NIGHT periods"""
    if not items:
        return []

    consolidated = []
    i = 0

    while i < len(items):
        current_item = items[i]
        current_hour = get_hour_from_timestamp(current_item["dt"])

        # Check if this should start a NIGHT period (00:00-01:59 to sunrise)
        # Only start NIGHT if we have multiple nighttime items to consolidate
        if current_hour == 0 or current_hour == 1:  # 00:00 or 01:00
            log(
                f"DEBUG NIGHT: Found potential night start at hour {current_hour} (ts: {current_item['dt']})"
            )
            night_items, next_i = collect_night_items(
                items, i, sunrise_ts, tomorrow_sunrise_ts
            )
            log(f"DEBUG NIGHT: Collected {len(night_items)} night items")
            if len(night_items) > 1:  # Only create NIGHT if multiple items
                night_cell = create_night_cell(night_items)
                log(f"DEBUG NIGHT: Created NIGHT cell with {len(night_items)} items")
                consolidated.append(night_cell)
                i = next_i
                continue
            else:
                log(
                    f"DEBUG NIGHT: Not enough items for NIGHT cell, proceeding normally"
                )

        # Try to consolidate similar adjacent items (max 6 hours)
        similar_items, next_i = collect_similar_items(items, i, max_hours=6)
        if len(similar_items) > 1:
            consolidated_cell = create_consolidated_cell(similar_items)
            consolidated.append(consolidated_cell)
            i = next_i
        else:
            # No consolidation, add individual item
            consolidated.append(current_item)
            i += 1

    return consolidated


def collect_night_items(items, start_idx, sunrise_ts, tomorrow_sunrise_ts):
    """Collect items from 00:00 until 1 hour after sunrise for NIGHT cell"""
    night_items = []
    i = start_idx

    # Determine which sunrise to use based on current item timestamp
    target_sunrise = (
        sunrise_ts if items[start_idx]["dt"] < sunrise_ts else tomorrow_sunrise_ts
    )

    # Calculate end time: 1 hour after sunrise
    night_end_time = target_sunrise + 3600 if target_sunrise else None

    while i < len(items):
        item = items[i]
        item_hour = get_hour_from_timestamp(item["dt"])

        # Stop collection if we reach 1 hour after sunrise
        if night_end_time and item["dt"] > night_end_time:
            break

        # Include all items from midnight (00:00) until 1 hour after sunrise
        if item_hour == 0 or item_hour >= 1:
            night_items.append(item)
            i += 1
        else:
            break

    return night_items, i


def collect_similar_items(items, start_idx, max_hours=6):
    """Collect adjacent items with similar conditions (icon, temp±2°, pop±10%)"""
    similar_items = [items[start_idx]]
    base_item = items[start_idx]
    i = start_idx + 1
    max_span_seconds = max_hours * 3600

    while i < len(items):
        item = items[i]

        # Check if span would exceed max hours
        time_span = item["dt"] - base_item["dt"]
        if time_span > max_span_seconds:
            break

        # Check similarity criteria
        if are_items_similar(base_item, item):
            similar_items.append(item)
            i += 1
        else:
            break

    return similar_items, i


def are_items_similar(item1, item2):
    """Check if two forecast items are similar enough to consolidate"""
    # Must have same icon
    if item1.get("icon") != item2.get("icon"):
        return False

    # Temperature criteria
    temp1 = item1.get("temp", 0)
    temp2 = item2.get("temp", 0)
    temp_diff = abs(temp1 - temp2)

    # POP criteria depend on temperature match
    pop1 = item1.get("pop", 0)
    pop2 = item2.get("pop", 0)
    pop_diff = abs(pop1 - pop2)

    if temp1 == temp2:
        # Same icon + same rounded temp → any POP difference allowed
        return True
    elif temp_diff <= 2:
        # Same icon + temp within ±2° → POP can differ by ±50%
        return pop_diff <= 0.5
    else:
        # Same icon but temp differs by more than 2° → no consolidation
        return False


def create_night_cell(night_items):
    """Create a consolidated NIGHT cell from multiple nighttime items"""
    # Calculate averages
    temps = [item.get("temp", 0) for item in night_items]
    pops = [item.get("pop", 0) for item in night_items]
    icons = [item.get("icon", "") for item in night_items]

    avg_temp = round(sum(temps) / len(temps))
    avg_pop = sum(pops) / len(pops)

    # Find most frequent icon
    most_frequent_icon = get_most_frequent_icon(icons)

    # Use middle timestamp for sorting
    middle_idx = len(night_items) // 2
    middle_timestamp = night_items[middle_idx]["dt"]

    return {
        "dt": middle_timestamp,
        "temp": avg_temp,
        "feels_like": avg_temp,  # Approximate
        "icon": most_frequent_icon,
        "description": "Night",
        "pop": avg_pop,
        "is_now": False,
        "is_special": True,
        "special_type": "night",
        "consolidated_count": len(night_items),
    }


def create_consolidated_cell(items):
    """Create a consolidated cell from similar adjacent items"""
    # Calculate averages
    temps = [item.get("temp", 0) for item in items]
    pops = [item.get("pop", 0) for item in items]
    feels_likes = [item.get("feels_like", 0) for item in items]

    avg_temp = round(sum(temps) / len(temps))
    avg_pop = sum(pops) / len(pops)
    avg_feels_like = round(sum(feels_likes) / len(feels_likes))

    # Use middle timestamp for sorting
    middle_idx = len(items) // 2
    middle_timestamp = items[middle_idx]["dt"]

    # Use the base item's icon and description
    base_item = items[0]

    return {
        "dt": middle_timestamp,
        "temp": avg_temp,
        "feels_like": avg_feels_like,
        "icon": base_item.get("icon"),
        "description": base_item.get("description", ""),
        "pop": avg_pop,
        "is_now": False,
        "is_special": False,
        "consolidated_count": len(items),
    }


def get_most_frequent_icon(icons):
    """Get the most frequently occurring icon from a list"""
    if not icons:
        return ""

    # Count occurrences
    icon_counts = {}
    for icon in icons:
        icon_counts[icon] = icon_counts.get(icon, 0) + 1

    # Return most frequent
    return max(icon_counts, key=icon_counts.get)


def add_sunrise_sunset_events(
    enhanced_items, weather_data, current_weather, forecast_items, current_timestamp
):
    """Add sunrise/sunset events, merging with nearby forecast items if within 15 minutes"""
    if "city" not in weather_data or not weather_data["city"]:
        return enhanced_items

    city_data = weather_data["city"]
    if "sunrise" not in city_data or "sunset" not in city_data:
        return enhanced_items

    sunrise_ts = city_data["sunrise"]
    sunset_ts = city_data["sunset"]
    tomorrow_sunrise_ts = sunrise_ts + 86400
    tomorrow_sunset_ts = sunset_ts + 86400

    future_window = 24 * 3600  # 24 hours from now

    # Check each sunrise/sunset event
    events_to_check = [
        (sunrise_ts, "sunrise", "Sunrise"),
        (sunset_ts, "sunset", "Sunset"),
        (tomorrow_sunrise_ts, "sunrise", "Tomorrow Sunrise"),
        (tomorrow_sunset_ts, "sunset", "Tomorrow Sunset"),
    ]

    for event_time, event_type, event_desc in events_to_check:
        if current_timestamp <= event_time <= current_timestamp + future_window:
            # Check if there's a nearby forecast item (within 15 minutes)
            nearby_item = find_nearby_forecast_item(enhanced_items, event_time, 15 * 60)

            if nearby_item:
                # Merge event into nearby item
                nearby_item["icon"] = event_type
                nearby_item["description"] = event_desc
                nearby_item["is_special"] = True
                nearby_item["special_type"] = event_type
            else:
                # Create separate event item
                event_temp = interpolate_temperature(event_time, forecast_items)
                if event_temp is None:
                    event_temp = current_weather["current_temp"]

                event_item = {
                    "dt": event_time,
                    "temp": event_temp,
                    "feels_like": current_weather["feels_like"],
                    "icon": event_type,
                    "description": event_desc,
                    "is_now": False,
                    "is_special": True,
                    "special_type": event_type,
                }
                enhanced_items.append(event_item)

    return enhanced_items


def find_nearby_forecast_item(items, target_time, tolerance_seconds):
    """Find forecast item within tolerance of target time"""
    for item in items:
        if not item.get("is_now") and not item.get("is_special"):
            if abs(item["dt"] - target_time) <= tolerance_seconds:
                return item
    return None


def fetch_weather_data(config_dict=None, http_client=None):
    """Fetch weather data using configured provider with injected HTTP client"""
    if config_dict is None:
        log("No weather config provided")
        return None

    # Use default HTTP client if none provided (for hardware)
    if http_client is None:
        from weather.http_client import HTTPClient

        http_client = HTTPClient()

    # Get provider from config
    provider = getattr(config, "WEATHER_PROVIDER", "openweathermap")
    log(f"Using weather provider: {provider}")

    weather_data = None
    if provider == "openweathermap":
        timezone_offset = config_dict.get("timezone_offset_hours", -5)
        weather_data = openweathermap.fetch_openweathermap_data(
            http_client, config_dict, timezone_offset
        )

    elif provider == "open_meteo":
        lat = config_dict.get("latitude")
        lon = config_dict.get("longitude")
        if lat is None or lon is None:
            log("Open-Meteo requires latitude and longitude")
            return None

        weather_data = open_meteo.fetch_open_meteo_data(http_client, lat, lon)
        if not weather_data:
            log("Open-Meteo fetch failed")
            return None

        weather_data = convert_weather_data_to_legacy_format(weather_data)

    else:
        log(f"Unknown weather provider: {provider}")
        return None

    # Always fetch weatherbit alerts if API key is configured
    weatherbit_api_key = getattr(config, "WEATHERBIT_API_KEY", None)
    if weather_data and weatherbit_api_key:
        lat = config_dict.get("latitude")
        lon = config_dict.get("longitude")

        if lat is not None and lon is not None:
            alerts_data = weatherbit.fetch_weatherbit_alerts(
                http_client, lat, lon, weatherbit_api_key
            )

            if alerts_data:
                weather_data["alerts"] = alerts_data
            else:
                weather_data["alerts"] = {"has_alerts": False, "alerts": []}
        else:
            log("Cannot fetch weatherbit alerts: missing lat/lon")
            weather_data["alerts"] = {"has_alerts": False, "alerts": []}
    else:
        weather_data["alerts"] = {"has_alerts": False, "alerts": []}

    return weather_data


def convert_weather_data_to_legacy_format(weather_data):
    """Convert new WeatherData model to legacy format for compatibility"""

    if isinstance(weather_data, WeatherData):
        # Convert WeatherData object to legacy format
        result = {
            "current": {
                "current_temp": weather_data.current_temp,
                "feels_like": weather_data.current_temp,  # Open-Meteo doesn't have feels_like
                "high_temp": weather_data.current_temp,  # Use current temp as placeholder
                "low_temp": weather_data.current_temp,  # Use current temp as placeholder
                "weather_desc": weather_data.current_description,
                "weather_icon": weather_data.current_icon,
                "humidity": weather_data.current_humidity,
                "wind_speed": 0,  # Open-Meteo basic API doesn't include wind
                "wind_gust": 0,  # Open-Meteo basic API doesn't include wind
                "current_timestamp": weather_data.timestamp,
            },
            "forecast": [f.to_dict() for f in weather_data.forecast],
            "city": {
                "name": weather_data.location or "Unknown",
                "country": "",
            },
        }
        return result

    # If already in legacy format, preserve air_quality if present
    if isinstance(weather_data, dict) and "air_quality" in weather_data:
        return weather_data

    return weather_data


def get_display_variables(weather_data):
    """Parse weather data into all variables needed for display"""
    if not weather_data or "current" not in weather_data:
        log("Invalid weather data format")
        return None

    # Parse current weather
    current_weather = parse_current_weather_from_forecast(weather_data)
    if not current_weather:
        log("No current weather data available")
        return None

    # Create enhanced forecast with NOW + sunrise/sunset
    forecast_items = create_enhanced_forecast_data(weather_data)

    if not forecast_items:
        log("No forecast data available")
        return None

    # Parse air quality data if available
    air_quality = None
    if weather_data.get("air_quality"):
        aqi_data = weather_data["air_quality"]
        air_quality = {
            "aqi": aqi_data.get("aqi", 1),
            "aqi_text": aqi_data.get("description", "Unknown"),
            "raw_aqi": aqi_data.get("raw_aqi", 0),
        }

    # Get current date info from weather API timestamp for accuracy
    api_timestamp = current_weather.get("current_timestamp")
    if api_timestamp:
        date_info = format_timestamp_to_date(api_timestamp)
        day_name = date_info["day_name"]
        day_num = date_info["day_num"]
        month_name = date_info["month_name"]
    else:
        day_name = None
        day_num = None
        month_name = None

    # Add zodiac sign if we have a timestamp
    zodiac_sign = None
    if api_timestamp:
        zodiac_sign = get_zodiac_sign_from_timestamp(api_timestamp)

    # Calculate moon phase icon name
    moon_icon_name = None
    if api_timestamp:
        moon_info = moon_phase.get_moon_info(api_timestamp)
        if moon_info:
            moon_icon_name = moon_phase.phase_to_icon_name(moon_info["phase"])

    # Return expected structure for display
    return {
        # Date info
        "day_name": day_name,
        "day_num": day_num,
        "month_name": month_name,
        # Current weather
        "current_temp": current_weather["current_temp"],
        "feels_like": current_weather["feels_like"],
        "high_temp": current_weather["high_temp"],
        "low_temp": current_weather["low_temp"],
        "weather_desc": current_weather["weather_desc"],
        "weather_icon_name": f"{current_weather['weather_icon']}.bmp",
        "sunrise_time": current_weather.get("sunrise_time"),
        "sunset_time": current_weather.get("sunset_time"),
        "sunrise_timestamp": current_weather.get("sunrise_timestamp"),
        "sunset_timestamp": current_weather.get("sunset_timestamp"),
        "humidity": current_weather.get("humidity", 0),
        "wind_speed": current_weather.get("wind_speed", 0),
        "wind_gust": current_weather.get("wind_gust", 0),
        # Forecast data
        "forecast_data": forecast_items,
        # Current timestamp for alternative header
        "current_timestamp": api_timestamp,
        # Air quality data
        "air_quality": air_quality,
        # Moon phase
        "moon_icon_name": moon_icon_name,
        # Zodiac sign
        "zodiac_sign": zodiac_sign,
        # Alerts data
        "alerts": weather_data.get("alerts"),
    }
