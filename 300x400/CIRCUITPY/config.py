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
WEATHER_PROVIDER = "open_meteo"  # "openweathermap" or "open_meteo"

# WiFi Configuration
WIFI_SSID = None  # WiFi network name (ssid)
WIFI_PASSWORD = None  # WiFi password

# WiFi Advanced Configuration
# Set WIFI_CHANNEL to your router's channel (1–13) to skip a full scan and connect faster.
# Leave as 0 to auto-scan all channels (default, but slower).
WIFI_CHANNEL = 0

# Seconds to wait for WiFi connection. Increase (e.g. 30) if your router's DHCP server
# is slow or appears to be exhausting its lease pool.
WIFI_CONNECT_TIMEOUT = 20

# Static IP Configuration (leave all as None to use DHCP)
# Using a static IP bypasses DHCP negotiation entirely, which avoids DHCP lease-exhaustion
# issues and speeds up the connection step noticeably.
# Example:
#   WIFI_STATIC_IP      = "192.168.1.100"
#   WIFI_STATIC_NETMASK = "255.255.255.0"
#   WIFI_STATIC_GATEWAY = "192.168.1.1"
#   WIFI_STATIC_DNS     = "8.8.8.8"
WIFI_STATIC_IP      = None  # e.g. "192.168.1.100"
WIFI_STATIC_NETMASK = None  # e.g. "255.255.255.0"
WIFI_STATIC_GATEWAY = None  # e.g. "192.168.1.1"
WIFI_STATIC_DNS     = None  # e.g. "8.8.8.8"  (or your router's IP)

# openweathermap.org API Configuration
OPENWEATHER_API_KEY = None  # API key string
LATITUDE = None  # latitude number
LONGITUDE = None  # longitude number

# Weatherbit.io API Configuration (for severe weather alerts)
WEATHERBIT_API_KEY = None  # API key string for weatherbit.io alerts

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

# Logging Configuration
# "ERROR" = only show errors (no print, no SD writes for regular logs)
# "INFO" = show all logs (print + write to SD for everything)
LOG_LEVEL = "INFO"  # "ERROR" or "INFO"

# Weather Cache Configuration
# When WiFi or the weather API is unavailable, pinkweather can display the last
# successfully fetched weather data instead of showing the sad-cloud error screen.
# WEATHER_CACHE_MAX_CYCLES is the maximum number of consecutive failed hourly update
# cycles before cached data is considered too stale to show (each cycle ≈ 1 hour).
# Set to 0 to disable the cache fallback entirely.
WEATHER_CACHE_MAX_CYCLES = 6  # show cached data for up to ~6 hours of failures
