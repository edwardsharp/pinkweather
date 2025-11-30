# SPDX-FileCopyrightText: 2019 Melissa LeBlanc-Williams for Adafruit Industries
# SPDX-License-Identifier: MIT

"""
Weather Display for Pi Pico 2W with e-ink display.
Uses modular rendering system compatible with development server.
"""

import board
import busio
import digitalio
from adafruit_epd.ssd1680 import Adafruit_SSD1680
from display_renderer import WeatherDisplayRenderer

def setup_display():
    """Initialize the e-ink display hardware."""
    # Create the SPI device and pins
    spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
    ecs = digitalio.DigitalInOut(board.CE0)
    dc = digitalio.DigitalInOut(board.D22)
    srcs = None
    rst = digitalio.DigitalInOut(board.D27)
    busy = digitalio.DigitalInOut(board.D17)

    display = Adafruit_SSD1680(
        122,
        250,        # 2.13" Tri-color display
        spi,
        cs_pin=ecs,
        dc_pin=dc,
        sramcs_pin=srcs,
        rst_pin=rst,
        busy_pin=busy,
    )

    display.rotation = 1
    return display

def main():
    """Main function to render and display content."""
    # Initialize hardware
    display = setup_display()

    # Create renderer with display dimensions
    renderer = WeatherDisplayRenderer(
        width=display.width,
        height=display.height,
        font_path="AndaleMono.ttf"
    )

    # Example 1: Simple text display
    sample_text = "Hello from your weather display! This is a test of the text wrapping functionality."
    image = renderer.render_text_display(sample_text, "Weather Station")

    # Example 2: Weather layout (uncomment to use)
    # image = renderer.render_weather_layout(
    #     temperature="72°F",
    #     condition="Sunny",
    #     location="San Francisco, CA",
    #     additional_info="Humidity: 65%\nWind: 5mph NW\nUV Index: 6"
    # )

    # Example 3: Debug display (uncomment to use)
    # debug_info = {
    #     "Memory": "45%",
    #     "CPU": "23%",
    #     "WiFi": "Connected",
    #     "Signal": "-42 dBm",
    #     "Uptime": "2h 15m"
    # }
    # image = renderer.render_debug_display(debug_info)

    # Display the rendered image
    display.image(image)
    display.display()

    print("Display updated successfully!")

if __name__ == '__main__':
    main()
