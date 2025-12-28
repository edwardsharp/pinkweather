"""
weather api module for pinkweather - provider-agnostic interface
works on both circuitpython hardware and standard python web server
"""

import config
from utils import moon_phase
from utils.astro_utils import get_zodiac_sign_from_timestamp
from utils.logger import log

from weather import open_meteo, openweathermap
from weather.date_utils import format_timestamp_to_date, format_timestamp_to_time
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
    """Create enhanced forecast with current weather as 'NOW' plus sunrise/sunset events"""
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

    # Store all special event times for filtering forecast items (all local)
    special_event_times = []

    # Add sunrise/sunset events from city data
    if "city" in weather_data and weather_data["city"]:
        city_data = weather_data["city"]
        if "sunrise" in city_data and "sunset" in city_data:
            # Timestamps are already in local time from provider
            sunrise_ts = city_data["sunrise"]
            sunset_ts = city_data["sunset"]

            # Calculate tomorrow's sunrise/sunset (add 24 hours) - already local
            tomorrow_sunrise_ts = sunrise_ts + 86400  # Local + 24 hours
            tomorrow_sunset_ts = sunset_ts + 86400  # Local + 24 hours

            # Include sunrise/sunset if they're in the future (within next 24 hours)
            future_window = 24 * 3600  # 24 hours from now

            # Today's sunrise/sunset - compare local times
            if current_timestamp <= sunrise_ts <= current_timestamp + future_window:
                # Calculate interpolated temperature for sunrise time
                sunrise_temp = interpolate_temperature(sunrise_ts, forecast_items)
                if sunrise_temp is None:
                    sunrise_temp = current_weather["current_temp"]

                sunrise_item = {
                    "dt": sunrise_ts,  # Store local time
                    "temp": sunrise_temp,
                    "feels_like": current_weather["feels_like"],
                    "icon": "sunrise",
                    "description": "Sunrise",
                    "is_now": False,
                    "is_special": True,
                    "special_type": "sunrise",
                }
                enhanced_items.append(sunrise_item)
                special_event_times.append(sunrise_ts)

            if current_timestamp <= sunset_ts <= current_timestamp + future_window:
                # Calculate interpolated temperature for sunset time
                sunset_temp = interpolate_temperature(sunset_ts, forecast_items)
                if sunset_temp is None:
                    sunset_temp = current_weather["current_temp"]

                sunset_item = {
                    "dt": sunset_ts,  # Store local time
                    "temp": sunset_temp,
                    "feels_like": current_weather["feels_like"],
                    "icon": "sunset",
                    "description": "Sunset",
                    "is_now": False,
                    "is_special": True,
                    "special_type": "sunset",
                }
                enhanced_items.append(sunset_item)
                special_event_times.append(sunset_ts)

            # Tomorrow's sunrise/sunset - compare local times
            if (
                current_timestamp
                <= tomorrow_sunrise_ts
                <= current_timestamp + future_window
            ):
                tomorrow_sunrise_temp = interpolate_temperature(
                    tomorrow_sunrise_ts, forecast_items
                )
                if tomorrow_sunrise_temp is None:
                    tomorrow_sunrise_temp = current_weather["current_temp"]

                tomorrow_sunrise_item = {
                    "dt": tomorrow_sunrise_ts,  # Store local time
                    "temp": tomorrow_sunrise_temp,
                    "feels_like": current_weather["feels_like"],
                    "icon": "sunrise",
                    "description": "Tomorrow Sunrise",
                    "is_now": False,
                    "is_special": True,
                    "special_type": "sunrise",
                }
                enhanced_items.append(tomorrow_sunrise_item)
                special_event_times.append(tomorrow_sunrise_ts)

            if (
                current_timestamp
                <= tomorrow_sunset_ts
                <= current_timestamp + future_window
            ):
                tomorrow_sunset_temp = interpolate_temperature(
                    tomorrow_sunset_ts, forecast_items
                )
                if tomorrow_sunset_temp is None:
                    tomorrow_sunset_temp = current_weather["current_temp"]

                tomorrow_sunset_item = {
                    "dt": tomorrow_sunset_ts,  # Store local time
                    "temp": tomorrow_sunset_temp,
                    "feels_like": current_weather["feels_like"],
                    "icon": "sunset",
                    "description": "Tomorrow Sunset",
                    "is_now": False,
                    "is_special": True,
                    "special_type": "sunset",
                }
                enhanced_items.append(tomorrow_sunset_item)
                special_event_times.append(tomorrow_sunset_ts)

    # Add regular forecast items (filter based on special events and current time)
    if forecast_items:
        for item in forecast_items:
            # Skip if forecast time is in the past (compare local times directly)
            if item["dt"] < current_timestamp:
                continue

            # Skip if too close to any special event (within 30 minutes) - all in local time
            too_close_to_special = False
            for special_time in special_event_times:
                if abs(item["dt"] - special_time) <= (30 * 60):
                    too_close_to_special = True
                    break

            if not too_close_to_special:
                # Mark regular forecast items but keep local timestamps
                item["is_now"] = False
                item["is_special"] = False
                enhanced_items.append(item)

    # Sort items: NOW first, then chronological order by timestamp
    def sort_key(item):
        if item.get("is_now", False):
            return (0, 0)  # NOW always first
        else:
            return (1, item["dt"])  # Everything else by timestamp

    enhanced_items.sort(key=sort_key)

    # Return up to 20 items for weather narrative analysis
    return enhanced_items[:20]


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

    if provider == "openweathermap":
        timezone_offset = config_dict.get("timezone_offset_hours", -5)
        return openweathermap.fetch_openweathermap_data(
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

        return convert_weather_data_to_legacy_format(weather_data)

    else:
        log(f"Unknown weather provider: {provider}")
        return None


def convert_weather_data_to_legacy_format(weather_data):
    """Convert new WeatherData model to legacy format for compatibility"""

    if isinstance(weather_data, WeatherData):
        # Convert WeatherData object to legacy format
        return {
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

    # If already in legacy format, return as-is
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
    }
