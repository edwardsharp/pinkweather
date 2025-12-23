"""
Logging module for pinkweather hardware
Logs to SD card when available, always prints to console
Automatically truncates log file to maintain reasonable size
"""

import os
import time

# Global logging configuration
LOG_FILE_PATH = "/sd/log.txt"
MAX_LOG_LINES = 100000
TRUNCATE_TO_LINES = 80000  # When we hit max, truncate to this many lines
_sd_available = None


def _check_sd_availability():
    """Check if SD card is available and writable"""
    global _sd_available
    if _sd_available is None:
        try:
            # Try to stat the SD card directory
            os.stat("/sd")
            # Try a quick write test
            test_file = "/sd/.log_test"
            with open(test_file, "w") as f:
                f.write("test")
            os.remove(test_file)
            _sd_available = True
        except (OSError, Exception):
            _sd_available = False
    return _sd_available


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


def _write_to_sd(message):
    """Write message to SD card log file"""
    if not _check_sd_availability():
        return False

    try:
        # Append message to log file
        with open(LOG_FILE_PATH, "a") as f:
            f.write(message + "\n")
        return True
    except Exception as e:
        # Print to console if SD write fails, but don't recurse
        print(f"SD log write failed: {e}")
        return False


def _truncate_log_if_needed():
    """Truncate log file if it exceeds maximum lines"""
    if not _check_sd_availability():
        return

    try:
        # Check if log file exists
        try:
            os.stat(LOG_FILE_PATH)
        except OSError:
            # File doesn't exist, nothing to truncate
            return

        # Count lines in log file
        line_count = 0
        with open(LOG_FILE_PATH, "r") as f:
            for _ in f:
                line_count += 1

        # If we exceed max lines, truncate to keep last TRUNCATE_TO_LINES
        if line_count > MAX_LOG_LINES:
            print(f"Truncating log file: {line_count} -> {TRUNCATE_TO_LINES} lines")

            # Read the last TRUNCATE_TO_LINES lines
            with open(LOG_FILE_PATH, "r") as f:
                lines = f.readlines()

            # Keep only the last TRUNCATE_TO_LINES
            lines_to_keep = lines[-TRUNCATE_TO_LINES:]

            # Write back to file
            with open(LOG_FILE_PATH, "w") as f:
                f.writelines(lines_to_keep)

            # Add truncation marker
            with open(LOG_FILE_PATH, "a") as f:
                timestamp = _get_timestamp()
                f.write(
                    f"{timestamp} LOG: Truncated from {line_count} to {len(lines_to_keep)} lines\n"
                )

    except Exception as e:
        print(f"Log truncation failed: {e}")


def log(message):
    """Main logging function - replaces print() calls

    Args:
        message: String message to log
    """
    # Get timestamp for both console and file
    timestamp = _get_timestamp()
    timestamped_message = f"{timestamp} {message}"

    # Print to console with timestamp (same format as log file)
    print(timestamped_message)

    # Try to write to SD card with same timestamp
    if _check_sd_availability():
        # Write to SD card
        if _write_to_sd(timestamped_message):
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


def log_warning(message):
    """Log warning message with WARNING prefix

    Args:
        message: Warning message to log
    """
    log(f"WARNING: {message}")


def log_debug(message):
    """Log debug message with DEBUG prefix

    Args:
        message: Debug message to log
    """
    log(f"DEBUG: {message}")


def log_info(message):
    """Log info message with INFO prefix

    Args:
        message: Info message to log
    """
    log(f"INFO: {message}")


def force_truncate_log():
    """Force log file truncation (for testing or maintenance)"""
    _truncate_log_if_needed()


def get_log_stats():
    """Get statistics about the current log file

    Returns:
        dict: Statistics including line count, file size, etc.
        None: If SD card not available or error
    """
    if not _check_sd_availability():
        return None

    try:
        # Get file stats
        stat_result = os.stat(LOG_FILE_PATH)
        file_size = stat_result[6]  # Size in bytes

        # Count lines
        line_count = 0
        with open(LOG_FILE_PATH, "r") as f:
            for _ in f:
                line_count += 1

        return {
            "line_count": line_count,
            "file_size_bytes": file_size,
            "file_size_kb": file_size / 1024,
            "max_lines": MAX_LOG_LINES,
            "truncate_threshold": TRUNCATE_TO_LINES,
            "sd_available": True,
        }
    except Exception as e:
        log_error(f"Failed to get log stats: {e}")
        return None


# Test function
def test_logger():
    """Test the logger functionality"""
    log("Logger test started")
    log_info("This is an info message")
    log_warning("This is a warning message")
    log_error("This is an error message")
    log_debug("This is a debug message")

    stats = get_log_stats()
    if stats:
        log(f"Log stats: {stats['line_count']} lines, {stats['file_size_kb']:.1f} KB")
    else:
        log("Could not retrieve log stats (SD card not available)")

    log("Logger test completed")


if __name__ == "__main__":
    test_logger()
