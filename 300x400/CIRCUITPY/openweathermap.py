"""
OpenWeatherMap API module for PinkWeather
Handles API calls and data parsing for OpenWeatherMap.org
"""

from date_utils import utc_to_local
from logger import log


def manual_capitalize(text):
    """Manually capitalize first letter for CircuitPython compatibility"""
    if not text:
        return text
    return text[0].upper() + text[1:] if len(text) > 1 else text.upper()


def get_api_urls(lat, lon, api_key, units="metric"):
    """Generate OpenWeatherMap API URLs for forecast and air quality"""
    if not api_key or not lat or not lon:
        return None

    base_params = f"lat={lat}&lon={lon}&appid={api_key}&units={units}"
    aqi_params = f"lat={lat}&lon={lon}&appid={api_key}"

    return {
        "forecast": f"https://api.openweathermap.org/data/2.5/forecast?{base_params}",
        "air_quality": f"https://api.openweathermap.org/data/2.5/air_pollution/forecast?{aqi_params}",
    }


def parse_air_quality_data(aqi_data):
    """Parse OpenWeatherMap air quality response into app format"""
    if not aqi_data or "list" not in aqi_data or not aqi_data["list"]:
        return None

    try:
        # Use first (most recent) air quality measurement from forecast
        current_aqi = aqi_data["list"][0]
        aqi_value = current_aqi["main"]["aqi"]

        # Map AQI number to word description
        aqi_descriptions = {
            1: "Good",
            2: "Fair",
            3: "Moderate",
            4: "Poor",
            5: "Very Poor",
        }

        return {
            "aqi": aqi_value,
            "description": aqi_descriptions.get(aqi_value, "Unknown"),
            "list": aqi_data["list"],  # Include full list for forecast matching
        }

    except (KeyError, TypeError, ValueError) as e:
        log(f"Error parsing air quality data: {e}")
        return None


def parse_current_weather(forecast_data, timezone_offset_hours):
    """Parse current weather from OpenWeatherMap forecast response (first item + city data)"""
    if not forecast_data or "list" not in forecast_data or "city" not in forecast_data:
        return None

    try:
        # Use first forecast item as current weather
        current_item = forecast_data["list"][0]
        city_data = forecast_data["city"]

        parsed = {
            "current_temp": round(current_item["main"]["temp"]),
            "feels_like": round(current_item["main"]["feels_like"]),
            "high_temp": round(current_item["main"]["temp_max"]),
            "low_temp": round(current_item["main"]["temp_min"]),
            "weather_desc": manual_capitalize(
                current_item["weather"][0]["description"]
            ),
            "weather_icon": current_item["weather"][0]["icon"],
            "city_name": city_data["name"],
            "country": city_data["country"],
            "humidity": current_item["main"].get("humidity", 0),
            "wind_speed": current_item.get("wind", {}).get("speed", 0),
            "wind_gust": current_item.get("wind", {}).get("gust", 0),
        }

        # Add current timestamp (convert UTC to local)
        parsed["current_timestamp"] = utc_to_local(
            current_item["dt"], timezone_offset_hours
        )

        # Add sunrise/sunset from city data
        if "sunrise" in city_data and "sunset" in city_data:
            sunrise_ts = city_data["sunrise"]
            sunset_ts = city_data["sunset"]

            # Convert UTC timestamps to local time
            sunrise_local = utc_to_local(sunrise_ts, timezone_offset_hours)
            sunset_local = utc_to_local(sunset_ts, timezone_offset_hours)

            parsed["sunrise_timestamp"] = sunrise_local
            parsed["sunset_timestamp"] = sunset_local
        else:
            parsed["sunrise_timestamp"] = None
            parsed["sunset_timestamp"] = None

        return parsed

    except (KeyError, TypeError, ValueError) as e:
        log(f"Error parsing current weather: {e}")
        return None


def parse_forecast_data(forecast_data, timezone_offset_hours, air_quality_data=None):
    """Parse OpenWeatherMap forecast response into app format (skip first item since it's current)"""
    if not forecast_data or "list" not in forecast_data:
        return []

    try:
        forecast_items = []

        # Create air quality lookup by timestamp if available
        aqi_lookup = {}
        if air_quality_data and "list" in air_quality_data:
            for aqi_item in air_quality_data["list"]:
                if "dt" in aqi_item and "main" in aqi_item:
                    aqi_timestamp = utc_to_local(aqi_item["dt"], timezone_offset_hours)
                    aqi_lookup[aqi_timestamp] = aqi_item["main"]["aqi"]

        # Parse forecast items (skip first item - it's used as current weather)
        for item in forecast_data["list"][1:]:
            # Convert UTC timestamp to local time
            local_timestamp = utc_to_local(item["dt"], timezone_offset_hours)

            # Find matching AQI data (within 30 minutes)
            item_aqi = None
            for aqi_ts, aqi_val in aqi_lookup.items():
                if abs(local_timestamp - aqi_ts) <= 1800:  # 30 minutes
                    item_aqi = aqi_val
                    break

            forecast_item = {
                "dt": local_timestamp,  # Local timestamp
                "temp": round(item["main"]["temp"]),
                "feels_like": round(item["main"]["feels_like"]),
                "humidity": item["main"].get("humidity", 0),
                "icon": item["weather"][0]["icon"],
                "description": manual_capitalize(item["weather"][0]["description"]),
                "pop": item.get("pop", 0),  # Precipitation probability
                "aqi": item_aqi,
            }

            # Add precipitation data if available
            if "rain" in item:
                forecast_item["rain"] = item["rain"].get("3h", 0)
            if "snow" in item:
                forecast_item["snow"] = item["snow"].get("3h", 0)

            forecast_items.append(forecast_item)

        return forecast_items

    except (KeyError, TypeError, ValueError) as e:
        log(f"Error parsing forecast data: {e}")
        return []


def parse_full_response(forecast_response, air_quality_response, timezone_offset_hours):
    """Parse complete OpenWeatherMap API responses into app data format"""

    # Parse current weather
    current_weather = parse_current_weather(forecast_response, timezone_offset_hours)
    if not current_weather:
        return None

    # Parse air quality
    air_quality = (
        parse_air_quality_data(air_quality_response) if air_quality_response else None
    )

    # Parse forecast data
    forecast_items = parse_forecast_data(
        forecast_response, timezone_offset_hours, air_quality
    )

    # Add city data for sunrise/sunset
    city_info = None
    if forecast_response and "city" in forecast_response:
        city_data = forecast_response["city"]
        city_info = {
            "name": city_data.get("name"),
            "country": city_data.get("country"),
            "sunrise": utc_to_local(city_data.get("sunrise", 0), timezone_offset_hours),
            "sunset": utc_to_local(city_data.get("sunset", 0), timezone_offset_hours),
        }

    return {
        "current": current_weather,
        "forecast": forecast_items,
        "air_quality": air_quality,
        "city": city_info,
    }


def fetch_weather_data_circuitpy(config, timezone_offset_hours):
    """Fetch OpenWeatherMap data using CircuitPython requests"""
    try:
        import ssl

        import adafruit_requests
        import socketpool
        import wifi

        urls = get_api_urls(
            config["latitude"],
            config["longitude"],
            config["api_key"],
            config.get("units", "metric"),
        )

        if not urls:
            log("Error: Missing required config for OpenWeatherMap API")
            return None

        # Create requests session for CircuitPython
        pool = socketpool.SocketPool(wifi.radio)
        context = ssl.create_default_context()
        requests = adafruit_requests.Session(pool, context)

        log("Fetching forecast data from OpenWeatherMap...")
        forecast_response = requests.get(urls["forecast"])

        if forecast_response.status_code != 200:
            log(f"Forecast API error: {forecast_response.status_code}")
            return None

        forecast_data = forecast_response.json()

        # Fetch air quality data
        air_quality_data = None
        try:
            log("Fetching air quality data from OpenWeatherMap...")
            aqi_response = requests.get(urls["air_quality"])
            if aqi_response.status_code == 200:
                air_quality_data = aqi_response.json()
            else:
                log(f"Air quality API error: {aqi_response.status_code}")
        except Exception as e:
            log(f"Air quality fetch failed: {e}")

        return parse_full_response(
            forecast_data, air_quality_data, timezone_offset_hours
        )

    except Exception as e:
        log(f"Error fetching OpenWeatherMap data: {e}")
        return None


def fetch_weather_data_python(config, timezone_offset_hours):
    """Fetch OpenWeatherMap data using standard Python requests"""
    try:
        import requests

        urls = get_api_urls(
            config["latitude"],
            config["longitude"],
            config["api_key"],
            config.get("units", "metric"),
        )

        if not urls:
            log("Error: Missing required config for OpenWeatherMap API")
            return None

        log("Fetching forecast data from OpenWeatherMap...")
        forecast_response = requests.get(urls["forecast"], timeout=10)
        forecast_response.raise_for_status()
        forecast_data = forecast_response.json()

        # Fetch air quality data
        air_quality_data = None
        try:
            log("Fetching air quality data from OpenWeatherMap...")
            aqi_response = requests.get(urls["air_quality"], timeout=10)
            aqi_response.raise_for_status()
            air_quality_data = aqi_response.json()
        except Exception as e:
            log(f"Air quality fetch failed: {e}")

        return parse_full_response(
            forecast_data, air_quality_data, timezone_offset_hours
        )

    except Exception as e:
        log(f"Error fetching OpenWeatherMap data: {e}")
        return None
