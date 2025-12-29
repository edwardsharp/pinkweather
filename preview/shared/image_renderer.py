"""
Centralized image renderer for preview system
Simplified approach that just works
"""

import os
import sys
from pathlib import Path

# Setup environment and paths
os.environ["BLINKA_FORCEBOARD"] = "GENERIC_LINUX_PC"
os.environ["BLINKA_FORCECHIP"] = "GENERIC_X86"
os.environ["DISPLAYIO_NO_BACKGROUND"] = "1"

# Add preview and hardware paths using absolute resolution
current_file = Path(__file__).resolve()  # Resolve file path first
preview_dir = current_file.parent.parent
hardware_path = preview_dir.parent / "300x400" / "CIRCUITPY"

if str(preview_dir) not in sys.path:
    sys.path.insert(0, str(preview_dir))
if str(hardware_path) not in sys.path:
    sys.path.insert(0, str(hardware_path))

# Import preview config with mocks
import shared.config as preview_config

# Mock hardware modules
sys.modules["config"] = preview_config
sys.modules["board"] = preview_config.board

# Setup filesystem
from shared.setup_filesystem import setup_preview_filesystem

setup_preview_filesystem()

from shared.pygame_manager import PersistentPygameDisplay

# Global display instance to prevent "Too many displays" error
_global_display = None

# Batch mode optimization globals
_batch_mode = False
_batch_icon_loader = None
_batch_display_function = None
_batch_imports_setup = False

# Cache display function to avoid repeated imports
_display_function = None

# Global variable to capture generated narrative
_last_generated_narrative = None


class WeatherImageRenderer:
    """Centralized weather image renderer for preview system"""

    def __init__(self, width=400, height=300):
        self.width = width
        self.height = height
        self.pygame_display = None
        self.original_cwd = os.getcwd()
        self._in_batch_context = False

    def _ensure_display(self):
        """Ensure pygame display is initialized (using global instance)"""
        global _global_display
        if _global_display is None:
            _global_display = PersistentPygameDisplay(self.width, self.height)
            _global_display.start()
        self.pygame_display = _global_display

    def _get_display_function(self):
        """Get cached display function, importing only once"""
        global _display_function
        if _display_function is None:
            # Setup hardware imports and change directory BEFORE importing
            if self.pygame_display:
                self.pygame_display._setup_hardware_imports()

            try:
                # Import display modules after changing directory
                import pygame
                from display.weather_display import create_weather_display_layout

                _display_function = create_weather_display_layout
            finally:
                # Always restore directory
                os.chdir(self.original_cwd)

        return _display_function

    def _capture_narrative_from_layout(self, weather_data, icon_loader):
        """Create layout and capture the generated narrative"""
        global _last_generated_narrative

        # In batch mode, use cached imports and skip directory changes
        if _batch_mode and _batch_display_function and _batch_imports_setup:
            try:
                # Use cached display function
                layout = _batch_display_function(
                    weather_data,
                    icon_loader=icon_loader,
                    indoor_temp_humidity="20°69%",
                )

                # Generate narrative using cached import
                from display.weather_display import generate_weather_narrative

                narrative = generate_weather_narrative(weather_data)
                _last_generated_narrative = narrative

                return layout, narrative
            except Exception as e:
                print(f"Batch mode layout creation failed: {e}")
                # Fall back to regular mode
                pass

        # Regular mode: change directory for imports
        # Don't change directory if we're already in batch context
        if not self._in_batch_context:
            os.chdir(hardware_path)

        try:
            # Import the display function
            from display.weather_display import create_weather_display_layout

            # Create the layout using the correct function that expects weather_data dict
            layout = create_weather_display_layout(
                weather_data,
                icon_loader=icon_loader,
                indoor_temp_humidity="20°69%",
            )

            # Generate the narrative separately to capture it
            from display.weather_display import generate_weather_narrative

            narrative = generate_weather_narrative(weather_data)
            _last_generated_narrative = narrative

            return layout, narrative
        finally:
            # Only change back if we changed in the first place
            if not self._in_batch_context:
                os.chdir(self.original_cwd)

    def render_weather_data_to_file(
        self, weather_data, output_file, use_icons=True, indoor_temp_humidity="20°69%"
    ):
        """Render weather data to PNG file using shared display modules

        Args:
            weather_data: Display variables from weather_api.get_display_variables()
            output_file: Output PNG file path (string or Path)
            use_icons: Whether to load and display weather icons
            indoor_temp_humidity: Indoor temperature/humidity string

        Returns:
            Path to output file on success, None on failure
        """
        try:
            self._ensure_display()

            # In batch mode, reuse cached components for performance
            if _batch_mode and _batch_icon_loader:
                icon_loader = _batch_icon_loader
            else:
                icon_loader = self.pygame_display.create_icon_loader(
                    use_icons=use_icons
                )

            # Create layout and capture narrative
            layout, narrative = self._capture_narrative_from_layout(
                weather_data,
                icon_loader,
            )

            # Ensure display exists before using it
            if self.pygame_display.display is None:
                self.pygame_display.start()

            # Optimize directory changes in batch mode
            if _batch_mode:
                # In batch mode, we should already be in the right context
                try:
                    import pygame

                    self.pygame_display.display.root_group = layout
                    self.pygame_display.display.refresh()
                    pygame.image.save(
                        self.pygame_display.display._pygame_screen, str(output_file)
                    )
                    self.pygame_display.display.root_group = None
                except ImportError:
                    # Fallback to directory change if imports fail
                    return self._render_with_directory_change(layout, output_file)
            else:
                return self._render_with_directory_change(layout, output_file)

            # Verify file was created
            if Path(output_file).exists():
                return Path(output_file)
            else:
                return None

        except Exception as e:
            print(f"Error rendering weather image: {e}")
            return None

    def _render_with_directory_change(self, layout, output_file):
        """Render with directory change (fallback method)"""
        os.chdir(hardware_path)
        try:
            import pygame

            self.pygame_display.display.root_group = layout
            self.pygame_display.display.refresh()
            pygame.image.save(
                self.pygame_display.display._pygame_screen, str(output_file)
            )
            self.pygame_display.display.root_group = None

            if Path(output_file).exists():
                return Path(output_file)
            else:
                return None
        finally:
            os.chdir(self.original_cwd)

    def render_weather_data_to_bytes(
        self, weather_data, use_icons=True, indoor_temp_humidity="20°69%"
    ):
        """Render weather data to PNG bytes (for HTTP responses)

        Args:
            weather_data: Display variables from weather_api.get_display_variables()
            use_icons: Whether to load and display weather icons
            indoor_temp_humidity: Indoor temperature/humidity string

        Returns:
            PNG bytes on success, None on failure
        """
        try:
            import io

            self._ensure_display()

            # Create layout and capture narrative
            layout, narrative = self._capture_narrative_from_layout(
                weather_data,
                self.pygame_display.create_icon_loader(use_icons=use_icons),
            )

            # Ensure display exists before using it
            if self.pygame_display.display is None:
                self.pygame_display.start()

            # Change to hardware directory for font loading during render
            os.chdir(hardware_path)
            try:
                # Render image
                import pygame

                self.pygame_display.display.root_group = layout
                self.pygame_display.display.refresh()

                # Save to bytes buffer instead of file
                buffer = io.BytesIO()
                pygame.image.save(
                    self.pygame_display.display._pygame_screen, buffer, "PNG"
                )
                self.pygame_display.display.root_group = None

                return buffer.getvalue()
            finally:
                # Always restore original directory
                os.chdir(self.original_cwd)

        except Exception as e:
            print(f"Error rendering weather image to bytes: {e}")
            return None

    def measure_narrative_text(self, weather_data):
        """Measure how narrative text will fit in the layout

        Args:
            weather_data: Display variables from weather_api.get_display_variables()

        Returns:
            Dict with measurement info: fits_in_space, line_count, height, width
        """
        try:
            # Fast text-only measurement - skip expensive layout creation
            return self._fast_text_measurement(weather_data)

        except Exception as e:
            print(f"Error measuring narrative text: {e}")
            return {
                "fits_in_space": False,
                "line_count": 0,
                "height": 0,
                "width": 0,
            }

    def _fast_text_measurement(self, weather_data):
        """Fast text measurement without creating full display layout"""
        try:
            self._ensure_display()

            # Generate just the narrative text without creating full layout
            os.chdir(hardware_path)
            try:
                # Set up CSV history data source if available (dependency injection)
                if (
                    hasattr(self, "_weather_history_manager")
                    and self._weather_history_manager
                ):
                    self._weather_history_manager.setup_csv_history_data_source()

                from display.weather_display import generate_weather_narrative

                narrative = generate_weather_narrative(weather_data)

                # Use pygame manager for text measurement while in hardware directory
                wrap_result = self.pygame_display._get_wrapped_text_and_count(narrative)
                line_count = wrap_result["line_count"]
                wrapped_text = wrap_result["wrapped_text"]
                char_count = len(self.pygame_display._strip_markup_tags(narrative))
                stripped_text = self.pygame_display._strip_markup_tags(narrative)
            finally:
                os.chdir(self.original_cwd)

            # Estimate if it fits (screen can show 7 lines max)
            fits_in_space = line_count <= 7

            return {
                "fits_in_space": fits_in_space,
                "line_count": line_count,
                "char_count": char_count,
                "stripped_text": stripped_text,
                "wrapped_text": wrapped_text,  # Hard-wrapped text with newlines
                "narrative_text": narrative,
                "height": line_count * 20,  # Estimated line height
                "width": char_count * 8,  # Estimated char width
            }

        except Exception as e:
            print(f"Fast text measurement failed: {e}")
            # Fallback to original method if fast method fails
            return self._full_layout_measurement(weather_data)

    def _full_layout_measurement(self, weather_data):
        """Full layout measurement (original method) as fallback"""
        try:
            self._ensure_display()

            # Create layout and capture narrative
            layout, narrative = self._capture_narrative_from_layout(
                weather_data, self.pygame_display.create_icon_loader(use_icons=False)
            )

            # Ensure display exists before using it
            if self.pygame_display.display is None:
                self.pygame_display.start()

            # Change to hardware directory for font loading during render
            os.chdir(hardware_path)
            try:
                # Render layout to get accurate measurements
                self.pygame_display.display.root_group = layout
                self.pygame_display.display.refresh()

                # Pass narrative text to pygame manager for measurement
                self.pygame_display._current_narrative = narrative

                # Extract text measurements from rendered layout
                text_metrics = self.pygame_display.measure_narrative_text(weather_data)

                # Add the actual narrative text to the metrics
                text_metrics["narrative_text"] = narrative

                # Clear layout
                self.pygame_display.display.root_group = None

                return text_metrics
            finally:
                # Always restore original directory
                os.chdir(self.original_cwd)

        except Exception as e:
            print(f"Full layout measurement failed: {e}")
            return {
                "fits_in_space": False,
                "line_count": 0,
                "height": 0,
                "width": 0,
            }

    def start_batch_mode(self):
        """Start batch mode for high-performance bulk operations"""
        global \
            _batch_mode, \
            _batch_icon_loader, \
            _batch_display_function, \
            _batch_imports_setup

        try:
            print("Initializing batch mode...")
            _batch_mode = True
            self._in_batch_context = True

            # Set silent mode for hardware logger to suppress verbose logging
            from shared.setup_filesystem import set_hardware_silent_mode

            set_hardware_silent_mode(True)

            # Ensure display is ready
            self._ensure_display()

            # Setup hardware environment once
            os.chdir(hardware_path)

            # Setup hardware imports once
            self.pygame_display._setup_hardware_imports()

            # Cache display function import
            from display.weather_display import create_weather_display_layout

            _batch_display_function = create_weather_display_layout

            # Create reusable icon loader
            _batch_icon_loader = self.pygame_display.create_icon_loader(use_icons=True)

            _batch_imports_setup = True
            print("Batch mode initialized successfully")

        except Exception as e:
            print(f"Failed to initialize batch mode: {e}")
            self.stop_batch_mode()
            raise

    def stop_batch_mode(self):
        """Stop batch mode and cleanup resources"""
        global \
            _batch_mode, \
            _batch_icon_loader, \
            _batch_display_function, \
            _batch_imports_setup

        try:
            # Restore hardware logger silent mode
            try:
                from shared.setup_filesystem import set_hardware_silent_mode

                set_hardware_silent_mode(False)
            except:
                pass  # Ignore if hardware logger not available

            # Restore directory
            if self._in_batch_context:
                os.chdir(self.original_cwd)
                self._in_batch_context = False

            # Clear cached resources
            _batch_mode = False
            _batch_icon_loader = None
            _batch_display_function = None
            _batch_imports_setup = False

            print("Batch mode stopped")

        except Exception as e:
            print(f"Error stopping batch mode: {e}")

    def shutdown(self):
        """Clean shutdown of pygame resources"""
        # Stop batch mode if active
        if _batch_mode:
            self.stop_batch_mode()

        # Don't shutdown global display, just clear our reference
        self.pygame_display = None

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup"""
        self.shutdown()

    # Batch mode context manager
    def batch_mode(self):
        """Context manager for batch mode operations"""
        return BatchModeContext(self)


class BatchModeContext:
    """Context manager for batch mode operations"""

    def __init__(self, renderer):
        self.renderer = renderer

    def __enter__(self):
        self.renderer.start_batch_mode()
        return self.renderer

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.renderer.stop_batch_mode()


# Convenience functions for one-off rendering
def render_weather_to_file(weather_data, output_file, **kwargs):
    """Convenience function to render weather data to file with auto-cleanup

    Args:
        weather_data: Display variables from weather_api.get_display_variables()
        output_file: Output PNG file path
        **kwargs: Additional arguments passed to render_weather_data_to_file

    Returns:
        Path to created file on success, None on failure
    """
    with WeatherImageRenderer() as renderer:
        return renderer.render_weather_data_to_file(weather_data, output_file, **kwargs)


def render_weather_to_bytes(weather_data, **kwargs):
    """Convenience function to render weather data to bytes with auto-cleanup

    Args:
        weather_data: Display variables from weather_api.get_display_variables()
        **kwargs: Additional arguments passed to render_weather_data_to_bytes

    Returns:
        PNG bytes on success, None on failure
    """
    with WeatherImageRenderer() as renderer:
        return renderer.render_weather_data_to_bytes(weather_data, **kwargs)


def measure_narrative_text_fit(weather_data):
    """Convenience function to measure narrative text fit with auto-cleanup

    Args:
        weather_data: Display variables from weather_api.get_display_variables()

    Returns:
        Dict with measurement info
    """
    with WeatherImageRenderer() as renderer:
        return renderer.measure_narrative_text(weather_data)
