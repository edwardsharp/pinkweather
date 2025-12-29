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


# Pin Configuration (mocked for preview compatibility)
class MockPin:
    """Mock pin object for preview environment"""

    pass


# Mock board module for compatibility
class MockBoard:
    LED = MockPin()
    GP18 = MockPin()
    GP19 = MockPin()
    GP16 = MockPin()
    GP17 = MockPin()
    GP20 = MockPin()
    GP21 = MockPin()
    GP22 = MockPin()
    GP26 = MockPin()
    GP27 = MockPin()
    GP28 = MockPin()


# Create mock board instance
board = MockBoard()

# Pin Configurationz (using mocked pins)
LED_PIN = board.LED
SPI_SCK_PIN = board.GP18
SPI_MOSI_PIN = board.GP19
SPI_MISO_PIN = board.GP16
DISPLAY_CS_PIN = board.GP17
DISPLAY_DC_PIN = board.GP20
DISPLAY_RST_PIN = board.GP21
DISPLAY_BUSY_PIN = board.GP22
SD_CS_PIN = board.GP26
SD_SRCS_PIN = board.GP27
SENSOR_SDA_PIN = board.GP28

# Display Configuration
DISPLAY_ROTATION = 0

# Preview-specific settings
INDOOR_TEMP_HUMIDITY = "20°69%"  # Hardcoded for preview (Celsius)
