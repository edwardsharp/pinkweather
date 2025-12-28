"""
configuration file for pinkweather

update with yr own values.
"""

# example configuration:
# WIFI_SSID = "MyWiFiNetwork"
# WIFI_PASSWORD = "MyWiFiPassword"
# OPENWEATHER_API_KEY = "abc123"
# LATITUDE = 0.0000000
# LONGITUDE = -0.0000000
# TIMEZONE_OFFSET_HOURS = -5
# DISPLAY_ROTATION = 0
# LED_PIN = board.LED
# SPI_SCK_PIN = board.GP18
# SPI_MOSI_PIN = board.GP19
# SPI_MISO_PIN = board.GP16
# DISPLAY_CS_PIN = board.GP17
# DISPLAY_DC_PIN = board.GP20
# DISPLAY_RST_PIN = None  # board.GP21 if wired
# DISPLAY_BUSY_PIN = None  # board.GP22 if wired
# SD_SRCS_PIN = board.GP22  # SRAM disable pin
# SD_CS_PIN = board.GP21  # SD card chip select
# I2C_SCL_PIN = board.GP27
# I2C_SDA_PIN = board.GP26

import board

# Weather Provider Configuration
WEATHER_PROVIDER = "openweathermap"  # "openweathermap" or "open_meteo"

# WiFi Configuration
WIFI_SSID = None  # WiFi network name (ssid)
WIFI_PASSWORD = None  # WiFi password

# openweathermap.org API Configuration
OPENWEATHER_API_KEY = None  # API key string
LATITUDE = None  # latitude number
LONGITUDE = None  # longitude number

# Timezone Configuration
TIMEZONE_OFFSET_HOURS = (
    -5
)  # number of hours offset from UTC (e.g., -5 for EST, -4 for EDT)

# rotate the display 0 so the bottom is the side with the 20pin cable
DISPLAY_ROTATION = 0

# Pin Configurationz
# LED Pin
LED_PIN = board.LED

# SPI Pins
SPI_SCK_PIN = board.GP18
SPI_MOSI_PIN = board.GP19
SPI_MISO_PIN = board.GP16

# Display Pins
DISPLAY_CS_PIN = board.GP17
DISPLAY_DC_PIN = board.GP20
DISPLAY_RST_PIN = None  # board.GP21 if wired
DISPLAY_BUSY_PIN = None  # board.GP22 if wired

# SD Card Pins
SD_SRCS_PIN = board.GP22  # SRAM disable pin
SD_CS_PIN = board.GP21  # SD card chip select

# I2C Pins (Temperature Sensor)
I2C_SCL_PIN = board.GP27
I2C_SDA_PIN = board.GP26
