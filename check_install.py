#!/usr/bin/env python3
"""
Installation Verification Script for PinkWeather

This script checks that all required dependencies are properly installed
and provides diagnostic information for troubleshooting.
"""

import sys
import os
import subprocess
from pathlib import Path

def check_python_version():
    """Check if Python version meets requirements."""
    version = sys.version_info
    required = (3, 8)

    print(f"Python version: {version.major}.{version.minor}.{version.micro}")

    if version >= required:
        print("✓ Python version OK")
        return True
    else:
        print(f"✗ Python {required[0]}.{required[1]}+ required")
        return False

def check_module(module_name, import_name=None, optional=False):
    """Check if a Python module can be imported."""
    if import_name is None:
        import_name = module_name

    try:
        __import__(import_name)
        status = "✓" if not optional else "✓ (optional)"
        print(f"{status} {module_name}")
        return True
    except ImportError as e:
        status = "✗" if not optional else "- (optional)"
        print(f"{status} {module_name}: {e}")
        return not optional  # Return True if optional, False if required

def check_pil_features():
    """Check PIL/Pillow capabilities."""
    try:
        from PIL import Image, ImageDraw, ImageFont

        # Test basic image creation
        test_img = Image.new("RGB", (100, 50), (255, 255, 255))
        draw = ImageDraw.Draw(test_img)
        draw.text((10, 10), "Test", fill=(0, 0, 0))

        print("✓ PIL/Pillow image creation works")

        # Check font support
        try:
            font = ImageFont.load_default()
            print("✓ Default font available")
        except:
            print("! Default font issue (may still work)")

        return True
    except Exception as e:
        print(f"✗ PIL/Pillow error: {e}")
        return False

def check_font_file():
    """Check if the TTF font file exists."""
    font_path = Path("AndaleMono.ttf")

    if font_path.exists():
        print("✓ AndaleMono.ttf found")
        return True
    else:
        print("! AndaleMono.ttf not found (will use system font)")
        return True  # Non-critical

def check_project_files():
    """Check if required project files exist."""
    required_files = [
        "display_renderer.py",
        "http_server.py",
        "code.py"
    ]

    all_good = True
    for file_path in required_files:
        if Path(file_path).exists():
            print(f"✓ {file_path}")
        else:
            print(f"✗ {file_path} missing")
            all_good = False

    return all_good

def check_display_renderer():
    """Test the display renderer module."""
    try:
        from display_renderer import WeatherDisplayRenderer

        # Test basic functionality
        renderer = WeatherDisplayRenderer()
        image = renderer.render_text_display("Test message")

        if image.size == (250, 122):
            print("✓ Display renderer working correctly")
            return True
        else:
            print(f"! Display renderer size issue: {image.size}")
            return False

    except Exception as e:
        print(f"✗ Display renderer error: {e}")
        return False

def check_http_server():
    """Test if HTTP server can be imported."""
    try:
        import http_server
        print("✓ HTTP server module loads")
        return True
    except Exception as e:
        print(f"✗ HTTP server error: {e}")
        return False

def check_circuitpython_compatibility():
    """Check for CircuitPython-specific modules (informational only)."""
    print("\nCircuitPython compatibility check (for microcontroller deployment):")

    modules_to_check = [
        ("board", "board"),
        ("busio", "busio"),
        ("digitalio", "digitalio"),
        ("adafruit_epd.ssd1680", "adafruit_epd.ssd1680")
    ]

    available_count = 0
    for display_name, import_name in modules_to_check:
        if check_module(display_name, import_name, optional=True):
            available_count += 1

    if available_count == 0:
        print("ℹ  No CircuitPython modules found (normal for development environment)")
    else:
        print(f"ℹ  {available_count}/{len(modules_to_check)} CircuitPython modules available")

def run_functional_test():
    """Run a functional test of the system."""
    print("\nRunning functional test...")

    try:
        from display_renderer import WeatherDisplayRenderer

        # Test different rendering modes
        renderer = WeatherDisplayRenderer()

        # Text rendering
        text_img = renderer.render_text_display("Installation test successful!", "Test")

        # Weather rendering
        weather_img = renderer.render_weather_layout(
            "72°F", "Test", "Test Location", "All systems OK"
        )

        # Debug rendering
        debug_img = renderer.render_debug_display({"Status": "OK", "Test": "Pass"})

        # Save test images
        text_img.save("test_text.png")
        weather_img.save("test_weather.png")
        debug_img.save("test_debug.png")

        print("✓ Functional test passed")
        print("✓ Test images saved (test_*.png)")
        return True

    except Exception as e:
        print(f"✗ Functional test failed: {e}")
        return False

def main():
    """Main verification function."""
    print("PinkWeather Installation Verification")
    print("=" * 40)

    checks_passed = 0
    total_checks = 0

    # Core system checks
    print("\n1. System Requirements:")
    if check_python_version():
        checks_passed += 1
    total_checks += 1

    # Module availability checks
    print("\n2. Required Modules:")
    modules = [
        ("PIL (Pillow)", "PIL"),
        ("urllib.parse", "urllib.parse"),
        ("http.server", "http.server"),
        ("base64", "base64"),
        ("io", "io"),
        ("json", "json"),
        ("time", "time"),
    ]

    for display_name, import_name in modules:
        if check_module(display_name, import_name):
            checks_passed += 1
        total_checks += 1

    # Optional modules
    print("\n3. Optional Modules:")
    check_module("requests", "requests", optional=True)

    # PIL functionality
    print("\n4. Image Processing:")
    if check_pil_features():
        checks_passed += 1
    total_checks += 1

    # Project files
    print("\n5. Project Files:")
    if check_project_files():
        checks_passed += 1
    total_checks += 1

    check_font_file()  # Non-critical

    # Module functionality
    print("\n6. Module Functionality:")
    if check_display_renderer():
        checks_passed += 1
    total_checks += 1

    if check_http_server():
        checks_passed += 1
    total_checks += 1

    # CircuitPython compatibility (informational)
    check_circuitpython_compatibility()

    # Functional test
    print("\n7. Functional Test:")
    if run_functional_test():
        checks_passed += 1
    total_checks += 1

    # Summary
    print("\n" + "=" * 40)
    print(f"Installation Check Summary: {checks_passed}/{total_checks} passed")

    if checks_passed == total_checks:
        print("✓ Installation is complete and working!")
        print("\nNext steps:")
        print("  • Run 'python http_server.py' to start the development server")
        print("  • Open http://localhost:8000 in your browser")
        print("  • Copy required files to Pi Pico 2W for deployment")
    else:
        print("! Some issues detected. Please check the output above.")
        print("\nCommon fixes:")
        print("  • Run: pip install -r requirements.txt")
        print("  • Ensure you're in the correct directory")
        print("  • Check Python version compatibility")

    return checks_passed == total_checks

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
