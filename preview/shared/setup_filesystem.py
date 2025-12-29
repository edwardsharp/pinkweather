"""
Preview filesystem setup - inject filesystem dependencies for preview system
"""

import sys
from pathlib import Path

from shared.filesystem import FileSystem as PreviewFileSystem


def setup_preview_filesystem():
    """Setup filesystem dependencies for preview system"""
    # Create preview filesystem
    filesystem = PreviewFileSystem()

    # Add hardware path for importing shared modules
    hardware_path = Path(__file__).parent.parent / "300x400" / "CIRCUITPY"
    sys.path.insert(0, str(hardware_path))

    # Inject into shared modules
    from utils.logger import set_filesystem as set_logger_filesystem
    from weather.weather_history import set_filesystem as set_weather_history_filesystem
    from weather.weather_persistence import (
        set_filesystem as set_weather_persistence_filesystem,
    )

    set_logger_filesystem(filesystem)
    set_weather_persistence_filesystem(filesystem)
    set_weather_history_filesystem(filesystem)

    return filesystem


def set_hardware_silent_mode(silent=True):
    """Set silent mode for hardware logger modules

    Args:
        silent (bool): If True, suppress hardware module log output
    """
    try:
        # Add hardware path for importing
        hardware_path = Path(__file__).parent.parent / "300x400" / "CIRCUITPY"
        if str(hardware_path) not in sys.path:
            sys.path.insert(0, str(hardware_path))

        # Set silent mode in hardware logger
        from utils.logger import set_silent_mode as set_hardware_silent_mode

        set_hardware_silent_mode(silent)

    except Exception as e:
        # If hardware logger import fails, silently continue
        # (this might happen if hardware modules aren't available)
        pass


if __name__ == "__main__":
    # Test the setup
    filesystem = setup_preview_filesystem()

    from utils.logger import log, test_logger

    print("Testing preview filesystem setup...")
    test_logger()
    print("Preview filesystem setup complete!")
