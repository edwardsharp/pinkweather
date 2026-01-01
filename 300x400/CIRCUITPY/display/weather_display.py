"""
Weather display module - reusable functions for weather data processing and display
Extracted from code.py to be shared between hardware and preview
"""

from utils.logger import log, log_error
from weather.narrative import get_weather_narrative

from display.header import create_weather_layout
from display.severe_alert import create_alert_overlay


# note, preview server will use generate_weather_narrative
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
            "air_quality": weather_data.get("air_quality"),
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
        log_error(f"Error generating weather narrative: {e}")
        # Use basic description instead
        return weather_data.get("weather_desc", "Weather information unavailable")


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

    # Add severe weather alert overlay if alerts exist
    alerts_data = weather_data.get("alerts")
    log(f"DEBUG: alerts_data = {alerts_data}")
    if alerts_data:
        log(f"DEBUG: Found alerts data, calling create_alert_overlay")
        alert_overlay = create_alert_overlay(icon_loader, alerts_data)
        if alert_overlay:
            log(f"DEBUG: Alert overlay created successfully, appending to layout")
            layout.append(alert_overlay)
        else:
            log(f"DEBUG: create_alert_overlay returned None")
    else:
        log(f"DEBUG: No alerts data found in weather_data")

    return layout
