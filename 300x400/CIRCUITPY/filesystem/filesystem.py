"""
Hardware filesystem abstraction for SD card operations
Used for dependency injection pattern - hardware uses SD card
"""

import json
import os


class FileSystem:
    """Simple hardware filesystem - SD card operations"""

    def __init__(self):
        # SD card mounted at /sd
        self.base_path = "/sd"

    def is_available(self):
        """Check if SD card is available"""
        try:
            os.stat(self.base_path)
            return True
        except:
            return False

    def append_text(self, filename, content):
        """Append text to file (for logging)"""
        if not self.is_available():
            return False

        try:
            with open(f"{self.base_path}/{filename}", "a") as f:
                f.write(content + "\n")
            return True
        except:
            return False

    def write_json(self, filename, data):
        """Write JSON data (for weather persistence)"""
        if not self.is_available():
            return False

        try:
            with open(f"{self.base_path}/{filename}", "w") as f:
                json.dump(data, f)
            return True
        except:
            return False

    def read_json(self, filename):
        """Read JSON data"""
        if not self.is_available():
            return None

        try:
            with open(f"{self.base_path}/{filename}", "r") as f:
                return json.load(f)
        except:
            return None

    def count_lines(self, filename):
        """Count lines in text file"""
        if not self.is_available():
            return 0

        try:
            with open(f"{self.base_path}/{filename}", "r") as f:
                return sum(1 for _ in f)
        except:
            return 0

    def truncate_file(self, filename, keep_lines):
        """Keep only the last N lines of a text file"""
        if not self.is_available():
            return False

        try:
            # Read all lines
            with open(f"{self.base_path}/{filename}", "r") as f:
                lines = f.readlines()

            if len(lines) <= keep_lines:
                return True  # No truncation needed

            # Keep last N lines
            kept_lines = lines[-keep_lines:]

            # Write back
            with open(f"{self.base_path}/{filename}", "w") as f:
                f.writelines(kept_lines)

            return True
        except:
            return False
