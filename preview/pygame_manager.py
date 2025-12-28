"""
Persistent pygame display manager for high-performance batch processing
Based on proven minimal approach - keep it simple!
"""

import os
import sys
import time
from pathlib import Path

# Force generic platform
os.environ["BLINKA_FORCEBOARD"] = "GENERIC_LINUX_PC"
os.environ["BLINKA_FORCECHIP"] = "GENERIC_X86"

# Try to disable DisplayIO background threads for cleaner shutdown
os.environ["DISPLAYIO_NO_BACKGROUND"] = "1"

import blinka_displayio_pygamedisplay
import pygame


class PersistentPygameDisplay:
    """Manages a single pygame display instance for batch processing"""

    def __init__(self, width=400, height=300):
        self.width = width
        self.height = height
        self.display = None
        self.original_cwd = os.getcwd()
        self.hardware_path = Path(__file__).parent.parent / "300x400" / "CIRCUITPY"
        self.icons_path = Path(__file__).parent.parent / "iconz" / "bmp"
        self._setup_mocks()

    def _setup_mocks(self):
        """Setup minimal mocks - only what we actually need"""

        # Minimal mocks
        class MockWifi:
            class Radio:
                def connect(self, ssid, password):
                    pass

                @property
                def connected(self):
                    return True

            radio = Radio()

        class MockSensor:
            @property
            def temperature(self):
                return 21.5

            @property
            def relative_humidity(self):
                return 65.0

        # Install minimal mocks
        sys.modules["wifi"] = MockWifi()
        sys.modules["adafruit_hdc302x"] = MockSensor()

    def _setup_hardware_imports(self):
        """Setup path and import hardware modules"""
        # Add hardware path and change directory for font loading
        if str(self.hardware_path) not in sys.path:
            sys.path.insert(0, str(self.hardware_path))
        os.chdir(self.hardware_path)

    def create_icon_loader(self, use_icons=True):
        """Create icon loader for hardware modules"""
        if not use_icons:
            return None

        def load_icon(filename):
            try:
                import displayio

                file_path = self.icons_path / filename
                if file_path.exists():
                    pic = displayio.OnDiskBitmap(str(file_path))
                    return displayio.TileGrid(pic, pixel_shader=pic.pixel_shader)
            except:
                pass
            return None

        return load_icon

    def start(self):
        """Initialize pygame display"""
        if self.display is None:
            # Initialize pygame first to ensure clean state
            pygame.init()
            self.display = blinka_displayio_pygamedisplay.PyGameDisplay(
                width=self.width, height=self.height
            )

            # Try to disable background refresh if possible
            if hasattr(self.display, "_auto_refresh"):
                self.display._auto_refresh = False

        return self.display

    def render_weather_data(self, weather_data, output_file):
        """Render single image efficiently - PNG only"""
        if self.display is None:
            self.start()

        try:
            # Import hardware modules from current directory
            from display.header import create_weather_layout

            # Create layout with real hardware code
            layout = create_weather_layout(**weather_data)

            # Render
            self.display.root_group = layout
            self.display.refresh()

            # Save PNG only
            pygame.image.save(self.display._pygame_screen, str(output_file))

            # Clear for next render (important for memory)
            self.display.root_group = None

            return output_file

        finally:
            # Keep current directory for consistency
            pass

    def measure_narrative_text(self, weather_data):
        """Measure narrative text fitting using real pygame rendering"""
        if self.display is None:
            self.start()

        try:
            # Import hardware modules from current directory
            from display.header import create_weather_layout

            # Create layout to measure actual text dimensions
            layout = create_weather_layout(**weather_data)

            # Render to get accurate measurements
            self.display.root_group = layout
            self.display.refresh()

            # Extract text measurements from rendered layout
            text_metrics = self._extract_text_metrics(layout)

            # Clear for next render
            self.display.root_group = None

            return text_metrics

        finally:
            # Keep current directory for consistency
            pass

    def _extract_text_metrics(self, layout):
        """Extract real text measurements from rendered layout"""
        # TODO: Implement actual measurement by walking DisplayIO group
        # For now, return placeholder that can be refined
        available_height = 120  # Available space for narrative text in layout

        return {
            "fits_in_space": True,  # TODO: implement real measurement
            "line_count": 3,
            "height": 85,
            "width": 380,
        }

    def shutdown(self):
        """Clean shutdown with proper DisplayIO thread handling"""
        if self.display:
            # Clear any remaining groups
            self.display.root_group = None

            # Try to stop any background processes
            try:
                # Disable auto refresh to stop background updates
                if hasattr(self.display, "_auto_refresh"):
                    self.display._auto_refresh = False

                # Stop any running threads
                if hasattr(self.display, "stop"):
                    self.display.stop()

                # Clear any background tasks
                if hasattr(self.display, "_background_task"):
                    self.display._background_task = None

                # Try to clean up any running event loops
                import displayio

                if hasattr(displayio, "_stop_background"):
                    displayio._stop_background()

            except Exception:
                pass  # Ignore errors during cleanup

            # Small delay to let threads finish
            import time

            time.sleep(0.05)

            # Force garbage collection
            import gc

            gc.collect()

            # Quit pygame with error handling
            try:
                if pygame.get_init():
                    pygame.display.quit()
                    pygame.quit()
            except Exception:
                pass

            self.display = None

        # Restore original working directory
        os.chdir(self.original_cwd)
