"""
Open-Meteo API provider
Free weather API service as alternative to OpenWeatherMap
"""

import json

from utils.logger import log

from weather.weather_models import APIValidator, ForecastData, WeatherData


def fetch_open_meteo_data(http_client, lat, lon):
    """Fetch data from Open-Meteo API using injected HTTP client"""
    # Open-Meteo API call
    url = "https://api.open-meteo.com/v1/forecast"

    # Build URL with params manually for CircuitPython compatibility
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,weather_code",
        "hourly": "temperature_2m,precipitation_probability,weather_code",
        "forecast_days": 3,
        "temperature_unit": "celsius",
        "timezone": "auto",
    }

    param_str = "&".join([f"{k}={v}" for k, v in params.items()])
    full_url = f"{url}?{param_str}"

    try:
        api_response = http_client.get(full_url)
        return transform_open_meteo_response(api_response)

    except Exception as e:
        log(f"Open-Meteo API error: {e}")
        raise


def transform_open_meteo_response(api_response):
    """Transform Open-Meteo API response to common weather model"""
    # Validate required sections
    if "current" not in api_response:
        raise ValueError("Missing 'current' section in Open-Meteo response")
    if "hourly" not in api_response:
        raise ValueError("Missing 'hourly' section in Open-Meteo response")

    weather_data = WeatherData()
    current_validator = APIValidator(api_response["current"], "Open-Meteo current")

    # Required current conditions
    weather_data.current_temp = round(current_validator.require("temperature_2m"))
    weather_code = current_validator.require("weather_code")
    weather_data.current_description = map_weather_code_to_description(weather_code)
    weather_data.current_icon = map_weather_code_to_icon(weather_code)

    # Parse timestamp
    time_str = current_validator.require("time")
    weather_data.timestamp = _parse_iso_timestamp(time_str)

    # Optional with logging
    weather_data.current_humidity = current_validator.optional(
        "relative_humidity_2m", 0
    )

    # Transform forecast (sample every 24 hours from hourly data)
    hourly = api_response["hourly"]
    hourly_validator = APIValidator(hourly, "Open-Meteo hourly")

    temps = hourly_validator.require("temperature_2m")
    pops = hourly_validator.optional("precipitation_probability", [])
    codes = hourly_validator.optional("weather_code", [])
    times = hourly_validator.require("time")

    # Sample every 24 hours for 3 days
    for i in range(24, min(72, len(temps)), 24):  # Start at +24h, skip current hour
        if i < len(temps):
            forecast = ForecastData()
            forecast.dt = (
                _parse_iso_timestamp(times[i])
                if i < len(times)
                else weather_data.timestamp + (i * 3600)
            )
            forecast.temp = round(temps[i])
            forecast.pop = (pops[i] / 100.0) if i < len(pops) else 0.0
            forecast.icon = map_weather_code_to_icon(codes[i] if i < len(codes) else 0)
            weather_data.forecast.append(forecast)

    return weather_data


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

        # Simple Unix timestamp calculation (approximate)
        # This is a basic implementation for CircuitPython compatibility
        days_since_epoch = (year - 1970) * 365 + (year - 1970) // 4
        days_since_epoch += sum(
            [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][: month - 1]
        )
        if month > 2 and year % 4 == 0:
            days_since_epoch += 1
        days_since_epoch += day - 1

        return int(days_since_epoch * 86400 + hour * 3600 + minute * 60)

    except Exception:
        # Fallback to current time
        try:
            import time

            return int(time.time())
        except ImportError:
            return 0
