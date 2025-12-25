"""
Shared weather engine - extracts working mock weather logic for reuse
Core functions that both web server and static scripts can call
"""

import os
import sys
from datetime import datetime

# Default air quality fallback (single source of truth)
DEFAULT_AIR_QUALITY = {"aqi": 1, "aqi_text": "Good"}


def add_circuitpy_to_path():
    """Add 300x400/CIRCUITPY to path for weather modules"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    circuitpy_path = os.path.join(current_dir, "..", "300x400", "CIRCUITPY")
    if circuitpy_path not in sys.path:
        sys.path.insert(0, circuitpy_path)


def generate_weather_display_for_timestamp(csv_path, timestamp):
    """
    Core function that generates complete weather display data for a given timestamp

    Args:
        csv_path: Path to historical CSV file
        timestamp: Unix timestamp (int) for the desired hour

    Returns:
        tuple: (weather_data, narrative, display_vars, current_weather)

    Raises:
        Exception: If CSV data missing or parsing fails
    """

    # Add paths for imports
    add_circuitpy_to_path()

    # Import required modules
    import weather_narrative
    from mock_history import compare_with_yesterday_web, compute_mock_history
    from mock_weather_data import generate_scenario_data
    from openweathermap import parse_full_response
    from weather_api import get_display_variables, parse_current_weather_from_forecast
    from weather_narrative import get_weather_narrative

    # Generate mock weather data from CSV
    mock_data = generate_scenario_data("ny_2024", timestamp)
    if not mock_data:
        raise Exception(f"Failed to generate mock data for timestamp {timestamp}")

    # Extract forecast and air quality data
    if isinstance(mock_data, dict) and "forecast" in mock_data:
        forecast_response = mock_data["forecast"]
        air_quality_response = mock_data.get("air_quality", DEFAULT_AIR_QUALITY)
    else:
        forecast_response = mock_data
        air_quality_response = DEFAULT_AIR_QUALITY

    # Parse through OpenWeatherMap module to get provider format
    timezone_offset = -5  # EST/EDT for NYC
    parsed_mock_data = parse_full_response(
        forecast_response, air_quality_response, timezone_offset
    )

    if not parsed_mock_data:
        raise Exception(f"Failed to parse mock data for timestamp {timestamp}")

    # Compute mock history from CSV data for yesterday comparisons
    mock_history = compute_mock_history(mock_data)
    if len(mock_history) == 0:
        print(f"Warning: No historical data found for timestamp {timestamp}")

    # Parse weather data
    current_weather = parse_current_weather_from_forecast(parsed_mock_data)
    display_vars = get_display_variables(parsed_mock_data)

    if not current_weather or not display_vars:
        raise Exception(
            f"Failed to parse weather/display vars for timestamp {timestamp}"
        )

    # Generate narrative with history comparisons
    original_compare = weather_narrative.compare_with_yesterday
    weather_narrative.compare_with_yesterday = (
        lambda ct, ht, lt, ts: compare_with_yesterday_web(ct, ht, lt, ts, use_mock=True)
    )

    try:
        narrative = get_weather_narrative(
            current_weather,
            display_vars["forecast_data"],
            current_weather.get("current_timestamp"),
        )
    finally:
        # Restore original function
        weather_narrative.compare_with_yesterday = original_compare

    if not narrative:
        raise Exception(f"Failed to generate narrative for timestamp {timestamp}")

    return parsed_mock_data, narrative, display_vars, current_weather


def render_weather_to_image(weather_data, narrative, display_vars, current_weather):
    """
    Core rendering function that creates PIL image from weather display data

    Args:
        weather_data: Parsed weather data from generate_weather_display_for_timestamp
        narrative: Generated narrative text
        display_vars: Display variables from get_display_variables
        current_weather: Current weather data from parse_current_weather_from_forecast

    Returns:
        PIL.Image: Rendered weather display image

    Raises:
        Exception: If rendering fails
    """

    # Add paths for imports
    add_circuitpy_to_path()

    from simple_web_render import render_400x300_weather_layout

    # Extract data for rendering
    forecast_data = display_vars["forecast_data"]
    current_timestamp = current_weather.get("current_timestamp")
    day_name = display_vars.get("day_name")
    day_num = display_vars.get("day_num")
    month_name = display_vars.get("month_name")
    air_quality = display_vars.get("air_quality")
    zodiac_sign = display_vars.get("zodiac_sign")

    # Render the complete weather layout
    image = render_400x300_weather_layout(
        current_weather=current_weather,
        forecast_data=forecast_data,
        weather_desc=narrative,
        current_timestamp=current_timestamp,
        day_name=day_name,
        day_num=day_num,
        month_name=month_name,
        air_quality=air_quality,
        zodiac_sign=zodiac_sign,
    )

    if not image:
        raise Exception("render_400x300_weather_layout returned None")

    return image


def generate_complete_weather_display(csv_path, timestamp):
    """
    Convenience function that generates weather display and renders to image in one call

    Args:
        csv_path: Path to historical CSV file
        timestamp: Unix timestamp (int) for the desired hour

    Returns:
        tuple: (image, narrative, metrics_dict)

    Raises:
        Exception: If any step fails
    """

    # Generate weather display data
    weather_data, narrative, display_vars, current_weather = (
        generate_weather_display_for_timestamp(csv_path, timestamp)
    )

    # Render to image
    image = render_weather_to_image(
        weather_data, narrative, display_vars, current_weather
    )

    # Create metrics dict for compatibility with static scripts
    dt = datetime.fromtimestamp(timestamp)
    metrics = {
        "timestamp": timestamp,
        "date": dt.strftime("%Y-%m-%d"),
        "hour": dt.strftime("%H:%M"),
        "narrative_text": narrative,
        "temp": current_weather.get("current_temp"),
        "weather_desc": current_weather.get("weather_desc"),
    }

    return image, narrative, metrics
