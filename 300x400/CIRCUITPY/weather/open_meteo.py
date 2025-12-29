"""
Open-Meteo API provider
Free weather API service as alternative to OpenWeatherMap
"""

import json

from utils.logger import log

from weather.date_utils import format_timestamp_to_time, utc_to_local
from weather.weather_models import APIValidator


def fetch_open_meteo_data(http_client, lat, lon, timezone_offset_hours=-5):
    """Fetch data from Open-Meteo API using injected HTTP client"""
    # Open-Meteo API call
    url = "https://api.open-meteo.com/v1/forecast"

    # Build URL with params manually for CircuitPython compatibility
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,weather_code",
        "hourly": "temperature_2m,precipitation_probability,weather_code",
        "daily": "sunrise,sunset,temperature_2m_max,temperature_2m_min",
        "forecast_days": 3,
        "temperature_unit": "celsius",
        "timezone": "UTC",
    }

    param_str = "&".join([f"{k}={v}" for k, v in params.items()])
    full_url = f"{url}?{param_str}"

    try:
        api_response = http_client.get(full_url)
        return transform_open_meteo_response(api_response, timezone_offset_hours)

    except Exception as e:
        log(f"Open-Meteo API error: {e}")
        raise


def transform_open_meteo_response(api_response, timezone_offset_hours):
    """Transform Open-Meteo API response to same format as OpenWeatherMap"""
    # Validate required sections
    if "current" not in api_response:
        raise ValueError("Missing 'current' section in Open-Meteo response")
    if "hourly" not in api_response:
        raise ValueError("Missing 'hourly' section in Open-Meteo response")

    current_validator = APIValidator(api_response["current"], "Open-Meteo current")

    # Required current conditions
    current_temp = round(current_validator.require("temperature_2m"))
    weather_code = current_validator.require("weather_code")
    weather_desc = map_weather_code_to_description(weather_code)
    weather_icon = map_weather_code_to_icon(weather_code)

    # Parse timestamp and convert from UTC to local time
    time_str = current_validator.require("time")
    utc_timestamp = _parse_iso_timestamp(time_str)
    # Convert UTC to local time using existing utility
    current_timestamp = utc_to_local(utc_timestamp, timezone_offset_hours)

    # Optional with logging
    current_humidity = current_validator.optional("relative_humidity_2m", 0)

    # Parse daily data (sunrise/sunset, high/low temps)
    sunrise_timestamp = None
    sunset_timestamp = None
    high_temp = current_temp + 5  # Fallback
    low_temp = current_temp - 5  # Fallback

    if "daily" in api_response:
        daily_data = api_response["daily"]
        if "sunrise" in daily_data and daily_data["sunrise"]:
            sunrise_utc = _parse_iso_timestamp(daily_data["sunrise"][0])
            sunrise_timestamp = utc_to_local(sunrise_utc, timezone_offset_hours)
        if "sunset" in daily_data and daily_data["sunset"]:
            sunset_utc = _parse_iso_timestamp(daily_data["sunset"][0])
            sunset_timestamp = utc_to_local(sunset_utc, timezone_offset_hours)
        if "temperature_2m_max" in daily_data and daily_data["temperature_2m_max"]:
            high_temp = round(daily_data["temperature_2m_max"][0])
        if "temperature_2m_min" in daily_data and daily_data["temperature_2m_min"]:
            low_temp = round(daily_data["temperature_2m_min"][0])

    # Build current weather data
    current_weather = {
        "current_temp": current_temp,
        "feels_like": current_temp,  # Open-Meteo doesn't provide feels_like
        "high_temp": high_temp,
        "low_temp": low_temp,
        "weather_desc": weather_desc,
        "weather_icon": weather_icon,
        "humidity": current_humidity,
        "current_timestamp": current_timestamp,
        "sunrise_timestamp": sunrise_timestamp,
        "sunset_timestamp": sunset_timestamp,
    }

    # Add formatted sunrise/sunset times
    if sunrise_timestamp:
        current_weather["sunrise_time"] = format_timestamp_to_time(sunrise_timestamp)
    if sunset_timestamp:
        current_weather["sunset_time"] = format_timestamp_to_time(sunset_timestamp)

    # Transform forecast (use all hourly data)
    hourly = api_response["hourly"]
    hourly_validator = APIValidator(hourly, "Open-Meteo hourly")

    temps = hourly_validator.require("temperature_2m")
    pops = hourly_validator.optional("precipitation_probability", [])
    codes = hourly_validator.optional("weather_code", [])
    times = hourly_validator.require("time")

    forecast_items = []
    # Use all hourly forecast data (skip first hour which is current)
    for i in range(1, min(len(temps), 72)):  # Start at hour 1, up to 72 hours
        if i < len(temps):
            # Convert UTC timestamp to local time
            utc_dt = (
                _parse_iso_timestamp(times[i])
                if i < len(times)
                else utc_timestamp + (i * 3600)
            )
            local_dt = utc_to_local(utc_dt, timezone_offset_hours)

            forecast_item = {
                "dt": local_dt,
                "temp": round(temps[i]),
                "pop": (pops[i] / 100.0)
                if i < len(pops) and pops[i] is not None
                else 0.0,
                "icon": map_weather_code_to_icon(codes[i] if i < len(codes) else 0),
                "description": map_weather_code_to_description(
                    codes[i] if i < len(codes) else 0
                ),
            }
            forecast_items.append(forecast_item)

    # Generate weather narrative using the same function as OpenWeatherMap
    from weather.narrative import get_weather_narrative

    try:
        narrative = get_weather_narrative(
            current_weather, forecast_items, current_timestamp
        )
    except Exception as e:
        log(f"Error generating weather narrative: {e}")
        narrative = weather_desc

    # Build city info
    city_info = {
        "name": "Location",  # Open-Meteo doesn't provide city name
        "country": "",
    }
    if sunrise_timestamp:
        city_info["sunrise"] = sunrise_timestamp
    if sunset_timestamp:
        city_info["sunset"] = sunset_timestamp

    return {
        "current": current_weather,
        "forecast": forecast_items,
        "air_quality": {"description": "Good"},  # Open-Meteo doesn't provide AQI
        "city": city_info,
        # Add generated narrative for display
        "weather_desc": narrative,
    }


def map_weather_code_to_description(code):
    """Map Open-Meteo weather codes to descriptions"""
    code_map = {
        0: "Clear sky",
        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Overcast",
        45: "Fog",
        48: "Depositing rime fog",
        51: "Light drizzle",
        53: "Moderate drizzle",
        55: "Dense drizzle",
        56: "Light freezing drizzle",
        57: "Dense freezing drizzle",
        61: "Slight rain",
        63: "Moderate rain",
        65: "Heavy rain",
        66: "Light freezing rain",
        67: "Heavy freezing rain",
        71: "Slight snow fall",
        73: "Moderate snow fall",
        75: "Heavy snow fall",
        77: "Snow grains",
        80: "Slight rain showers",
        81: "Moderate rain showers",
        82: "Violent rain showers",
        85: "Slight snow showers",
        86: "Heavy snow showers",
        95: "Thunderstorm",
        96: "Thunderstorm with slight hail",
        99: "Thunderstorm with heavy hail",
    }
    return code_map.get(code, f"Unknown weather code {code}")


def map_weather_code_to_icon(code):
    """Map Open-Meteo weather codes to standard icon codes"""
    if code == 0:
        return "01d"  # Clear sky
    elif code in [1, 2]:
        return "02d"  # Partly cloudy
    elif code == 3:
        return "04d"  # Overcast
    elif code in [45, 48]:
        return "50d"  # Fog
    elif code in [51, 53, 55, 56, 57]:
        return "09d"  # Drizzle
    elif code in [61, 63, 65, 80, 81, 82]:
        return "10d"  # Rain
    elif code in [66, 67]:
        return "13d"  # Freezing rain
    elif code in [71, 73, 75, 77, 85, 86]:
        return "13d"  # Snow
    elif code in [95, 96, 99]:
        return "11d"  # Thunderstorm
    else:
        return "01d"  # Default to clear


def _parse_iso_timestamp(time_str):
    """Parse ISO 8601 timestamp to Unix timestamp"""
    try:
        # Simple parser for YYYY-MM-DDTHH:MM format
        # Example: "2024-01-15T14:30"
        date_part, time_part = time_str.split("T")
        year, month, day = map(int, date_part.split("-"))
        hour, minute = map(int, time_part.split(":"))

        # More accurate Unix timestamp calculation
        # Account for leap years properly
        days_since_epoch = 0

        # Add days for complete years since 1970
        for y in range(1970, year):
            if y % 4 == 0 and (y % 100 != 0 or y % 400 == 0):
                days_since_epoch += 366  # leap year
            else:
                days_since_epoch += 365

        # Add days for complete months in the target year
        days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0):
            days_in_month[1] = 29  # February in leap year

        days_since_epoch += sum(days_in_month[: month - 1])

        # Add days for the current month (day - 1 because day 1 = 0 days elapsed)
        days_since_epoch += day - 1

        return int(days_since_epoch * 86400 + hour * 3600 + minute * 60)

    except Exception:
        # Fallback to current time
        try:
            import time

            return int(time.time())
        except ImportError:
            return 0
