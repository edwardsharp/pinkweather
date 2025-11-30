import board
import busio
import displayio
import terminalio
import time

import fourwire
import adafruit_ssd1680

from adafruit_display_text.label import Label
from adafruit_display_shapes.rect import Rect

# Release any previous display
displayio.release_displays()

# --- SPI + Pins (matches your wiring) ---
spi = busio.SPI(board.GP18, MOSI=board.GP19, MISO=board.GP16)

display_bus = fourwire.FourWire(
    spi,
    command=board.GP20,     # DC
    chip_select=board.GP17, # CS
    reset=board.GP21,       # RST
    baudrate=1_000_000
)

# Create the SSD1680 display object
display = adafruit_ssd1680.SSD1680(
    display_bus,
    width=250,
    height=122,
    rotation=270,
    busy_pin=board.GP22
)

# --- Create the main displayio Group ---
g = displayio.Group()

# tell the display to use this as the root layer
display.root_group = g

# Colors
BLACK = 0x000000
WHITE = 0xFFFFFF
RED   = 0xFF0000

BORDER = 20

# Background rectangle
bg = Rect(0, 0, display.width, display.height, fill=BLACK)
g.append(bg)

# Inner rectangle
inner = Rect(
    BORDER,
    BORDER,
    display.width - 2 * BORDER,
    display.height - 2 * BORDER,
    fill=WHITE,
)
g.append(inner)

# Text label
text = "ZOMG HELLO WORLD!"
label = Label(terminalio.FONT, text=text, color=RED)
label.anchor_point = (0.5, 0.5)
label.anchored_position = (display.width // 2, display.height // 2)
g.append(label)

# Refresh the e-ink panel
display.refresh()

# Wait while display is updating
while display.busy:
    time.sleep(0.1)
