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
import os
from digitalio import DigitalInOut

# shared display functions
from display import create_text_display, get_text_capacity

# Release any previously used displays
displayio.release_displays()

# Pin assignments for Pico 2W
# SPI pins: SCK=GP18, MOSI=GP19, MISO=GP16
# CS pin: GP17, DC pin: GP20
spi = busio.SPI(clock=board.GP18, MOSI=board.GP19, MISO=board.GP16)

# Pin assignments for FourWire (use Pin objects directly)
cs_pin = board.GP17
dc_pin = board.GP20

# Reset and Busy pins (optional but recommended)
rst_pin = None  # board.GP21
busy_pin = None  # digitalio.DigitalInOut(board.GP22) #TODO wire this!

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
    highlight_color=0x000000,
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

        print(f"Loaded {filename}: {pic.width}x{pic.height} pixels")

        # Debug bitmap properties
        print(f"  Pixel shader type: {type(pic.pixel_shader)}")
        if hasattr(pic.pixel_shader, '__len__'):
            print(f"  Palette colors: {len(pic.pixel_shader)}")

        # Use original ColorConverter - custom palette made icons invisible
        tilegrid = displayio.TileGrid(pic, pixel_shader=pic.pixel_shader)
        print(f"  Using ColorConverter")

        return tilegrid
    except Exception as e:
        print(f"Failed to load {filename}: {e}")
        return None

def update_display_with_icons_and_text(text_content):
    """Update display with weather icon, moon icon, and text"""
    check_memory()

    # Create main display group
    main_group = displayio.Group()

    # Create white background
    background_bitmap = displayio.Bitmap(DISPLAY_WIDTH, DISPLAY_HEIGHT, 1)
    background_palette = displayio.Palette(1)
    background_palette[0] = WHITE
    background_sprite = displayio.TileGrid(background_bitmap, pixel_shader=background_palette)
    main_group.append(background_sprite)

    # Load three test icons to debug red artifacts
    if sd_available:
        # Load night weather icon (01n.bmp)
        weather_night_icon = load_bmp_icon("01n.bmp")
        if weather_night_icon:
            weather_night_icon.x = 10   # Left side
            weather_night_icon.y = 10   # Top
            main_group.append(weather_night_icon)
            print(f"01n.bmp at ({weather_night_icon.x}, {weather_night_icon.y})")

        # Load day weather icon (01d.bmp)
        weather_day_icon = load_bmp_icon("01d.bmp")
        if weather_day_icon:
            weather_day_icon.x = 90   # Middle
            weather_day_icon.y = 10   # Top
            main_group.append(weather_day_icon)
            print(f"01d.bmp at ({weather_day_icon.x}, {weather_day_icon.y})")

        # Load moon phase icon
        current_phase = calculate_moon_phase()
        moon_icon_name = phase_to_icon_name(current_phase)
        moon_icon = load_bmp_icon(f"{moon_icon_name}.bmp")
        if moon_icon:
            moon_icon.x = 170  # Right side
            moon_icon.y = 10   # Top
            main_group.append(moon_icon)
            print(f"Moon icon at ({moon_icon.x}, {moon_icon.y}): {moon_icon_name}")
    else:
        print("SD card not available - no icons loaded")

    # Create text display (moved down to make room for icons)
    text_group = create_text_display(text_content)
    # Offset the text group down by 80 pixels to make room for icons (64px + margin)
    text_group.y = 80
    main_group.append(text_group)

    # Clear display first to prevent red artifacts
    display.root_group = displayio.Group()
    time.sleep(0.1)

    # Set the root group and refresh the display
    display.root_group = main_group
    display.refresh()

    print("Display refreshed!")
    check_memory()

    # Wait for the refresh to complete
    time.sleep(display.time_to_refresh + 2)
    print("Refresh complete")

def update_display_with_text(text_content):
    """Update display with formatted text content (legacy function)"""
    update_display_with_icons_and_text(text_content)

# Get and print text capacity information
capacity = get_text_capacity()
print(f"Display capacity: ~{capacity['chars_per_line']} chars/line, ~{capacity['lines_per_screen']} lines")
print(f"Total capacity: ~{capacity['total_capacity']} characters")
print(f"Font metrics: {capacity['char_width']}w x {capacity['char_height']}h, line height: {capacity['line_height']}")

# Sample weather text with markup
sample_text = """<b>Now:</b> <red>Cloudy</red> conditions with <i>rain</i> expected around <b>2am</b>. Wind gusts up to <b>25mph</b> making it feel like <red>-2°C</red>.

<b>Tomorrow:</b> <red>Sunny</red> and <b>4°C</b> with light winds from the <i>west</i> at 10mph.

<b>Weekend:</b> <bi>Partly cloudy</bi> with temperatures reaching <b>6°C</b>."""

# Initial display update
print("Rendering initial text with icons...")
update_display_with_icons_and_text(sample_text)

# main loop
print("hello pinkweather!")
while True:

    time.sleep(60)  # 😴
