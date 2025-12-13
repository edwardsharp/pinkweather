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
    """Generate OpenWeather API URLs with given configuration"""
    if config is None:
        return None

    # Check if required config values are present
    if not config.get('api_key') or not config.get('latitude') or not config.get('longitude'):
        return None

    base_params = f"lon={config['longitude']}&lat={config['latitude']}&appid={config['api_key']}&units={config['units']}"

    return {
        'current': f"https://api.openweathermap.org/data/2.5/weather?{base_params}",
        'forecast': f"https://api.openweathermap.org/data/2.5/forecast?{base_params}"
    }

def parse_current_weather(current_data, timezone_offset_hours=None):
    """Parse current weather API response into display variables"""
    if not current_data:
        return None

    try:
        parsed = {
            'current_temp': round(current_data['main']['temp']),
            'feels_like': round(current_data['main']['feels_like']),
            'high_temp': round(current_data['main']['temp_max']),
            'low_temp': round(current_data['main']['temp_min']),
            'weather_desc': manual_capitalize(current_data['weather'][0]['description']),
            'weather_icon': current_data['weather'][0]['icon'],
            'city_name': current_data['name'],
            'country': current_data['sys']['country']
        }

        # Add sunrise/sunset if available
        if 'sys' in current_data and 'sunrise' in current_data['sys']:
            sunrise_ts = current_data['sys']['sunrise']
            sunset_ts = current_data['sys']['sunset']

            # Format timestamps to readable times
            parsed['sunrise_time'] = format_time_simple(sunrise_ts, timezone_offset_hours)
            parsed['sunset_time'] = format_time_simple(sunset_ts, timezone_offset_hours)
        else:
            parsed['sunrise_time'] = '7:30a'
            parsed['sunset_time'] = '4:28p'

        return parsed

    except (KeyError, TypeError, ValueError) as e:
        print(f"Error parsing current weather: {e}")
        return None

def parse_forecast_data(forecast_data):
    """Parse forecast API response into display variables"""
    if not forecast_data or 'list' not in forecast_data:
        return None

    try:
        forecast_items = []

        # Take first 8 items (24 hours of 3-hour forecasts)
        for item in forecast_data['list'][:8]:
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

def get_display_variables(current_data, forecast_data, timezone_offset_hours=None):
    """Parse API responses into all variables needed for display"""

    # Parse current weather
    current_weather = parse_current_weather(current_data, timezone_offset_hours)
    if not current_weather:
        print("Using fallback current weather data")
        current_weather = get_fallback_current_weather()

    # Parse forecast
    forecast_items = parse_forecast_data(forecast_data)
    if not forecast_items:
        print("Using fallback forecast data")
        forecast_items = get_fallback_forecast()

    # Get current date info
    current_time = time.localtime()
    day_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                   'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

    day_name = day_names[current_time[6]]  # tm_wday
    day_num = current_time[2]  # tm_mday
    month_name = month_names[current_time[1] - 1]  # tm_mon

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

        # Use gmtime if available (standard Python), fallback to localtime (CircuitPython)
        try:
            time_struct = time.gmtime(local_timestamp)
        except AttributeError:
            time_struct = time.localtime(local_timestamp)

        hour = time_struct[3]  # tm_hour
        minute = time_struct[4]  # tm_min

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
        'sunset_time': '4:28p'
    }

def get_fallback_forecast():
    """Fallback forecast data for testing"""
    current_timestamp = int(time.time())
    test_icons = ['01d', '202d', '02d', '521d', '03n', '701d', '04d', '09n']

    forecast_items = []
    for i in range(8):
        forecast_items.append({
            'dt': current_timestamp + (i * 3600 * 3),  # 3-hour intervals
            'temp': -1 - i,  # Decreasing temps
            'feels_like': -3 - i,
            'icon': test_icons[i],
            'description': 'Test weather'
        })

    return forecast_items

# Platform-specific HTTP functions
try:
    # Try CircuitPython imports
    import wifi
    import socketpool
    import ssl
    import adafruit_requests

    def fetch_weather_data_circuitpy(config=None):
        """Fetch weather data on CircuitPython hardware"""
        if not wifi.radio.connected:
            print("WiFi not connected")
            return None, None

        urls = get_weather_urls(config)
        if not urls:
            print("Weather API configuration incomplete")
            return None, None

        pool = socketpool.SocketPool(wifi.radio)
        context = ssl.create_default_context()
        requests = adafruit_requests.Session(pool, context)

        current_weather = None
        forecast_data = None

        try:
            # Fetch current weather
            print("Fetching current weather...")
            response = requests.get(urls['current'])
            if response.status_code == 200:
                current_weather = response.json()
                print("Current weather data received")
            else:
                print(f"Current weather request failed: {response.status_code}")
            response.close()

            # Fetch forecast
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

        return current_weather, forecast_data

    # Set the active fetch function
    fetch_weather_data = fetch_weather_data_circuitpy

except ImportError:
    # Standard Python imports for web server
    try:
        import urllib.request
        import urllib.parse

        def fetch_weather_data_python(config=None):
            """Fetch weather data using standard Python urllib"""
            urls = get_weather_urls(config)
            if not urls:
                print("Weather API configuration incomplete")
                return None, None

            current_weather = None
            forecast_data = None

            try:
                # Fetch current weather
                print("Fetching current weather...")
                with urllib.request.urlopen(urls['current']) as response:
                    if response.getcode() == 200:
                        current_weather = json.loads(response.read().decode())
                        print("Current weather data received")
                    else:
                        print(f"Current weather request failed: {response.getcode()}")

                # Fetch forecast
                print("Fetching forecast data...")
                with urllib.request.urlopen(urls['forecast']) as response:
                    if response.getcode() == 200:
                        forecast_data = json.loads(response.read().decode())
                        print("Forecast data received")
                    else:
                        print(f"Forecast request failed: {response.getcode()}")

            except Exception as e:
                print(f"Error fetching weather data: {e}")

            return current_weather, forecast_data

        # Set the active fetch function
        fetch_weather_data = fetch_weather_data_python

    except ImportError:
        # No HTTP capability, use fallback
        def fetch_weather_data_fallback(config=None):
            """Fallback when no HTTP capability available"""
            print("No HTTP capability available, using fallback data")
            return None, None

        fetch_weather_data = fetch_weather_data_fallback
