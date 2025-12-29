"""
Centralized logger for web modules
Provides simple logging functions with global silent mode control
"""

# Global configuration
_silent_mode = False


def set_silent_mode(silent=True):
    """Enable or disable silent mode globally

    Args:
        silent (bool): If True, suppress all log output
    """
    global _silent_mode
    _silent_mode = silent


def is_silent():
    """Check if logger is in silent mode

    Returns:
        bool: True if silent mode is enabled
    """
    return _silent_mode


def log(message):
    """Log message

    Args:
        message: Message to log
    """
    if not _silent_mode:
        print(message)


def log_error(message):
    """Log error message with ERROR prefix

    Args:
        message: Error message to log
    """
    if not _silent_mode:
        print(f"ERROR: {message}")
