"""
Shared Weather API module for PinkWeather
Works on both CircuitPython hardware and standard Python web server
"""

import json
import time
from date_utils import format_timestamp_to_date, format_timestamp_to_time

# No default configuration - must be provided by calling code

def manual_capitalize(text):
    """Manually capitalize first letter for CircuitPython compatibility"""
    if not text:
        return text
    return text[0].upper() + text[1:] if len(text) > 1 else text.upper()

def get_weather_urls(config=None):
    """Generate OpenWeather API URLs with given configuration - only forecast endpoint needed"""
    if config is None:
        return None

    # Check if required config values are present
    if not config.get('api_key') or not config.get('latitude') or not config.get('longitude'):
        return None

    base_params = f"lon={config['longitude']}&lat={config['latitude']}&appid={config['api_key']}&units={config['units']}"

    return {
        'forecast': f"https://api.openweathermap.org/data/2.5/forecast?{base_params}"
    }

def parse_current_weather_from_forecast(forecast_data, timezone_offset_hours=None):
    """Parse current weather from forecast API response (first item + city data)"""
    if not forecast_data or 'list' not in forecast_data or 'city' not in forecast_data:
        return None

    try:
        # Use first forecast item as current weather
        current_item = forecast_data['list'][0]
        city_data = forecast_data['city']

        parsed = {
            'current_temp': round(current_item['main']['temp']),
            'feels_like': round(current_item['main']['feels_like']),
            'high_temp': round(current_item['main']['temp_max']),
            'low_temp': round(current_item['main']['temp_min']),
            'weather_desc': manual_capitalize(current_item['weather'][0]['description']),
            'weather_icon': current_item['weather'][0]['icon'],
            'city_name': city_data['name'],
            'country': city_data['country'],
            'humidity': current_item['main'].get('humidity', 0),
            'wind_speed': current_item.get('wind', {}).get('speed', 0),
            'wind_gust': current_item.get('wind', {}).get('gust', 0)
        }

        # Add current timestamp from API for accurate date
        parsed['current_timestamp'] = current_item['dt']

        # Add sunrise/sunset from city data
        if 'sunrise' in city_data and 'sunset' in city_data:
            sunrise_ts = city_data['sunrise']
            sunset_ts = city_data['sunset']

            # Debug logging for sunrise/sunset timestamps
            print(f"DEBUG: Raw sunrise timestamp from API: {sunrise_ts}")
            print(f"DEBUG: Raw sunset timestamp from API: {sunset_ts}")
            print(f"DEBUG: Current timestamp from API: {current_item['dt']}")

            # Test both UTC and local time interpretations
            sunrise_utc_formatted = format_timestamp_to_time(sunrise_ts, timezone_offset_hours, format_12h=True)
            sunset_utc_formatted = format_timestamp_to_time(sunset_ts, timezone_offset_hours, format_12h=True)
            sunrise_local_formatted = format_timestamp_to_time(sunrise_ts, 0, format_12h=True)
            sunset_local_formatted = format_timestamp_to_time(sunset_ts, 0, format_12h=True)

            print(f"DEBUG: Sunrise as UTC+offset: {sunrise_utc_formatted}")
            print(f"DEBUG: Sunset as UTC+offset: {sunset_utc_formatted}")
            print(f"DEBUG: Sunrise as local time: {sunrise_local_formatted}")
            print(f"DEBUG: Sunset as local time: {sunset_local_formatted}")

            # Store both timestamps and formatted times (temporarily use local time interpretation)
            parsed['sunrise_timestamp'] = sunrise_ts
            parsed['sunset_timestamp'] = sunset_ts
            parsed['sunrise_time'] = format_timestamp_to_time(sunrise_ts, 0, format_12h=True)  # Try as local time
            parsed['sunset_time'] = format_timestamp_to_time(sunset_ts, 0, format_12h=True)   # Try as local time
        else:
            parsed['sunrise_timestamp'] = None
            parsed['sunset_timestamp'] = None
            parsed['sunrise_time'] = None
            parsed['sunset_time'] = None

        return parsed

    except (KeyError, TypeError, ValueError) as e:
        print(f"Error parsing current weather from forecast: {e}")
        return None

def parse_forecast_data(forecast_data):
    """Parse forecast API response into display variables (skip first item since it's used as current)"""
    if not forecast_data or 'list' not in forecast_data:
        return None

    try:
        forecast_items = []

        # Skip first item (used as current weather), take next 8 items
        for item in forecast_data['list'][1:9]:
            parsed_item = {
                'dt': item['dt'],
                'temp': round(item['main']['temp']),
                'feels_like': round(item['main']['feels_like']),
                'icon': item['weather'][0]['icon'],
                'description': item['weather'][0]['description']
            }
            forecast_items.append(parsed_item)

        return forecast_items

    except (KeyError, TypeError, ValueError) as e:
        print(f"Error parsing forecast data: {e}")
        return None

def interpolate_temperature(target_timestamp, forecast_items):
    """Calculate interpolated temperature for a target timestamp based on surrounding forecast data"""
    if not forecast_items or len(forecast_items) < 2:
        return None

    # Find the two forecast items that bracket the target timestamp
    before_item = None
    after_item = None

    for item in forecast_items:
        if item['dt'] <= target_timestamp:
            before_item = item
        elif item['dt'] > target_timestamp and after_item is None:
            after_item = item
            break

    # If we can't bracket the time, use the closest available
    if before_item is None and after_item is not None:
        return after_item['temp']
    elif after_item is None and before_item is not None:
        return before_item['temp']
    elif before_item is None and after_item is None:
        return forecast_items[0]['temp']  # Fallback to first item

    # Linear interpolation between before and after temperatures
    time_diff = after_item['dt'] - before_item['dt']
    if time_diff == 0:
        return before_item['temp']

    temp_diff = after_item['temp'] - before_item['temp']
    target_offset = target_timestamp - before_item['dt']
    interpolated_temp = before_item['temp'] + (temp_diff * target_offset / time_diff)

    return round(interpolated_temp)

def create_enhanced_forecast_data(forecast_data, timezone_offset_hours=None):
    """Create enhanced forecast with current weather as 'NOW' plus sunrise/sunset events from single API"""
    if timezone_offset_hours is None:
        raise ValueError("timezone_offset_hours must be provided")

    enhanced_items = []

    # Parse current weather from forecast data
    current_weather = parse_current_weather_from_forecast(forecast_data, timezone_offset_hours)
    if not current_weather:
        return []

    current_timestamp = current_weather['current_timestamp']
    print(f"Current API timestamp: {current_timestamp}")

    # Convert current time to local for comparison
    local_current_timestamp = current_timestamp + (timezone_offset_hours * 3600)
    print(f"Local current timestamp: {local_current_timestamp}")

    # Get forecast items for temperature interpolation
    forecast_items = parse_forecast_data(forecast_data)

    # Create "NOW" cell
    now_item = {
        'dt': current_timestamp,  # Use actual current timestamp
        'temp': current_weather['current_temp'],
        'feels_like': current_weather['feels_like'],
        'icon': current_weather['weather_icon'],
        'description': 'Current conditions',
        'is_now': True
    }
    enhanced_items.append(now_item)

    # Add sunrise/sunset events from city data
    if 'city' in forecast_data:
        city_data = forecast_data['city']
        if 'sunrise' in city_data and 'sunset' in city_data:
            sunrise_ts = city_data['sunrise']
            sunset_ts = city_data['sunset']

            print(f"API sunrise UTC: {sunrise_ts}, sunset UTC: {sunset_ts}")
            print(f"Current API time UTC: {current_timestamp}")

            # API appears to return sunrise/sunset in local time, not UTC
            # So we don't need to apply timezone conversion
            local_sunrise_ts = sunrise_ts
            local_sunset_ts = sunset_ts

            # Calculate tomorrow's sunrise/sunset (add 24 hours to local times)
            tomorrow_sunrise_ts = sunrise_ts + 86400  # Local time + 24 hours
            tomorrow_sunset_ts = sunset_ts + 86400    # Local time + 24 hours
            local_tomorrow_sunrise_ts = tomorrow_sunrise_ts
            local_tomorrow_sunset_ts = tomorrow_sunset_ts

            # Include sunrise/sunset if they're within past 6 hours or future 24 hours
            past_window = 6 * 3600  # 6 hours ago
            future_window = 24 * 3600  # 24 hours from now

            print(f"Local sunrise: {local_sunrise_ts}, local sunset: {local_sunset_ts}")
            print(f"Local tomorrow sunrise: {local_tomorrow_sunrise_ts}, local tomorrow sunset: {local_tomorrow_sunset_ts}")

            # Store all special event times for filtering forecast items
            special_event_times = []

            # Today's sunrise/sunset - convert current time to local for comparison
            local_current_timestamp = current_timestamp + (timezone_offset_hours * 3600)
            if local_current_timestamp - past_window <= sunrise_ts <= local_current_timestamp + future_window:
                # Calculate interpolated temperature for sunrise time
                # Convert sunrise time to UTC for interpolation (forecast items are in UTC)
                sunrise_utc = sunrise_ts - (timezone_offset_hours * 3600)
                sunrise_temp = interpolate_temperature(sunrise_utc, forecast_items)
                if sunrise_temp is None:
                    sunrise_temp = current_weather['current_temp']

                sunrise_item = {
                    'dt': sunrise_ts,  # Store local time (API gives local time)
                    'display_time': local_sunrise_ts,  # Same as dt since already local
                    'temp': sunrise_temp,
                    'feels_like': current_weather['feels_like'],  # Could also interpolate this
                    'icon': 'sunrise',
                    'description': 'Sunrise',
                    'is_now': False,
                    'is_special': True,
                    'special_type': 'sunrise'
                }
                enhanced_items.append(sunrise_item)
                special_event_times.append(local_sunrise_ts)
                print(f"Added sunrise at local time {local_sunrise_ts} with temp {sunrise_temp}°C")

            if local_current_timestamp - past_window <= sunset_ts <= local_current_timestamp + future_window:
                # Calculate interpolated temperature for sunset time
                # Convert sunset time to UTC for interpolation (forecast items are in UTC)
                sunset_utc = sunset_ts - (timezone_offset_hours * 3600)
                sunset_temp = interpolate_temperature(sunset_utc, forecast_items)
                if sunset_temp is None:
                    sunset_temp = current_weather['current_temp']

                sunset_item = {
                    'dt': sunset_ts,  # Store local time (API gives local time)
                    'display_time': local_sunset_ts,  # Same as dt since already local
                    'temp': sunset_temp,
                    'feels_like': current_weather['feels_like'],  # Could also interpolate this
                    'icon': 'sunset',
                    'description': 'Sunset',
                    'is_now': False,
                    'is_special': True,
                    'special_type': 'sunset'
                }
                enhanced_items.append(sunset_item)
                special_event_times.append(local_sunset_ts)
                print(f"Added sunset at local time {local_sunset_ts} with temp {sunset_temp}°C")

            # Tomorrow's sunrise/sunset - compare with local current time
            if local_current_timestamp - past_window <= tomorrow_sunrise_ts <= local_current_timestamp + future_window:
                # Calculate interpolated temperature for tomorrow's sunrise time
                # Convert tomorrow's sunrise time to UTC for interpolation (forecast items are in UTC)
                tomorrow_sunrise_utc = tomorrow_sunrise_ts - (timezone_offset_hours * 3600)
                tomorrow_sunrise_temp = interpolate_temperature(tomorrow_sunrise_utc, forecast_items)
                if tomorrow_sunrise_temp is None:
                    tomorrow_sunrise_temp = current_weather['current_temp']

                tomorrow_sunrise_item = {
                    'dt': tomorrow_sunrise_ts,  # Store local time (API gives local time)
                    'display_time': local_tomorrow_sunrise_ts,  # Same as dt since already local
                    'temp': tomorrow_sunrise_temp,
                    'feels_like': current_weather['feels_like'],  # Could also interpolate this
                    'icon': 'sunrise',
                    'description': 'Tomorrow Sunrise',
                    'is_now': False,
                    'is_special': True,
                    'special_type': 'sunrise'
                }
                enhanced_items.append(tomorrow_sunrise_item)
                special_event_times.append(local_tomorrow_sunrise_ts)
                print(f"Added tomorrow sunrise at local time {local_tomorrow_sunrise_ts} with temp {tomorrow_sunrise_temp}°C")

            if local_current_timestamp - past_window <= tomorrow_sunset_ts <= local_current_timestamp + future_window:
                # Calculate interpolated temperature for tomorrow's sunset time
                # Convert tomorrow's sunset time to UTC for interpolation (forecast items are in UTC)
                tomorrow_sunset_utc = tomorrow_sunset_ts - (timezone_offset_hours * 3600)
                tomorrow_sunset_temp = interpolate_temperature(tomorrow_sunset_utc, forecast_items)
                if tomorrow_sunset_temp is None:
                    tomorrow_sunset_temp = current_weather['current_temp']

                tomorrow_sunset_item = {
                    'dt': tomorrow_sunset_ts,  # Store local time (API gives local time)
                    'display_time': local_tomorrow_sunset_ts,  # Same as dt since already local
                    'temp': tomorrow_sunset_temp,
                    'feels_like': current_weather['feels_like'],  # Could also interpolate this
                    'icon': 'sunset',
                    'description': 'Tomorrow Sunset',
                    'is_now': False,
                    'is_special': True,
                    'special_type': 'sunset'
                }
                enhanced_items.append(tomorrow_sunset_item)
                special_event_times.append(local_tomorrow_sunset_ts)
                print(f"Added tomorrow sunset at local time {local_tomorrow_sunset_ts} with temp {tomorrow_sunset_temp}°C")

    # Add regular forecast items (filter based on special events and current time)
    # forecast_items already loaded above for temperature interpolation
    if forecast_items:
        print(f"Processing {len(forecast_items)} forecast items")
        for item in forecast_items:
            # item['dt'] is UTC from API, convert to local for comparison with sunrise/sunset
            print(f"Forecast item: UTC {item['dt']}")

            # Skip if forecast time is in the past (compare UTC times directly)
            if item['dt'] <= current_timestamp:
                print(f"  Skipping: forecast time {item['dt']} is in past, current UTC time {current_timestamp}")
                continue

            # Convert to local time for special event comparison
            forecast_local_time = item['dt'] + (timezone_offset_hours * 3600)

            # Skip if too close to any special event (within 30 minutes)
            too_close_to_special = False
            if 'special_event_times' in locals():
                for special_time in special_event_times:
                    if abs(forecast_local_time - special_time) <= (30 * 60):
                        print(f"  Skipping: too close to special event at {special_time}")
                        too_close_to_special = True
                        break

            if not too_close_to_special:
                # Mark regular forecast items but keep UTC timestamps
                item['is_now'] = False
                item['is_special'] = False
                enhanced_items.append(item)
                print(f"  Added forecast item at UTC {item['dt']}")

    # Sort items: NOW first, then chronological order by timestamp
    def sort_key(item):
        if item.get('is_now', False):
            return (0, 0)  # NOW always first
        else:
            return (1, item['dt'])  # Everything else by timestamp

    enhanced_items.sort(key=sort_key)

    # Debug output for ordering
    print("Enhanced forecast order:")
    for i, item in enumerate(enhanced_items[:8]):
        item_type = "NOW" if item.get('is_now') else item.get('special_type', 'forecast')
        print(f"  {i+1}. {item_type} - dt:{item['dt']}")

    # Return up to 8 items for display
    return enhanced_items[:8]

def get_display_variables(forecast_data, timezone_offset_hours=None):
    """Parse forecast API response into all variables needed for display"""

    # Parse current weather from forecast data
    current_weather = parse_current_weather_from_forecast(forecast_data, timezone_offset_hours)
    if not current_weather:
        print("No current weather data available")
        return None

    # Create enhanced forecast with NOW + sunrise/sunset from single API
    if forecast_data:
        forecast_items = create_enhanced_forecast_data(forecast_data, timezone_offset_hours)
    else:
        print("No forecast data available")
        return None

    # Get current date info from weather API timestamp for accuracy
    if current_weather.get('current_timestamp'):
        api_timestamp = current_weather['current_timestamp']
        if timezone_offset_hours is None:
            raise ValueError("timezone_offset_hours must be provided")

        # Convert timestamp to date components using centralized utility
        date_info = format_timestamp_to_date(api_timestamp, timezone_offset_hours)
        day_name = date_info['day_name']
        day_num = date_info['day_num']
        month_name = date_info['month_name']
    else:
        # No timestamp available - return None values
        day_name = None
        day_num = None
        month_name = None

    # Combine everything for display
    display_vars = {
        # Date info
        'day_name': day_name,
        'day_num': day_num,
        'month_name': month_name,

        # Current weather
        'current_temp': current_weather['current_temp'],
        'feels_like': current_weather['feels_like'],
        'high_temp': current_weather['high_temp'],
        'low_temp': current_weather['low_temp'],
        'weather_desc': current_weather['weather_desc'],
        'weather_icon_name': f"{current_weather['weather_icon']}.bmp",
        'sunrise_time': current_weather['sunrise_time'],
        'sunset_time': current_weather['sunset_time'],
        'sunrise_timestamp': current_weather.get('sunrise_timestamp'),
        'sunset_timestamp': current_weather.get('sunset_timestamp'),
        'humidity': current_weather.get('humidity', 0),
        'wind_speed': current_weather.get('wind_speed', 0),
        'wind_gust': current_weather.get('wind_gust', 0),

        # Forecast data
        'forecast_data': forecast_items,

        # Current timestamp for alternative header
        'current_timestamp': current_weather.get('current_timestamp'),

        # Moon phase (placeholder - you can add moon calculation later)
        'moon_icon_name': 'moon-waning-crescent-5.bmp'
    }

    return display_vars



# Removed fallback functions - use real weather data or fail cleanly

# Platform-specific HTTP functions
try:
    # Try CircuitPython imports
    import wifi
    import socketpool
    import ssl
    import adafruit_requests

    def fetch_weather_data_circuitpy(config=None):
        """Fetch weather data on CircuitPython hardware - only forecast endpoint needed"""
        if not wifi.radio.connected:
            print("WiFi not connected")
            return None

        urls = get_weather_urls(config)
        if not urls:
            print("Weather API configuration incomplete")
            return None

        pool = socketpool.SocketPool(wifi.radio)
        context = ssl.create_default_context()
        requests = adafruit_requests.Session(pool, context)

        forecast_data = None

        try:
            # Fetch forecast only (includes current weather in first item)
            print("Fetching forecast data...")
            response = requests.get(urls['forecast'])
            if response.status_code == 200:
                forecast_data = response.json()
                print("Forecast data received")
            else:
                print(f"Forecast request failed: {response.status_code}")
            response.close()

        except Exception as e:
            print(f"Error fetching weather data: {e}")

        return forecast_data

    # Set the active fetch function
    fetch_weather_data = fetch_weather_data_circuitpy

except ImportError:
    # Standard Python imports for web server
    try:
        import urllib.request
        import urllib.parse

        def fetch_weather_data_python(config=None):
            """Fetch weather data using standard Python urllib - only forecast endpoint needed"""
            urls = get_weather_urls(config)
            if not urls:
                print("Weather API configuration incomplete")
                return None

            forecast_data = None

            try:
                # Fetch forecast only (includes current weather in first item)
                print("Fetching forecast data...")
                with urllib.request.urlopen(urls['forecast']) as response:
                    if response.getcode() == 200:
                        forecast_data = json.loads(response.read().decode())
                        print("Forecast data received")
                    else:
                        print(f"Forecast request failed: {response.getcode()}")

            except Exception as e:
                print(f"Error fetching weather data: {e}")

            return forecast_data

        # Set the active fetch function
        fetch_weather_data = fetch_weather_data_python

    except ImportError:
        # No HTTP capability, use fallback
        def fetch_weather_data_fallback(config=None):
            """Fallback when no HTTP capability available"""
            print("No HTTP capability available, using fallback data")
            return None

        fetch_weather_data = fetch_weather_data_fallback
