"""
Convert CSV weather records to weather API format using real CSV data
Minimal fallbacks - use CSV data directly
"""

import math
import os
import sys
from datetime import datetime

try:
    from astral import LocationInfo
    from astral.sun import sun

    ASTRAL_AVAILABLE = True
except ImportError:
    ASTRAL_AVAILABLE = False


def add_weather_api_to_path():
    """Add weather API module to path for imports"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    web_dir = os.path.dirname(current_dir)
    project_root = os.path.dirname(web_dir)
    circuitpy_400x300_path = os.path.join(project_root, "300x400", "CIRCUITPY")

    if circuitpy_400x300_path not in sys.path:
        sys.path.insert(0, circuitpy_400x300_path)

    if web_dir not in sys.path:
        sys.path.insert(0, web_dir)


def wmo_code_to_icon(code, is_day=True):
    """Convert WMO weather code to OpenWeather icon format"""
    icon_map = {
        0: "01",
        1: "02",
        2: "03",
        3: "04",
        45: "50",
        48: "50",
        51: "09",
        53: "09",
        55: "09",
        61: "10",
        63: "10",
        65: "10",
        71: "13",
        73: "13",
        75: "13",
        80: "09",
        81: "10",
        82: "10",
        95: "11",
    }
    base_icon = icon_map.get(int(float(code)), "01")
    suffix = "d" if is_day else "n"
    return f"{base_icon}{suffix}"


def wmo_code_to_description(code):
    """Convert WMO weather code to description"""
    wmo_codes = {
        0: "clear sky",
        1: "mainly clear",
        2: "partly cloudy",
        3: "overcast",
        45: "fog",
        48: "depositing rime fog",
        51: "light drizzle",
        53: "moderate drizzle",
        55: "dense drizzle",
        61: "slight rain",
        63: "moderate rain",
        65: "heavy rain",
        71: "slight snow fall",
        73: "moderate snow fall",
        75: "heavy snow fall",
        80: "slight rain showers",
        81: "moderate rain showers",
        82: "violent rain showers",
        95: "thunderstorm",
    }
    return wmo_codes.get(int(float(code)), "unknown weather")


def calculate_sunrise_sunset(timestamp):
    """Calculate real sunrise/sunset times for NYC coordinates"""
    if not ASTRAL_AVAILABLE:
        # Fallback to hardcoded times
        day_start = timestamp - (timestamp % 86400)
        return day_start + (6 * 3600), day_start + (18 * 3600)

    try:
        dt = datetime.fromtimestamp(timestamp)
        # NYC coordinates
        nyc = LocationInfo("New York", "USA", "America/New_York", 40.7128, -74.0060)
        s = sun(nyc.observer, date=dt.date())

        sunrise_ts = int(s["sunrise"].timestamp())
        sunset_ts = int(s["sunset"].timestamp())
        return sunrise_ts, sunset_ts
    except Exception:
        # Fallback if calculation fails
        day_start = timestamp - (timestamp % 86400)
        return day_start + (6 * 3600), day_start + (18 * 3600)


def wind_direction_from_weather(weather_code):
    """Simple wind direction based on weather type"""
    code = int(float(weather_code))
    if code in [0, 1]:
        return 270  # Clear - westerly
    elif code in [2, 3]:
        return 225  # Cloudy - SW
    elif code >= 60:
        return 180  # Rain/storms - southerly
    else:
        return 270


def generate_forecast_hours(csv_record):
    """Generate 48 hours of forecast using CSV record as base"""
    base_timestamp = int(csv_record["timestamp"])
    base_temp = float(csv_record["temp"])
    base_code = csv_record["weather_code"]
    base_humidity = int(float(csv_record["humidity"]))
    base_feels = float(csv_record["feels_like"])
    base_wind = float(csv_record["wind_speed"])
    base_gust = float(csv_record["wind_gust"])
    base_vis = int(float(csv_record["visibility"]))
    precipitation = float(csv_record.get("precipitation", 0))

    # Convert precipitation to probability
    pop = min(0.8, precipitation * 10) if precipitation > 0 else 0.0

    forecast_list = []

    for hour in range(48):
        hour_timestamp = base_timestamp + (hour * 3600)
        dt = datetime.fromtimestamp(hour_timestamp)
        is_day = 6 <= dt.hour <= 18

        # Simple temperature variation: cooler at night, gradual daily change
        daily_cycle = 3 * math.sin((dt.hour - 4) * math.pi / 12)
        daily_trend = (hour // 24) * 1.0
        forecast_temp = base_temp + daily_cycle + daily_trend

        # Feels like varies with forecast temp
        feels_like = base_feels + (forecast_temp - base_temp)

        forecast_item = {
            "dt": hour_timestamp,
            "temp": round(forecast_temp, 1),
            "feels_like": round(feels_like, 1),
            "humidity": base_humidity,
            "icon": wmo_code_to_icon(base_code, is_day),
            "description": wmo_code_to_description(base_code),
            "pop": pop,
            "aqi": 2,
            "main": {
                "temp": forecast_temp,
                "feels_like": feels_like,
                "temp_min": float(csv_record.get("daily_low", forecast_temp - 2)),
                "temp_max": float(csv_record.get("daily_high", forecast_temp + 2)),
                "pressure": 1013,
                "humidity": base_humidity,
            },
            "weather": [
                {
                    "id": 800 + int(float(base_code)),
                    "main": wmo_code_to_description(base_code).title(),
                    "description": wmo_code_to_description(base_code),
                    "icon": wmo_code_to_icon(base_code, is_day),
                }
            ],
            "clouds": {"all": int(float(csv_record["cloud_cover"]))},
            "wind": {
                "speed": base_wind,
                "deg": wind_direction_from_weather(base_code),
                "gust": base_gust,
            },
            "visibility": base_vis,
            "sys": {"pod": "d" if is_day else "n"},
            "dt_txt": dt.strftime("%Y-%m-%d %H:%M:%S"),
        }
        forecast_list.append(forecast_item)

    return forecast_list


def convert_csv_record_to_weather_data(record):
    """Convert CSV record to weather API format"""
    timestamp = int(record["timestamp"])
    dt = datetime.fromtimestamp(timestamp)
    is_day = 6 <= dt.hour <= 18

    # Use CSV data directly - no fallback calculations
    temp = float(record["temp"])
    feels_like = float(record["feels_like"])
    humidity = int(float(record["humidity"]))
    visibility = int(float(record["visibility"]))
    cloud_cover = int(float(record["cloud_cover"]))
    wind_speed = float(record["wind_speed"])
    wind_gust = float(record["wind_gust"])
    weather_code = record["weather_code"]
    weather_desc = record["weather_desc"]
    uv_index = float(record.get("uv_index", 0))

    # Use daily highs/lows if available, otherwise use current temp as fallback
    daily_high = float(record.get("daily_high", temp))
    daily_low = float(record.get("daily_low", temp))

    # Calculate real sunrise/sunset times
    sunrise_ts, sunset_ts = calculate_sunrise_sunset(timestamp)

    # Current weather section
    current_weather = {
        "current_temp": round(temp),
        "feels_like": round(feels_like),
        "high_temp": round(daily_high),
        "low_temp": round(daily_low),
        "temp": temp,
        "temp_min": daily_low,
        "temp_max": daily_high,
        "pressure": 1013,
        "humidity": humidity,
        "visibility": visibility,
        "uv_index": uv_index,
        "clouds": cloud_cover,
        "wind_speed": wind_speed,
        "wind_gust": wind_gust,
        "wind_deg": wind_direction_from_weather(weather_code),
        "weather_desc": weather_desc,
        "weather_main": weather_desc.title(),
        "weather_icon": wmo_code_to_icon(weather_code, is_day),
        "icon": wmo_code_to_icon(weather_code, is_day),
        "sunrise": sunrise_ts,
        "sunset": sunset_ts,
        "sunrise_timestamp": sunrise_ts,
        "sunset_timestamp": sunset_ts,
        "current_timestamp": timestamp,
        "dt": timestamp,
        "city_name": "Historical Location",
        "country": "US",
    }

    # Generate forecast
    forecast_list = generate_forecast_hours(record)

    # Air quality data
    air_quality_data = {
        "list": [
            {
                "main": {"aqi": 2},
                "components": {
                    "co": 233.4,
                    "no": 0.01,
                    "no2": 16.7,
                    "o3": 72.66,
                    "so2": 0.64,
                    "pm2_5": 3.11,
                    "pm10": 3.76,
                    "nh3": 0.72,
                },
                "dt": timestamp,
            }
        ],
        "aqi": 2,
        "description": "Fair",
    }

    # Complete weather data structure
    weather_data = {
        "current": current_weather,
        "forecast": forecast_list,
        "air_quality": air_quality_data,
        "city": {
            "name": "Historical Location",
            "coord": {"lat": 40.7, "lon": -74.0},
            "country": "US",
            "timezone": -18000,
            "sunrise": sunrise_ts,
            "sunset": sunset_ts,
        },
    }

    return weather_data


def setup_mock_history_for_csv_record(record, csv_data_list=None):
    """Setup weather history for the last 10 days"""
    add_weather_api_to_path()

    try:
        from datetime import timedelta

        from mock_history import _mock_history_cache

        current_timestamp = int(record["timestamp"])
        current_date = datetime.fromtimestamp(current_timestamp)

        _mock_history_cache.clear()

        if csv_data_list:
            for days_back in range(1, 11):
                historical_date = current_date - timedelta(days=days_back)
                target_timestamp = int(historical_date.timestamp())

                # Find closest CSV record
                closest_record = None
                min_diff = float("inf")

                for csv_record in csv_data_list:
                    csv_timestamp = int(csv_record["timestamp"])
                    diff = abs(csv_timestamp - target_timestamp)
                    if diff < min_diff:
                        min_diff = diff
                        closest_record = csv_record

                if closest_record and min_diff < 86400:
                    temp = float(closest_record["temp"])
                    date_key = historical_date.strftime("%Y-%m-%d")
                    _mock_history_cache[date_key] = {
                        "current": temp,
                        "high": float(closest_record.get("daily_high", temp)),
                        "low": float(closest_record.get("daily_low", temp)),
                    }
    except ImportError:
        pass


def render_csv_record_to_image(record, output_path, csv_data_list=None):
    """Render CSV record to weather display image"""
    try:
        add_weather_api_to_path()

        from simple_web_render import render_400x300_weather_layout
        from weather_api import (
            get_display_variables,
            parse_current_weather_from_forecast,
        )

        # Setup historical data
        setup_mock_history_for_csv_record(record, csv_data_list)

        # Convert to weather API format
        weather_data = convert_csv_record_to_weather_data(record)

        # Parse using existing infrastructure
        display_vars = get_display_variables(weather_data)
        current_weather = parse_current_weather_from_forecast(weather_data)

        if not display_vars or not current_weather:
            print(f"Error: Failed to parse weather data for {record.get('date')}")
            return False

        # Use narrative from CSV
        narrative_text = record.get("narrative_text", "No narrative available")

        # Render image
        image = render_400x300_weather_layout(
            current_weather=current_weather,
            forecast_data=display_vars["forecast_data"],
            weather_desc=narrative_text,
            current_timestamp=display_vars["current_timestamp"],
            day_name=display_vars["day_name"],
            day_num=display_vars["day_num"],
            month_name=display_vars["month_name"],
            air_quality=display_vars.get("air_quality"),
            zodiac_sign=display_vars.get("zodiac_sign"),
        )

        if image:
            image.save(output_path, "PNG")
            return True
        else:
            return False

    except Exception as e:
        print(f"Error rendering {output_path}: {e}")
        return False
