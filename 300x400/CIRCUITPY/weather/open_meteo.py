"""
Open-Meteo API provider
Free weather API service as alternative to OpenWeatherMap
"""

from utils.logger import log

from weather.date_utils import (
    format_timestamp_to_date,
    format_timestamp_to_time,
    utc_to_local,
)
from weather.weather_models import APIValidator


def fetch_open_meteo_data(http_client, lat, lon, timezone_offset_hours=-5):
    """Fetch data from Open-Meteo API using injected HTTP client"""
    # Open-Meteo weather API call
    weather_url = "https://api.open-meteo.com/v1/forecast"
    weather_params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,weather_code,uv_index",
        "hourly": "temperature_2m,precipitation_probability,weather_code,uv_index",
        "forecast_days": 3,
        "temperature_unit": "celsius",
        "timezone": "UTC",
    }

    weather_param_str = "&".join([f"{k}={v}" for k, v in weather_params.items()])
    weather_full_url = f"{weather_url}?{weather_param_str}"

    # Open-Meteo air quality API call
    aqi_url = "https://air-quality-api.open-meteo.com/v1/air-quality"
    aqi_params = {
        "latitude": lat,
        "longitude": lon,
        "current": "us_aqi",
        "hourly": "us_aqi",
        "forecast_days": 3,
        "timezone": "UTC",
    }

    aqi_param_str = "&".join([f"{k}={v}" for k, v in aqi_params.items()])
    aqi_full_url = f"{aqi_url}?{aqi_param_str}"

    try:
        # Fetch weather data
        log("Fetching weather data from Open-Meteo...")
        weather_response = http_client.get(weather_full_url)

        # Fetch air quality data
        aqi_response = None
        try:
            log("Fetching air quality data from Open-Meteo...")
            aqi_response = http_client.get(aqi_full_url)
        except Exception as e:
            log(f"Air quality fetch failed: {e}")

        return transform_open_meteo_response(
            weather_response, timezone_offset_hours, aqi_response
        )

    except Exception as e:
        log(f"Open-Meteo API error: {e}")
        raise


def transform_open_meteo_response(
    api_response, timezone_offset_hours, aqi_response=None
):
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
    current_uv_index = current_validator.optional("uv_index", 0)

    # Calculate high/low temps from hourly data and estimate sunrise/sunset
    sunrise_timestamp = None
    sunset_timestamp = None
    high_temp = current_temp + 5  # Fallback
    low_temp = current_temp - 5  # Fallback

    # Calculate high/low from hourly forecast for today
    hourly = api_response.get("hourly", {})
    if "temperature_2m" in hourly and hourly["temperature_2m"]:
        # Take first 24 hours for today's high/low
        today_temps = hourly["temperature_2m"][:24]
        if today_temps:
            high_temp = round(max(today_temps))
            low_temp = round(min(today_temps))

    # Simple sunrise/sunset estimation (winter times, adjust as needed)
    # Get date components from current timestamp
    date_info = format_timestamp_to_date(current_timestamp)

    # Calculate start of day timestamp (midnight)
    # Days since epoch calculation
    days_since_epoch = current_timestamp // 86400
    start_of_day = days_since_epoch * 86400

    # Approximate times (7:30 AM / 5:30 PM local time)
    sunrise_timestamp = start_of_day + (7 * 3600) + (30 * 60)  # 7:30 AM
    sunset_timestamp = start_of_day + (17 * 3600) + (30 * 60)  # 5:30 PM

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
        "uv_index": round(current_uv_index, 1) if current_uv_index else 0,
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
    if temps and len(temps) > 1:
        for i in range(1, min(len(temps), 72)):  # Start at hour 1, up to 72 hours
            if i < len(temps):
                # Convert UTC timestamp to local time
                utc_dt = (
                    _parse_iso_timestamp(times[i])
                    if times and i < len(times)
                    else utc_timestamp + (i * 3600)
                )
                local_dt = utc_to_local(utc_dt, timezone_offset_hours)

                forecast_item = {
                    "dt": local_dt,
                    "temp": round(temps[i]),
                    "pop": (pops[i] / 100.0)
                    if pops and i < len(pops) and pops[i] is not None
                    else 0.0,
                    "icon": map_weather_code_to_icon(
                        codes[i] if codes and i < len(codes) else 0
                    ),
                    "description": map_weather_code_to_description(
                        codes[i] if codes and i < len(codes) else 0
                    ),
                }
                forecast_items.append(forecast_item)

    # Build city info
    city_info = {
        "name": "Location",  # Open-Meteo doesn't provide city name
        "country": "",
    }
    if sunrise_timestamp:
        city_info["sunrise"] = sunrise_timestamp
    if sunset_timestamp:
        city_info["sunset"] = sunset_timestamp

    # Parse air quality data
    air_quality_data = parse_air_quality_data(aqi_response) if aqi_response else None
    if not air_quality_data:
        # Fallback for when AQI API fails
        air_quality_data = {
            "aqi": 1,
            "raw_aqi": 25,
            "description": "Good",
        }

    # Add air quality to current weather data for narrative generation
    current_weather["air_quality"] = air_quality_data

    # Generate weather narrative using the same function as OpenWeatherMap
    from weather.narrative import get_weather_narrative

    try:
        narrative = get_weather_narrative(
            current_weather, forecast_items, current_timestamp
        )
    except Exception as e:
        log(f"Error generating weather narrative: {e}")
        narrative = weather_desc

    return {
        "current": current_weather,
        "forecast": forecast_items,
        "air_quality": air_quality_data,
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


def parse_air_quality_data(aqi_response):
    """Parse Open-Meteo air quality response and map to OpenWeatherMap format"""
    if not aqi_response or "current" not in aqi_response:
        return None

    try:
        current_aqi = aqi_response["current"]

        # Get raw US AQI value
        raw_aqi = current_aqi.get("us_aqi", 0)
        if raw_aqi is None:
            raw_aqi = 0

        # Map US AQI to OpenWeatherMap 1-5 scale
        if raw_aqi <= 50:
            aqi_scale = 1
            description = "Good"
        elif raw_aqi <= 100:
            aqi_scale = 2
            description = "Fair"
        elif raw_aqi <= 150:
            aqi_scale = 3
            description = "Moderate"
        elif raw_aqi <= 200:
            aqi_scale = 4
            description = "Poor"
        else:
            aqi_scale = 5
            description = "Very Poor"

        return {
            "aqi": aqi_scale,
            "raw_aqi": int(raw_aqi),
            "description": description,
            "list": [],  # Empty list for compatibility
        }

    except (KeyError, TypeError, ValueError) as e:
        log(f"Error parsing air quality data: {e}")
        return None


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
