"""
shared weather api module for pinkweather
works on both circuitpython hardware and standard python web server
"""

import json

from date_utils import format_timestamp_to_date, format_timestamp_to_time, utc_to_local
from logger import log


def manual_capitalize(text):
    """Manually capitalize first letter for CircuitPython compatibility"""
    if not text:
        return text
    return text[0].upper() + text[1:] if len(text) > 1 else text.upper()


def get_weather_urls(config=None):
    """Generate OpenWeather API URLs with given configuration - forecast and air quality endpoints"""
    if config is None:
        return None

    # Check if required config values are present
    if (
        not config.get("api_key")
        or not config.get("latitude")
        or not config.get("longitude")
    ):
        return None

    base_params = f"lat={config['latitude']}&lon={config['longitude']}&appid={config['api_key']}&units={config.get('units', 'metric')}"

    # Air quality uses same lat/lon/appid but no units parameter
    aqi_params = (
        f"lat={config['latitude']}&lon={config['longitude']}&appid={config['api_key']}"
    )

    return {
        "forecast": f"https://api.openweathermap.org/data/2.5/forecast?{base_params}",
        "air_quality": f"https://api.openweathermap.org/data/2.5/air_pollution/forecast?{aqi_params}",
    }


def parse_air_quality(aqi_data):
    """Parse air quality data from OpenWeather API forecast response"""
    if not aqi_data or "list" not in aqi_data or not aqi_data["list"]:
        return None

    try:
        # Use first (most recent) air quality measurement from forecast
        current_aqi = aqi_data["list"][0]
        aqi_value = current_aqi["main"]["aqi"]

        # Map AQI number to word
        aqi_map = {1: "Good", 2: "Fair", 3: "Mid", 4: "Poor", 5: "Bad"}

        aqi_text = aqi_map.get(aqi_value, "Unknown")

        log(f"Air quality: {aqi_value} ({aqi_text})")

        return {"aqi": aqi_value, "aqi_text": aqi_text}
    except (KeyError, TypeError, ValueError) as e:
        log(f"Error parsing air quality data: {e}")
        return None


def parse_current_weather_from_forecast(forecast_data, timezone_offset_hours=None):
    """Parse current weather from forecast API response (first item + city data)"""
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

        # Add current timestamp from API for accurate date (convert UTC to local)
        parsed["current_timestamp"] = utc_to_local(
            current_item["dt"], timezone_offset_hours
        )

        # Add sunrise/sunset from city data
        if "sunrise" in city_data and "sunset" in city_data:
            sunrise_ts = city_data["sunrise"]
            sunset_ts = city_data["sunset"]

            # Convert UTC timestamps to local time immediately
            sunrise_local = utc_to_local(sunrise_ts, timezone_offset_hours)
            sunset_local = utc_to_local(sunset_ts, timezone_offset_hours)

            # Store both timestamps and formatted times (all in local time)
            parsed["sunrise_timestamp"] = sunrise_local
            parsed["sunset_timestamp"] = sunset_local
            parsed["sunrise_time"] = format_timestamp_to_time(
                sunrise_local, format_12h=True
            )
            parsed["sunset_time"] = format_timestamp_to_time(
                sunset_local, format_12h=True
            )
        else:
            parsed["sunrise_timestamp"] = None
            parsed["sunset_timestamp"] = None
            parsed["sunrise_time"] = None
            parsed["sunset_time"] = None

        return parsed

    except (KeyError, TypeError, ValueError) as e:
        log(f"Error parsing current weather from forecast: {e}")
        return None


def parse_forecast_data(forecast_data, timezone_offset_hours):
    """Parse forecast API response into display variables (skip first item since it's used as current)"""
    if not forecast_data or "list" not in forecast_data:
        return None

    try:
        forecast_items = []

        # Skip first item (used as current weather), take remaining items
        for item in forecast_data["list"][1:]:
            # Convert forecast timestamps to local time
            parsed_item = {
                "dt": utc_to_local(item["dt"], timezone_offset_hours),
                "temp": round(item["main"]["temp"], 1),
                "feels_like": round(item["main"]["feels_like"], 1),
                "icon": item["weather"][0]["icon"],
                "description": item["weather"][0]["description"],
            }
            forecast_items.append(parsed_item)

        return forecast_items

    except (KeyError, TypeError, ValueError) as e:
        log(f"Error parsing forecast data: {e}")
        return None


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


def create_enhanced_forecast_data(forecast_data, timezone_offset_hours=None):
    """Create enhanced forecast with current weather as 'NOW' plus sunrise/sunset events from single API"""
    if timezone_offset_hours is None:
        raise ValueError("timezone_offset_hours must be provided")

    enhanced_items = []

    # Parse current weather from forecast data
    current_weather = parse_current_weather_from_forecast(
        forecast_data, timezone_offset_hours
    )
    if not current_weather:
        return []

    current_timestamp = current_weather["current_timestamp"]  # Already in local time

    # Get forecast items for temperature interpolation
    forecast_items = parse_forecast_data(forecast_data, timezone_offset_hours)

    # Create "NOW" cell
    now_item = {
        "dt": current_timestamp,  # Use actual current timestamp (already local)
        "temp": current_weather["current_temp"],
        "feels_like": current_weather["feels_like"],
        "icon": current_weather["weather_icon"],
        "description": "Current conditions",
        "is_now": True,
    }
    enhanced_items.append(now_item)

    # Add sunrise/sunset events from city data
    if "city" in forecast_data:
        city_data = forecast_data["city"]
        if "sunrise" in city_data and "sunset" in city_data:
            # Convert UTC timestamps to local time
            sunrise_ts = utc_to_local(city_data["sunrise"], timezone_offset_hours)
            sunset_ts = utc_to_local(city_data["sunset"], timezone_offset_hours)

            # Calculate tomorrow's sunrise/sunset (add 24 hours) - already local
            tomorrow_sunrise_ts = sunrise_ts + 86400  # Local + 24 hours
            tomorrow_sunset_ts = sunset_ts + 86400  # Local + 24 hours

            # Include sunrise/sunset if they're in the future (within next 24 hours)
            # Don't show past sunrise/sunset events
            future_window = 24 * 3600  # 24 hours from now

            # Store all special event times for filtering forecast items (all local)
            special_event_times = []

            # Today's sunrise/sunset - compare local times
            log(f"DEBUG: Current time: {current_timestamp}, Sunrise: {sunrise_ts}")
            log(
                f"DEBUG: Time since sunrise: {(current_timestamp - sunrise_ts) / 3600:.1f} hours"
            )
            log(f"DEBUG: Future window: {future_window / 3600} hours")

            if current_timestamp <= sunrise_ts <= current_timestamp + future_window:
                # Calculate interpolated temperature for sunrise time
                sunrise_temp = interpolate_temperature(sunrise_ts, forecast_items)
                if sunrise_temp is None:
                    sunrise_temp = current_weather["current_temp"]

                sunrise_item = {
                    "dt": sunrise_ts,  # Store local time
                    "temp": sunrise_temp,
                    "feels_like": current_weather[
                        "feels_like"
                    ],  # Could also interpolate this
                    "icon": "sunrise",
                    "description": "Sunrise",
                    "is_now": False,
                    "is_special": True,
                    "special_type": "sunrise",
                }
                enhanced_items.append(sunrise_item)
                special_event_times.append(sunrise_ts)

            log(f"DEBUG: Current time: {current_timestamp}, Sunset: {sunset_ts}")
            log(
                f"DEBUG: Time until sunset: {(sunset_ts - current_timestamp) / 3600:.1f} hours"
            )

            if current_timestamp <= sunset_ts <= current_timestamp + future_window:
                # Calculate interpolated temperature for sunset time
                # Calculate interpolated temperature for sunset time
                sunset_temp = interpolate_temperature(sunset_ts, forecast_items)
                if sunset_temp is None:
                    sunset_temp = current_weather["current_temp"]

                sunset_item = {
                    "dt": sunset_ts,  # Store local time
                    "temp": sunset_temp,
                    "feels_like": current_weather[
                        "feels_like"
                    ],  # Could also interpolate this
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
                # Calculate interpolated temperature for tomorrow's sunrise time
                # Calculate interpolated temperature for tomorrow's sunrise time
                tomorrow_sunrise_temp = interpolate_temperature(
                    tomorrow_sunrise_ts, forecast_items
                )
                if tomorrow_sunrise_temp is None:
                    tomorrow_sunrise_temp = current_weather["current_temp"]

                tomorrow_sunrise_item = {
                    "dt": tomorrow_sunrise_ts,  # Store local time
                    "temp": tomorrow_sunrise_temp,
                    "feels_like": current_weather[
                        "feels_like"
                    ],  # Could also interpolate this
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
                # Calculate interpolated temperature for tomorrow's sunset time
                # Calculate interpolated temperature for tomorrow's sunset time
                tomorrow_sunset_temp = interpolate_temperature(
                    tomorrow_sunset_ts, forecast_items
                )
                if tomorrow_sunset_temp is None:
                    tomorrow_sunset_temp = current_weather["current_temp"]

                tomorrow_sunset_item = {
                    "dt": tomorrow_sunset_ts,  # Store local time
                    "temp": tomorrow_sunset_temp,
                    "feels_like": current_weather[
                        "feels_like"
                    ],  # Could also interpolate this
                    "icon": "sunset",
                    "description": "Tomorrow Sunset",
                    "is_now": False,
                    "is_special": True,
                    "special_type": "sunset",
                }
                enhanced_items.append(tomorrow_sunset_item)
                special_event_times.append(tomorrow_sunset_ts)

    # Add regular forecast items (filter based on special events and current time)
    # forecast_items already loaded above for temperature interpolation
    if forecast_items:
        for item in forecast_items:
            # Skip if forecast time is in the past (compare local times directly)
            if item["dt"] <= current_timestamp:
                continue

            # Skip if too close to any special event (within 30 minutes) - all in local time
            too_close_to_special = False
            if "special_event_times" in locals():
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


def get_display_variables(forecast_data, timezone_offset_hours=None):
    """Parse forecast API response into all variables needed for display"""

    # Handle both old format (direct forecast data) and new format (dict with forecast/air_quality)
    if isinstance(forecast_data, dict) and "forecast" in forecast_data:
        air_quality_data = forecast_data.get("air_quality")
        forecast_data = forecast_data["forecast"]
    else:
        # Legacy format - forecast_data is already the forecast data directly
        air_quality_data = None

    # Parse current weather from forecast data
    current_weather = parse_current_weather_from_forecast(
        forecast_data, timezone_offset_hours
    )
    if not current_weather:
        log("No current weather data available")
        return None

    # Create enhanced forecast with NOW + sunrise/sunset from single API
    if forecast_data:
        forecast_items = create_enhanced_forecast_data(
            forecast_data, timezone_offset_hours
        )
    else:
        log("No forecast data available")
        return None

    # Parse air quality data if available
    air_quality = None
    if air_quality_data:
        air_quality = parse_air_quality(air_quality_data)
        if air_quality:
            log(f"Air quality parsed: {air_quality['aqi_text']}")
        else:
            log("Failed to parse air quality data")
    else:
        log("No air quality data available")

    # Get current date info from weather API timestamp for accuracy
    if current_weather.get("current_timestamp"):
        api_timestamp = current_weather["current_timestamp"]
        if timezone_offset_hours is None:
            raise ValueError("timezone_offset_hours must be provided")

        # Convert timestamp to date components using centralized utility
        date_info = format_timestamp_to_date(api_timestamp)
        day_name = date_info["day_name"]
        day_num = date_info["day_num"]
        month_name = date_info["month_name"]
    else:
        # No timestamp available - return None values
        day_name = None
        day_num = None
        month_name = None

    # Combine everything for display
    display_vars = {
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
        "sunrise_time": current_weather["sunrise_time"],
        "sunset_time": current_weather["sunset_time"],
        "sunrise_timestamp": current_weather.get("sunrise_timestamp"),
        "sunset_timestamp": current_weather.get("sunset_timestamp"),
        "humidity": current_weather.get("humidity", 0),
        "wind_speed": current_weather.get("wind_speed", 0),
        "wind_gust": current_weather.get("wind_gust", 0),
        # Forecast data
        "forecast_data": forecast_items,
        # Current timestamp for alternative header
        "current_timestamp": current_weather.get("current_timestamp"),
        # Air quality data
        "air_quality": air_quality,
        # Moon phase (placeholder - you can add moon calculation later)
        "moon_icon_name": "moon-waning-crescent-5",
        # Zodiac sign
        "zodiac_sign": None,  # Will be set below if timestamp available
    }

    log(f"DEBUG: Adding air_quality to display_vars: {air_quality}")

    # Add zodiac sign if we have a timestamp
    if api_timestamp:
        from astro_utils import get_zodiac_sign_from_timestamp

        display_vars["zodiac_sign"] = get_zodiac_sign_from_timestamp(api_timestamp)
        log(f"Zodiac sign: {display_vars['zodiac_sign']}")

    return display_vars


# Platform-specific HTTP functions
try:
    # Try CircuitPython imports
    import ssl

    import adafruit_requests
    import socketpool
    import wifi

    def fetch_weather_data_circuitpy(config=None):
        """Fetch weather data on CircuitPython hardware - only forecast endpoint needed"""
        if not wifi.radio.connected:
            log("WiFi not connected")
            return None

        urls = get_weather_urls(config)
        if not urls:
            log("Weather API configuration incomplete")
            return None

        pool = socketpool.SocketPool(wifi.radio)
        context = ssl.create_default_context()
        requests = adafruit_requests.Session(pool, context)

        forecast_data = None

        try:
            # Fetch forecast data (includes current weather in first item)
            log("Fetching forecast data...")
            forecast_response = requests.get(urls["forecast"])
            if forecast_response.status_code != 200:
                log(f"Forecast request failed: {forecast_response.status_code}")
                return None

            forecast_data = forecast_response.json()
            log("Forecast data received")

            # Fetch air quality data
            air_quality_data = None
            try:
                log("Fetching air quality data...")
                aqi_response = requests.get(urls["air_quality"])
                if aqi_response.status_code == 200:
                    air_quality_data = aqi_response.json()
                    log("Air quality data received")
                else:
                    log(f"Air quality request failed: {aqi_response.status_code}")
            except Exception as e:
                log(f"Error fetching air quality data: {e}")

            # Return both datasets
            return {"forecast": forecast_data, "air_quality": air_quality_data}

        except Exception as e:
            log(f"Error fetching weather data: {e}")
            return None

    # Set the active fetch function
    fetch_weather_data = fetch_weather_data_circuitpy

except ImportError:
    # Standard Python imports for web server
    try:
        import urllib.parse
        import urllib.request

        def fetch_weather_data_python(config=None):
            """Fetch weather data using standard Python urllib - forecast and air quality endpoints"""
            if not urls:
                urls = get_weather_urls(config)
            if not urls:
                log("Weather API configuration incomplete")
                return None

            try:
                # Fetch forecast data (includes current weather in first item)
                log("Fetching forecast data...")
                with urllib.request.urlopen(urls["forecast"]) as forecast_response:
                    if forecast_response.getcode() != 200:
                        log(f"Forecast request failed: {forecast_response.getcode()}")
                        return None
                    forecast_data = json.loads(forecast_response.read().decode())
                    log("Forecast data received")

                # Fetch air quality data
                air_quality_data = None
                try:
                    log("Fetching air quality data...")
                    with urllib.request.urlopen(urls["air_quality"]) as aqi_response:
                        if aqi_response.getcode() == 200:
                            air_quality_data = json.loads(aqi_response.read().decode())
                            log("Air quality data received")
                        else:
                            log(f"Air quality request failed: {aqi_response.getcode()}")
                except Exception as e:
                    log(f"Error fetching air quality data: {e}")

                # Return both datasets
                return {"forecast": forecast_data, "air_quality": air_quality_data}

            except Exception as e:
                log(f"Error fetching weather data: {e}")
                return None

        # Set the active fetch function
        fetch_weather_data = fetch_weather_data_python

    except ImportError:
        # o noz! #TODO: something meaningful?
        log("onoz! weather_api unable to import http library!")
        fetch_weather_data = None
