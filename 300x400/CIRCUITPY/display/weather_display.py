"""
Weather display module - reusable functions for weather data processing and display
Extracted from code.py to be shared between hardware and preview
"""

import time

import config
from utils.logger import log
from weather import weather_api
from weather.weather_narrative import get_weather_narrative

from display.header import create_weather_layout


def generate_weather_narrative(weather_data):
    """Generate rich weather narrative from weather data"""
    try:
        # Extract current weather info for narrative generation
        current_weather = {
            "current_temp": weather_data.get("current_temp", 0),
            "feels_like": weather_data.get("feels_like", 0),
            "high_temp": weather_data.get("high_temp", 0),
            "low_temp": weather_data.get("low_temp", 0),
            "weather_desc": weather_data.get("weather_desc", ""),
            "sunrise_time": weather_data.get("sunrise_time", "7:00a"),
            "sunset_time": weather_data.get("sunset_time", "5:00p"),
            "humidity": weather_data.get("humidity", 0),
            "wind_speed": weather_data.get("wind_speed", 0),
            "wind_gust": weather_data.get("wind_gust", 0),
        }

        forecast_data = weather_data.get("forecast_data", [])
        current_timestamp = weather_data.get("current_timestamp")

        # Generate the rich narrative
        narrative = get_weather_narrative(
            current_weather, forecast_data, current_timestamp
        )

        log(f"Generated weather narrative: {narrative}")
        return narrative

    except Exception as e:
        log(f"Error generating weather narrative: {e}")
        # Use basic description instead
        return weather_data.get("weather_desc", "Weather information unavailable")


def get_weather_display_data(http_client=None):
    """Get weather data for display - fetch fresh data from API"""

    # Build weather config from hardware config
    WEATHER_CONFIG = (
        {
            "api_key": config.OPENWEATHER_API_KEY,
            "latitude": config.LATITUDE,
            "longitude": config.LONGITUDE,
            "timezone_offset_hours": config.TIMEZONE_OFFSET_HOURS,
            "units": "metric",
        }
        if config.OPENWEATHER_API_KEY and config.LATITUDE and config.LONGITUDE
        else None
    )

    if WEATHER_CONFIG is None:
        log("Weather API not configured")
        return None

    # Fetch weather data
    for attempt in range(3):
        log(f"Fetching fresh weather data from API (attempt {attempt + 1}/3)")
        try:
            forecast_data = weather_api.fetch_weather_data(WEATHER_CONFIG, http_client)
            if forecast_data:
                display_vars = weather_api.get_display_variables(forecast_data)

                if display_vars:
                    log("Weather data fetch successful")
                    return display_vars
                else:
                    log("Weather data processing failed")
            else:
                log("Weather API returned no data")

            if attempt < 2:
                log("Retrying in 5 seconds...")
                time.sleep(5)
                continue
            return None

        except Exception as e:
            log(f"Weather fetch error (attempt {attempt + 1}): {e}")
            if attempt < 2 and "Name or service not known" in str(e):
                log("DNS error detected, waiting 10 seconds before retry...")
                time.sleep(10)
                continue
            return None

    return None


def create_weather_display_layout(
    weather_data, icon_loader=None, indoor_temp_humidity=None
):
    """Create complete weather layout with generated narrative

    Args:
        weather_data: Display variables from weather_api.get_display_variables()
        icon_loader: Function to load weather icons
        indoor_temp_humidity: Indoor temperature/humidity string (e.g. "20°69%")

    Returns:
        DisplayIO group containing complete weather layout
    """

    # Generate rich weather narrative
    weather_narrative = generate_weather_narrative(weather_data)

    # Create layout with all display parameters
    layout = create_weather_layout(
        current_timestamp=weather_data.get("current_timestamp"),
        forecast_data=weather_data.get("forecast_data", []),
        weather_desc=weather_narrative,  # Use generated narrative, not basic desc
        icon_loader=icon_loader,
        day_name=weather_data.get("day_name"),
        day_num=weather_data.get("day_num"),
        month_name=weather_data.get("month_name"),
        air_quality=weather_data.get("air_quality"),
        zodiac_sign=weather_data.get("zodiac_sign"),
        indoor_temp_humidity=indoor_temp_humidity,
    )

    return layout
