"""
Centralized preview system initialization
Handles all mocking, path setup, and module configuration in one place
"""

import os
import sys
from pathlib import Path


class PreviewInitializer:
    """Centralized initialization for preview system"""

    def __init__(self):
        self.preview_dir = Path(__file__).parent.parent
        self.hardware_path = self.preview_dir.parent / "300x400" / "CIRCUITPY"
        self.original_cwd = os.getcwd()
        self.initialized = False

    def setup_environment(self):
        """Setup environment variables for blinka/pygame"""
        if not self.initialized:
            # Force generic platform for blinka
            os.environ["BLINKA_FORCEBOARD"] = "GENERIC_LINUX_PC"
            os.environ["BLINKA_FORCECHIP"] = "GENERIC_X86"
            os.environ["DISPLAYIO_NO_BACKGROUND"] = "1"

    def setup_mocks(self):
        """Setup basic mocks that preview/config.py doesn't handle"""
        if not self.initialized:
            # Only mock modules that preview/config.py doesn't already handle

            # WiFi mocks
            class MockWifi:
                class Radio:
                    def connect(self, ssid, password):
                        pass

                    @property
                    def connected(self):
                        return True

                radio = Radio()

            # Sensor mocks
            class MockSensor:
                @property
                def temperature(self):
                    return 21.5

                @property
                def relative_humidity(self):
                    return 65.0

            # Install basic mocks (preview/config.py handles board mocking)
            if "wifi" not in sys.modules:
                sys.modules["wifi"] = MockWifi()
            if "adafruit_hdc302x" not in sys.modules:
                sys.modules["adafruit_hdc302x"] = MockSensor()

    def setup_paths(self):
        """Setup import paths for hardware modules"""
        if str(self.hardware_path) not in sys.path:
            sys.path.insert(0, str(self.hardware_path))

    def setup_config(self):
        """Setup config module with preview config"""
        if not self.initialized:
            # Import preview config BEFORE adding hardware path to avoid conflicts
            preview_config_path = self.preview_dir / "config.py"
            if preview_config_path.exists():
                # Add preview directory to path FIRST
                if str(self.preview_dir) not in sys.path:
                    sys.path.insert(0, str(self.preview_dir))

                # Import preview config (this should load the preview version with mocks)
                import config as preview_config

                # Also mock the board module directly for safety
                sys.modules["board"] = preview_config.board

                # Replace hardware config module
                sys.modules["config"] = preview_config
            else:
                print(f"Warning: Preview config not found at {preview_config_path}")

    def setup_filesystem(self):
        """Setup filesystem dependencies"""
        if not self.initialized:
            # Import setup_filesystem from preview directory
            setup_filesystem_path = self.preview_dir / "setup_filesystem.py"
            if setup_filesystem_path.exists():
                import importlib.util

                spec = importlib.util.spec_from_file_location(
                    "setup_filesystem", setup_filesystem_path
                )
                setup_filesystem_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(setup_filesystem_module)
                setup_filesystem_module.setup_preview_filesystem()

    def change_to_hardware_dir(self):
        """Change to hardware directory for font/resource loading"""
        os.chdir(self.hardware_path)

    def restore_directory(self):
        """Restore original working directory"""
        os.chdir(self.original_cwd)

    def initialize_all(self):
        """Complete initialization sequence"""
        if self.initialized:
            return

        self.setup_environment()
        self.setup_mocks()
        self.setup_config()  # Setup config BEFORE paths to avoid import conflicts
        self.setup_paths()
        self.setup_filesystem()
        self.initialized = True

    def __enter__(self):
        """Context manager entry - initialize and change directory"""
        self.initialize_all()
        self.change_to_hardware_dir()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - restore directory"""
        self.restore_directory()


# Global instance for convenience
_initializer = None


def get_initializer():
    """Get global initializer instance"""
    global _initializer
    if _initializer is None:
        _initializer = PreviewInitializer()
    return _initializer


def initialize_preview():
    """Convenience function to initialize preview system"""
    initializer = get_initializer()
    initializer.initialize_all()
    return initializer


def with_hardware_context(func):
    """Decorator to run function in hardware directory context"""

    def wrapper(*args, **kwargs):
        with get_initializer():
            return func(*args, **kwargs)

    return wrapper


# Convenience functions
def ensure_preview_initialized():
    """Ensure preview system is initialized"""
    get_initializer().initialize_all()


def hardware_context():
    """Context manager for hardware directory operations"""
    return get_initializer()
