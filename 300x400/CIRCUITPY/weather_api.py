"""
Shared Weather API module for PinkWeather
Works on both CircuitPython hardware and standard Python web server
"""

import json
import time

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
            'country': city_data['country']
        }

        # Add current timestamp from API for accurate date
        parsed['current_timestamp'] = current_item['dt']

        # Add sunrise/sunset from city data
        if 'sunrise' in city_data and 'sunset' in city_data:
            sunrise_ts = city_data['sunrise']
            sunset_ts = city_data['sunset']

            # Format timestamps to readable times
            parsed['sunrise_time'] = format_time_simple(sunrise_ts, timezone_offset_hours)
            parsed['sunset_time'] = format_time_simple(sunset_ts, timezone_offset_hours)
        else:
            parsed['sunrise_time'] = '7:30a'
            parsed['sunset_time'] = '4:28p'

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

def create_enhanced_forecast_data(forecast_data, timezone_offset_hours=None):
    """Create enhanced forecast with current weather as 'NOW' plus sunrise/sunset events from single API"""
    if timezone_offset_hours is None:
        timezone_offset_hours = -5  # Default EST offset

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

    # Create "NOW" cell
    now_item = {
        'dt': current_timestamp - 86400,  # Make NOW always sort first (24 hours earlier)
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

            # Convert UTC times to local times for storage and display
            local_sunrise_ts = sunrise_ts + (timezone_offset_hours * 3600)
            local_sunset_ts = sunset_ts + (timezone_offset_hours * 3600)

            # Include sunrise/sunset if they're within past 6 hours or future 24 hours
            past_window = 6 * 3600  # 6 hours ago
            future_window = 24 * 3600  # 24 hours from now

            print(f"Local sunrise: {local_sunrise_ts}, local sunset: {local_sunset_ts}")

            # Store all special event times for filtering forecast items
            special_event_times = []

            # Compare UTC times - include if within past 6 hours or future 24 hours
            if current_timestamp - past_window <= sunrise_ts <= current_timestamp + future_window:
                sunrise_item = {
                    'dt': local_sunrise_ts,  # Store as local time for correct display
                    'temp': current_weather['current_temp'],
                    'feels_like': current_weather['feels_like'],
                    'icon': 'sunrise',
                    'description': 'Sunrise',
                    'is_now': False,
                    'is_special': True,
                    'special_type': 'sunrise'
                }
                enhanced_items.append(sunrise_item)
                special_event_times.append(local_sunrise_ts)
                print(f"Added sunrise at local time {local_sunrise_ts}")

            if current_timestamp - past_window <= sunset_ts <= current_timestamp + future_window:
                sunset_item = {
                    'dt': local_sunset_ts,  # Store as local time for correct display
                    'temp': current_weather['current_temp'],
                    'feels_like': current_weather['feels_like'],
                    'icon': 'sunset',
                    'description': 'Sunset',
                    'is_now': False,
                    'is_special': True,
                    'special_type': 'sunset'
                }
                enhanced_items.append(sunset_item)
                special_event_times.append(local_sunset_ts)
                print(f"Added sunset at local time {local_sunset_ts}")

    # Add regular forecast items (filter based on special events and current time)
    forecast_items = parse_forecast_data(forecast_data)
    if forecast_items:
        print(f"Processing {len(forecast_items)} forecast items")
        for item in forecast_items:
            # item['dt'] is already UTC from API, compare directly with UTC current time
            print(f"Forecast item: UTC {item['dt']}")

            # Skip if forecast time is in the past (compare UTC times directly)
            if item['dt'] <= current_timestamp:
                print(f"  Skipping: forecast time {item['dt']} is in past, current UTC time {current_timestamp}")
                continue

            # Convert to local time for special event comparison only
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

    # Sort all items by timestamp to create natural timeline
    enhanced_items.sort(key=lambda x: x['dt'])

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
        print("Using fallback current weather data")
        current_weather = get_fallback_current_weather()

    # Create enhanced forecast with NOW + sunrise/sunset from single API
    if forecast_data:
        forecast_items = create_enhanced_forecast_data(forecast_data, timezone_offset_hours)
    else:
        print("Using fallback forecast data")
        forecast_items = get_fallback_forecast()

    # Get current date info from weather API timestamp for accuracy
    if current_weather.get('current_timestamp'):
        api_timestamp = current_weather['current_timestamp']
        if timezone_offset_hours is None:
            timezone_offset_hours = -5
        local_timestamp = api_timestamp + (timezone_offset_hours * 3600)

        # Convert timestamp to date components manually without gmtime
        days_since_epoch = local_timestamp // 86400
        # January 1, 1970 was a Thursday (day 4 in 0-6 scale where Monday=0)
        day_of_week = (days_since_epoch + 4) % 7  # Thursday = 4

        # Approximate year calculation
        year = 1970 + (days_since_epoch // 365)
        days_in_year = days_since_epoch % 365

        # Simple month/day calculation (approximation good enough for display)
        if days_in_year < 31:
            month = 1
            day = days_in_year + 1
        elif days_in_year < 59:
            month = 2
            day = days_in_year - 30
        elif days_in_year < 90:
            month = 3
            day = days_in_year - 58
        elif days_in_year < 120:
            month = 4
            day = days_in_year - 89
        elif days_in_year < 151:
            month = 5
            day = days_in_year - 119
        elif days_in_year < 181:
            month = 6
            day = days_in_year - 150
        elif days_in_year < 212:
            month = 7
            day = days_in_year - 180
        elif days_in_year < 243:
            month = 8
            day = days_in_year - 211
        elif days_in_year < 273:
            month = 9
            day = days_in_year - 242
        elif days_in_year < 304:
            month = 10
            day = days_in_year - 272
        elif days_in_year < 334:
            month = 11
            day = days_in_year - 303
        else:
            month = 12
            day = days_in_year - 333
    else:
        # Fallback values
        day_of_week = 5  # Saturday
        day = 14
        month = 12

    day_names = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN']
    month_names = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN',
                   'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']

    day_name = day_names[day_of_week]
    day_num = day
    month_name = month_names[month - 1]

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

        # Forecast data
        'forecast_data': forecast_items,

        # Current timestamp for alternative header
        'current_timestamp': current_weather.get('current_timestamp', int(time.time())),

        # Moon phase (placeholder - you can add moon calculation later)
        'moon_icon_name': 'moon-waning-crescent-5.bmp'
    }

    return display_vars

def format_time_simple(timestamp, timezone_offset_hours=None):
    """Format Unix timestamp to simple time format (7:30a) with timezone offset"""
    try:
        if timezone_offset_hours is None:
            timezone_offset_hours = -5  # Default EST offset

        # Apply timezone offset to UTC timestamp
        local_timestamp = timestamp + (timezone_offset_hours * 3600)

        # Convert timestamp to time components manually
        hours_since_epoch = local_timestamp // 3600
        hour = hours_since_epoch % 24
        minute = (local_timestamp % 3600) // 60

        # Convert to 12-hour format
        if hour == 0:
            hour_12 = 12
            ampm = 'a'
        elif hour < 12:
            hour_12 = hour
            ampm = 'a'
        elif hour == 12:
            hour_12 = 12
            ampm = 'p'
        else:
            hour_12 = hour - 12
            ampm = 'p'

        return f"{hour_12}:{minute:02d}{ampm}"
    except:
        return "12:00p"

def get_fallback_current_weather():
    """Fallback current weather data for testing"""
    return {
        'current_temp': -1,
        'feels_like': -7,
        'high_temp': -4,
        'low_temp': -10,
        'weather_desc': 'Cloudy. 40 percent chance of flurries this evening. Periods of snow beginning near midnight. Amount 2 to 4 cm. Wind up to 15 km/h. Low minus 5. Wind chill near -9.',
        'weather_icon': '09d',
        'sunrise_time': '7:30a',
        'sunset_time': '4:28p',
        'current_timestamp': int(time.time())  # Use current time for consistency
    }

def get_fallback_forecast():
    """Fallback forecast data for testing with enhanced structure"""
    # Use current time for consistent testing with real API behavior
    import time
    current_timestamp = int(time.time())
    test_icons = ['01d', '202d', '02d', '521d', '03n', '701d', '04d', '09n']

    forecast_items = []

    # First item is always "NOW" - use earlier timestamp to ensure it sorts first
    forecast_items.append({
        'dt': current_timestamp - 86400,  # 24 hours earlier to ensure first
        'temp': -1,
        'feels_like': -3,
        'icon': '01d',
        'description': 'Current conditions',
        'is_now': True,
        'is_special': False
    })

    # Add future forecast items (starting 3 hours from now)
    for i in range(1, 6):  # 5 forecast items
        forecast_items.append({
            'dt': current_timestamp + (i * 3600 * 3),  # 3-hour intervals
            'temp': -1 - i,  # Decreasing temps
            'feels_like': -3 - i,
            'icon': test_icons[i],
            'description': 'Test weather',
            'is_now': False,
            'is_special': False
        })

    # Add sunrise event (6 hours from now)
    forecast_items.append({
        'dt': current_timestamp + (6 * 3600),
        'temp': -2,
        'feels_like': -4,
        'icon': 'sunrise',
        'description': 'Sunrise',
        'is_now': False,
        'is_special': True,
        'special_type': 'sunrise'
    })

    # Add sunset event (18 hours from now)
    forecast_items.append({
        'dt': current_timestamp + (18 * 3600),
        'temp': -8,
        'feels_like': -10,
        'icon': 'sunset',
        'description': 'Sunset',
        'is_now': False,
        'is_special': True,
        'special_type': 'sunset'
    })

    # Sort by timestamp (NOW will be first due to earlier timestamp)
    forecast_items.sort(key=lambda x: x['dt'])
    return forecast_items[:8]

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
