import time
import board
import busio
import digitalio
import displayio
import fourwire
import terminalio
from adafruit_display_text import label
import adafruit_ssd1683

# Release any previously used displays
displayio.release_displays()

# Pin assignments for Pico 2W
# SPI pins: SCK=GP18, MOSI=GP19, MISO=GP16
# CS pin: GP17
spi = busio.SPI(clock=board.GP18, MOSI=board.GP19, MISO=board.GP16)

# Pin assignments for FourWire (use Pin objects directly)
cs_pin = board.GP17
dc_pin = board.GP20

# Reset and Busy pins (optional but recommended)
# Connect these to available GPIO pins if you have them wired
rst_pin = None  # board.GP21
busy_pin = None  # digitalio.DigitalInOut(board.GP22) if u want 2

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

# Create a display group
g = displayio.Group()

# Display dimensions and colors
DISPLAY_WIDTH = 400
DISPLAY_HEIGHT = 300
BLACK = 0x000000
WHITE = 0xFFFFFF
RED = 0xFF0000

# Create "Hello World!" text
status_text = "Hello World!"
status_label = label.Label(terminalio.FONT, text=status_text, color=WHITE, scale=3)
status_label.anchor_point = (0.5, 0.5)
status_label.anchored_position = (DISPLAY_WIDTH // 2, DISPLAY_HEIGHT // 2)

# Add the label to the group
g.append(status_label)

# Set the root group and refresh the display
display.root_group = g
display.refresh()

print("Display refreshed with Hello World!")

# Wait for the refresh to complete
time.sleep(display.time_to_refresh)
print("Refresh complete")

# Keep the program running
while True:
    time.sleep(10)
