"""
PinkWeather CircuitPython Code for 400x300 E-ink Display
Text display with markup support and hard word wrapping
"""

import time
import board
import busio
import displayio
import fourwire
import adafruit_ssd1683

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
    highlight_color=0xFF0000,
    busy_pin=busy_pin
)

# Rotate display 180 degrees
display.rotation = 180

# Display dimensions and colors
DISPLAY_WIDTH = 400
DISPLAY_HEIGHT = 300
BLACK = 0x000000
WHITE = 0xFFFFFF
RED = 0xFF0000

def update_display_with_text(text_content):
    """Update display with formatted text content"""
    print("Updating display...")

    # Create text display using shared display function
    display_group = create_text_display(text_content)

    # Set the root group and refresh the display
    display.root_group = display_group
    display.refresh()

    print("Display refreshed!")

    # Wait for the refresh to complete
    time.sleep(display.time_to_refresh + 2)
    print("Refresh complete")

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
print("Rendering initial text...")
update_display_with_text(sample_text)

# main loop
print("hello pinkweather!")
while True:

    time.sleep(60)  # 😴
