"""
Logging module for pinkweather
Accepts injected filesystem for dependency injection pattern
Logs to filesystem when available, always prints to console
"""

import time

# Global logging configuration
_filesystem = None
_silent_mode = False  # When True, suppress all print() output
LOG_FILENAME = "log.txt"
MAX_LOG_LINES = 100000


def set_filesystem(filesystem):
    """Set the filesystem to use for logging (dependency injection)"""
    global _filesystem
    _filesystem = filesystem


def _filesystem_available():
    """Check if filesystem is available"""
    return _filesystem is not None and _filesystem.is_available()


def _get_timestamp():
    """Get current timestamp in readable format (time since boot)"""
    try:
        # Get current time in seconds since boot
        current_time = time.monotonic()

        # Format as uptime showing days, hours, minutes, and always seconds
        days = int(current_time // 86400)
        hours = int((current_time % 86400) // 3600)
        minutes = int((current_time % 3600) // 60)
        seconds = current_time % 60  # Keep fractional seconds for precision

        if days > 0:
            return f"[{days}d{hours:02d}h{minutes:02d}m{seconds:05.2f}s]"
        elif hours > 0:
            return f"[{hours}h{minutes:02d}m{seconds:05.2f}s]"
        elif minutes > 0:
            return f"[{minutes}m{seconds:05.2f}s]"
        else:
            return f"[{seconds:.2f}s]"
    except:
        return "[--:--s]"


def _write_to_filesystem(message):
    """Write message to filesystem log file"""
    if not _filesystem_available():
        return False

    try:
        return _filesystem.append_text(LOG_FILENAME, message)
    except Exception as e:
        # Print to console if filesystem write fails, but don't recurse (respect silent mode)
        if not _silent_mode:
            print(f"Filesystem log write failed: {e}")
        return False


def _truncate_log_if_needed():
    """Truncate log file if it exceeds maximum lines"""
    if not _filesystem_available():
        return

    try:
        # Count lines in log file
        line_count = _filesystem.count_lines(LOG_FILENAME)

        # If we exceed max lines, truncate to keep last 80% of max
        if line_count > MAX_LOG_LINES:
            keep_lines = int(MAX_LOG_LINES * 0.8)
            if not _silent_mode:
                print(f"Truncating log file: {line_count} -> {keep_lines} lines")

            # Truncate the file
            if _filesystem.truncate_file(LOG_FILENAME, keep_lines):
                # Add truncation marker
                timestamp = _get_timestamp()
                _filesystem.append_text(
                    LOG_FILENAME,
                    f"{timestamp} LOG: Truncated from {line_count} to {keep_lines} lines",
                )
            else:
                if not _silent_mode:
                    print("Log truncation failed")

    except Exception as e:
        if not _silent_mode:
            print(f"Log truncation failed: {e}")


def log(message):
    """Main logging function - replaces print() calls

    Args:
        message: String message to log
    """
    # In silent mode, do nothing at all
    if _silent_mode:
        return

    # Get timestamp for both console and file
    timestamp = _get_timestamp()
    timestamped_message = f"{timestamp} {message}"

    # Print to console with timestamp
    print(timestamped_message)

    # Try to write to filesystem with same timestamp
    if _filesystem_available():
        if _write_to_filesystem(timestamped_message):
            # Occasionally check if we need to truncate (every ~100 calls)
            # Use a simple modulo check based on time to avoid counting calls
            if int(time.monotonic()) % 100 == 0:
                _truncate_log_if_needed()


def log_error(message):
    """Log error message with ERROR prefix

    Args:
        message: Error message to log
    """
    log(f"ERROR: {message}")


def force_truncate_log():
    """Force log file truncation (for testing or maintenance)"""
    _truncate_log_if_needed()


def get_log_stats():
    """Get statistics about the current log file

    Returns:
        dict: Statistics about log file or None if filesystem unavailable
    """
    if not _filesystem_available():
        return None

    try:
        line_count = _filesystem.count_lines(LOG_FILENAME)
        return {
            "line_count": line_count,
            "max_lines": MAX_LOG_LINES,
            "filesystem_available": True,
            "log_filename": LOG_FILENAME,
        }
    except Exception as e:
        log_error(f"Failed to get log stats: {e}")
        return None


def test_logger():
    """Test the logger functionality"""
    log("Logger test started")
    log_error("This is an error message")

    stats = get_log_stats()
    if stats:
        log(f"Log stats: {stats['line_count']} lines (max: {stats['max_lines']})")
    else:
        log("Could not retrieve log stats (filesystem not available)")

    log("Logger test completed")


def set_silent_mode(silent):
    """Enable or disable silent mode for logger

    Args:
        silent (bool): If True, suppress all print() output from logger
    """
    global _silent_mode
    _silent_mode = silent


def is_silent_mode():
    """Check if logger is in silent mode

    Returns:
        bool: True if silent mode is enabled
    """
    return _silent_mode


if __name__ == "__main__":
    test_logger()
