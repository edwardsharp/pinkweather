"""
SD Card Debug Script for Pico 2W with Adafruit eInk Feather Friend
Tests SD card initialization step by step to isolate issues
"""

import time
import board
import busio
import digitalio
import adafruit_sdcard
import storage
import os
from digitalio import DigitalInOut

print("=== SD Card Debug Test ===")
print("Hardware: Pico 2W + Adafruit eInk Feather Friend")

# Use shared SPI bus (don't create new one - display already uses it)
print("1. Using shared SPI bus...")
print("   Note: Run this separately, not with main display code!")
try:
    spi = busio.SPI(clock=board.GP18, MOSI=board.GP19, MISO=board.GP16)
    print(f"   SPI initialized: {spi}")
except ValueError as e:
    print(f"   SPI conflict: {e}")
    print("   This is expected if display code is running")
    print("   Run this script alone, without main code.py")
    import sys
    sys.exit(1)

# Initialize SRAM CS pin (disable SRAM to avoid conflicts)
print("2. Disabling SRAM (SRCS high)...")
try:
    srcs_pin = DigitalInOut(board.GP22)  # Guess - you may need to adjust
    srcs_pin.direction = digitalio.Direction.OUTPUT
    srcs_pin.value = True  # High = SRAM disabled
    print(f"   SRAM disabled on GP22")
except Exception as e:
    print(f"   Could not disable SRAM on GP22: {e}")
    print("   Trying without SRAM control...")

# Initialize SD card CS pin
print("3. Initializing SD CS pin...")
cs_sd = DigitalInOut(board.GP21)
cs_sd.direction = digitalio.Direction.OUTPUT
cs_sd.value = True  # Start high (deselected)
print(f"   SD CS pin ready on GP21")

# Test SPI communication
print("4. Testing SPI bus...")
try:
    # Try to lock SPI
    while not spi.try_lock():
        pass
    print("   SPI lock acquired")

    # Configure SPI
    spi.configure(baudrate=250000, phase=0, polarity=0)
    print("   SPI configured (250kHz)")

    spi.unlock()
    print("   SPI unlocked - bus is working")
except Exception as e:
    print(f"   SPI test failed: {e}")

# Try SD card initialization
print("5. Creating SDCard object...")
try:
    sdcard = adafruit_sdcard.SDCard(spi, cs_sd, baudrate=250000)
    print("   SDCard object created successfully!")

    print("6. Creating filesystem...")
    vfs = storage.VfsFat(sdcard)
    print("   VfsFat created")

    print("7. Mounting filesystem...")
    storage.mount(vfs, "/sd")
    print("   Mounted at /sd")

    print("8. Testing file access...")
    files = os.listdir("/sd")
    print(f"   Files found: {files}")

    # Test creating a file
    print("9. Testing write access...")
    with open("/sd/test.txt", "w") as f:
        f.write("Hello from Pico 2W!")
    print("   Write test successful")

    # Test reading the file
    with open("/sd/test.txt", "r") as f:
        content = f.read()
    print(f"   Read test: '{content}'")

    print("\n✅ SD CARD WORKING PERFECTLY!")

except Exception as e:
    print(f"\n❌ SD card failed at step: {e}")
    print(f"   Error type: {type(e).__name__}")

    # Troubleshooting suggestions
    print("\n🔧 Troubleshooting:")
    print("   1. Check wiring:")
    print("      GP21 -> SD CS")
    print("      GP18 -> SD SCK")
    print("      GP19 -> SD MOSI")
    print("      GP16 -> SD MISO")
    print("      3.3V -> SD VCC")
    print("      GND  -> SD GND")
    print("   2. SRAM CS (SRCS) - try connecting to:")
    print("      GP22 (or another available pin)")
    print("   3. SD Card requirements:")
    print("      - FAT32 formatted")
    print("      - 32GB or smaller")
    print("      - Class 4+ speed")
    print("   4. Try different baudrates:")
    print("      - 100000 (very slow)")
    print("      - 250000 (current)")
    print("      - 1000000 (fast)")

print("\nDebug complete.")
