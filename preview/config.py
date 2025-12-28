"""
Preview configuration file - loads from .env file
Similar structure to hardware config but loads from environment variables
"""

import os

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Weather Provider Configuration
WEATHER_PROVIDER = "openweathermap"  # "openweathermap" or "open_meteo"

# WiFi Configuration (not used in preview)
WIFI_SSID = None
WIFI_PASSWORD = None

# openweathermap.org API Configuration - loaded from .env
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
LATITUDE = float(os.getenv("LATITUDE", 40.655786))
LONGITUDE = float(os.getenv("LONGITUDE", -73.9585369))

# Timezone Configuration - loaded from .env
TIMEZONE_OFFSET_HOURS = int(os.getenv("TIMEZONE_OFFSET_HOURS", -5))

# Display Configuration (not used in preview but kept for compatibility)
DISPLAY_ROTATION = 0

# Preview-specific settings
INDOOR_TEMP_HUMIDITY = "20° 45%"  # Hardcoded for preview (Celsius)
