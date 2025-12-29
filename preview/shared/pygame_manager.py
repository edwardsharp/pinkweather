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
        current_file = Path(__file__).resolve()  # Resolve file path first
        self.hardware_path = current_file.parent.parent.parent / "300x400" / "CIRCUITPY"
        self.icons_path = current_file.parent.parent.parent / "iconz" / "bmp"
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

        class MockBoard:
            LED = "LED"  # Mock LED pin

        # Install minimal mocks
        sys.modules["wifi"] = MockWifi()
        sys.modules["adafruit_hdc302x"] = MockSensor()
        sys.modules["board"] = MockBoard()

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
            # Import the correct display function that expects weather_data dict
            from display.weather_display import create_weather_display_layout

            # Create layout using the function that accepts weather_data dict
            layout = create_weather_display_layout(
                weather_data,
                icon_loader=self.create_icon_loader(use_icons=False),
                indoor_temp_humidity="20° 45%",
            )

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
        """Extract text metrics from narrative text using actual text wrapping"""
        try:
            # Get the narrative text from instance variable (set by image renderer)
            narrative_text = getattr(self, "_current_narrative", "")

            if not narrative_text:
                return {
                    "fits_in_space": True,
                    "line_count": 0,
                    "char_count": 0,
                    "stripped_text": "",
                }

            # Strip markup tags to get plain text
            stripped_text = self._strip_markup_tags(narrative_text)
            char_count = len(stripped_text)

            # Get actual line count by using the text renderer's wrapping logic
            line_count = self._get_wrapped_line_count(narrative_text)

            # Simple check: assume max 8-10 lines fit comfortably
            max_lines = 9
            fits_in_space = line_count <= max_lines

            return {
                "fits_in_space": fits_in_space,
                "line_count": line_count,
                "char_count": char_count,
                "stripped_text": stripped_text,
            }

        except Exception as e:
            print(f"Text metrics calculation failed: {e}")
            return {
                "fits_in_space": True,
                "line_count": 1,
                "char_count": 0,
                "stripped_text": "",
            }

    def _get_wrapped_line_count(self, narrative_text):
        """Get actual line count by using text renderer's wrapping logic"""
        try:
            # Import text renderer from hardware directory
            from display.text_renderer import TextRenderer

            # Create text renderer instance
            renderer = TextRenderer()

            # Parse markup and wrap text using the same logic as display
            segments = renderer.parse_markup(narrative_text)
            wrapped_lines = renderer.hard_wrap_text(segments)

            return len(wrapped_lines)

        except Exception as e:
            print(f"Failed to get wrapped line count: {e}")
            # Fallback: estimate based on character count
            chars_per_line = 50  # Conservative estimate
            stripped_text = self._strip_markup_tags(narrative_text)
            estimated_lines = max(
                1, (len(stripped_text) + chars_per_line - 1) // chars_per_line
            )
            return estimated_lines

    def _strip_markup_tags(self, text):
        """Remove markup tags like <h>, <i>, <b>, <red> from text"""
        import re

        # Remove all markup tags but keep the content inside
        cleaned = re.sub(r"<[^>]+>", "", text)
        return cleaned.strip()

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
