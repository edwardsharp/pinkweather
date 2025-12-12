"""
PinkWeather CircuitPython Code for 400x300 E-ink Display
Text display with markup support and hard word wrapping
"""

import time
import board
import busio
import digitalio
import displayio
import fourwire
import adafruit_ssd1683
import adafruit_sdcard
import storage
import gc
from digitalio import DigitalInOut

# shared display functions
from display import get_text_capacity, create_weather_layout, WEATHER_ICON_X, WEATHER_ICON_Y, MOON_ICON_X, MOON_ICON_Y

# Release any previously used displays
displayio.release_displays()

# Pin assignments for Pico 2W
# SPI pins: SCK=GP18, MOSI=GP19, MISO=GP16
# CS pin: GP17, DC pin: GP20
spi = busio.SPI(clock=board.GP18, MOSI=board.GP19, MISO=board.GP16)

# Pin assignments for FourWire (use Pin objects directly)
cs_pin = board.GP17
dc_pin = board.GP20  # You'll need to wire this DC pin!

# Reset and Busy pins (optional but recommended)
rst_pin = None  # board.GP21
busy_pin = None  # digitalio.DigitalInOut(board.GP22) if you wire it

# Create the display bus
display_bus = fourwire.FourWire(
    spi,
    command=dc_pin,
    chip_select=cs_pin,
    reset=rst_pin,
    baudrate=1000000
)

# Wait a moment for the bus to initialize
time.sleep(1)

# Create the display
display = adafruit_ssd1683.SSD1683(
    display_bus,
    width=400,
    height=300,
    highlight_color=0x000000,  # Black instead of red to prevent artifacts
    busy_pin=busy_pin
)

# Rotate display 180 degrees
display.rotation = 180

# Initialize SD card
sd_available = False
try:
    # Disable SRAM to avoid SPI conflicts (SRCS -> GP22)
    srcs_pin = DigitalInOut(board.GP22)
    srcs_pin.direction = digitalio.Direction.OUTPUT
    srcs_pin.value = True  # High = SRAM disabled

    # Initialize SD card
    cs_sd = DigitalInOut(board.GP21)
    sdcard = adafruit_sdcard.SDCard(spi, cs_sd, baudrate=250000)
    vfs = storage.VfsFat(sdcard)
    storage.mount(vfs, "/sd")
    sd_available = True
    print("SD card ready")

except Exception as e:
    print(f"SD card failed: {e}")
    print("Continuing without SD card...")
    sd_available = False

# Display dimensions and colors
DISPLAY_WIDTH = 400
DISPLAY_HEIGHT = 300
BLACK = 0x000000
WHITE = 0xFFFFFF
RED = 0xFF0000

def calculate_moon_phase(unix_timestamp=None, year=None, month=None, day=None):
    """Calculate moon phase for a given date (simplified version for CircuitPython)"""
    # Use unix timestamp if provided, otherwise use current date
    if unix_timestamp is not None:
        time_struct = time.localtime(unix_timestamp)
        year = time_struct.tm_year
        month = time_struct.tm_mon
        day = time_struct.tm_mday
    elif year is None or month is None or day is None:
        current_time = time.localtime()
        year = year or current_time.tm_year
        month = month or current_time.tm_mon
        day = day or current_time.tm_mday

    # Calculate Julian day number
    if month <= 2:
        year -= 1
        month += 12

    a = year // 100
    b = 2 - a + (a // 4)

    julian_day = int(365.25 * (year + 4716)) + int(30.6001 * (month + 1)) + day + b - 1524.5

    # Calculate days since known new moon (January 6, 2000)
    days_since_new_moon = julian_day - 2451550.1

    # Calculate number of lunar cycles (29.53058867 days per cycle)
    lunar_cycle_length = 29.53058867
    cycles = days_since_new_moon / lunar_cycle_length

    # Get fractional part (phase within current cycle)
    phase = cycles - int(cycles)

    # Ensure phase is between 0 and 1
    if phase < 0:
        phase += 1

    return phase

def phase_to_icon_name(phase, use_detailed=True):
    """Convert numeric phase to BMP icon filename"""
    if phase < 0.03 or phase > 0.97:
        return "moon-new"
    elif phase < 0.22:
        # Waxing crescent (1-5, gets brighter)
        crescent_num = int((phase - 0.03) / 0.038) + 1
        crescent_num = max(1, min(5, crescent_num))
        return f"moon-waxing-crescent-{crescent_num}"
    elif phase < 0.28:
        return "moon-first-quarter"
    elif phase < 0.47:
        # Waxing gibbous (1-6, gets brighter)
        gibbous_num = int((phase - 0.28) / 0.032) + 1
        gibbous_num = max(1, min(6, gibbous_num))
        return f"moon-waxing-gibbous-{gibbous_num}"
    elif phase < 0.53:
        return "moon-full"
    elif phase < 0.72:
        # Waning gibbous (6-1, gets dimmer)
        gibbous_num = 6 - int((phase - 0.53) / 0.032)
        gibbous_num = max(1, min(6, gibbous_num))
        return f"moon-waning-gibbous-{gibbous_num}"
    elif phase < 0.78:
        return "moon-third-quarter"
    else:
        # Waning crescent (5-1, gets dimmer)
        crescent_num = 5 - int((phase - 0.78) / 0.038)
        crescent_num = max(1, min(5, crescent_num))
        return f"moon-waning-crescent-{crescent_num}"

def format_date(unix_timestamp=None):
    """Format date as 'Thu 11 Dec' (day of week, day, month)"""
    if unix_timestamp is None:
        time_struct = time.localtime()
    else:
        time_struct = time.localtime(unix_timestamp)

    days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
              'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

    day_name = days[time_struct.tm_wday]
    day_num =  time_struct.tm_mday
    month_name = months[time_struct.tm_mon - 1]

    return day_name, day_num, month_name

def format_time(unix_timestamp=None):
    """Format time as '9:36p' (12-hour format with am/p suffix)"""
    if unix_timestamp is None:
        time_struct = time.localtime()
    else:
        time_struct = time.localtime(unix_timestamp)

    hour = time_struct.tm_hour
    minute = time_struct.tm_min

    # Convert to 12-hour format
    if hour == 0:
        hour_12 = 12
        suffix = 'a'
    elif hour < 12:
        hour_12 = hour
        suffix = 'a'
    elif hour == 12:
        hour_12 = 12
        suffix = 'p'
    else:
        hour_12 = hour - 12
        suffix = 'p'

    return f"{hour_12}:{minute:02d}{suffix}"

def check_memory():
    """Check available memory and force collection if low"""
    gc.collect()
    free_mem = gc.mem_free()
    if free_mem < 2048:  # If less than 2KB free
        print(f"LOW MEMORY: {free_mem} bytes free")
        gc.collect()
    return free_mem

def load_bmp_icon(filename):
    """Load BMP icon from SD card with error handling"""
    if not sd_available:
        return None

    try:
        file_path = f"/sd/bmp/{filename}"
        pic = displayio.OnDiskBitmap(file_path)
        return displayio.TileGrid(pic, pixel_shader=pic.pixel_shader)
    except Exception as e:
        print(f"Failed to load {filename}: {e}")
        return None

def update_display_with_weather_layout():
    """Create structured weather layout with icons using display.py"""
    check_memory()

    # Get current time for date/time display
    day_name, day_num, month_name = format_date()
    current_time = format_time()

    # Sample sunrise/sunset times (you can replace with real data later)
    sunrise_time = "7:31a"
    sunset_time = "4:28p"

    # Sample temperature data (you can replace with real data later)
    current_temp = -1
    feels_like = -7
    high_temp = -4
    low_temp = -10

    # Weather description
    weather_desc = "Cloudy. 40 percent chance of flurries this evening. Periods of snow beginning near midnight. Amount 2 to 4 cm. Wind up to 15 km/h. Low minus 5. Wind chill near -9."

    # Get moon phase for icon
    current_phase = calculate_moon_phase()
    moon_icon_name = phase_to_icon_name(current_phase)

    # Create weather layout using display.py
    main_group = create_weather_layout(
        day_name=day_name,
        day_num=day_num,
        month_name=month_name,
        current_temp=current_temp,
        feels_like=feels_like,
        high_temp=high_temp,
        low_temp=low_temp,
        sunrise_time=sunrise_time,
        sunset_time=sunset_time,
        weather_desc=weather_desc,
        weather_icon_name="01n.bmp",
        moon_icon_name=f"{moon_icon_name}.bmp"
    )

    # Load and position icons if SD card is available
    if sd_available:
        # Weather icon (between first line elements)
        weather_icon = load_bmp_icon("01n.bmp")
        if weather_icon:
            weather_icon.x = WEATHER_ICON_X
            weather_icon.y = WEATHER_ICON_Y
            main_group.append(weather_icon)

        # Moon phase icon (between first line elements)
        moon_icon = load_bmp_icon(f"{moon_icon_name}.bmp")
        if moon_icon:
            moon_icon.x = MOON_ICON_X
            moon_icon.y = MOON_ICON_Y
            main_group.append(moon_icon)
            print(f"Moon phase: {moon_icon_name}")

    # Update display
    display.root_group = main_group
    display.refresh()

    print("Weather layout displayed!")
    check_memory()

    # Wait for refresh to complete
    time.sleep(display.time_to_refresh + 2)
    print("Refresh complete")

# Get text capacity information
capacity = get_text_capacity()
print(f"Display: {capacity['chars_per_line']} chars/line, {capacity['lines_per_screen']} lines, {capacity['total_capacity']} total")

# Display structured weather layout
update_display_with_weather_layout()

# Main loop
print("PinkWeather ready!")
while True:
    # Add your main program logic here
    # For example:
    # - Fetch weather data from API
    # - Update display with new information
    # - Handle sensor readings
    # - etc.

    time.sleep(60)  # Sleep for 1 minute
