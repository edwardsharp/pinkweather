"""
Preview filesystem abstraction for local disk operations
Used for dependency injection pattern - preview uses local disk instead of SD card
"""

import json
from pathlib import Path


class FileSystem:
    """Simple preview filesystem - just the essentials"""

    def __init__(self):
        # Store files in preview/.cache/
        self.base_path = Path(__file__).parent / ".cache"
        self.base_path.mkdir(exist_ok=True)

    def is_available(self):
        """Always available for preview"""
        return True

    def append_text(self, filename, content):
        """Append text to file (for logging)"""
        try:
            (self.base_path / filename).write_text(
                (self.base_path / filename).read_text() + content + "\n"
                if (self.base_path / filename).exists()
                else content + "\n"
            )
            return True
        except:
            return False

    def write_json(self, filename, data):
        """Write JSON data (for weather persistence)"""
        try:
            with open(self.base_path / filename, "w") as f:
                json.dump(data, f)
            return True
        except:
            return False

    def read_json(self, filename):
        """Read JSON data"""
        try:
            with open(self.base_path / filename, "r") as f:
                return json.load(f)
        except:
            return None

    def count_lines(self, filename):
        """Count lines in text file"""
        try:
            file_path = self.base_path / filename
            if not file_path.exists():
                return 0
            return len(file_path.read_text().splitlines())
        except:
            return 0

    def truncate_file(self, filename, keep_lines):
        """Keep only the last N lines of a text file"""
        try:
            file_path = self.base_path / filename
            if not file_path.exists():
                return False

            content = file_path.read_text()
            lines = content.splitlines()

            if len(lines) <= keep_lines:
                return True  # No truncation needed

            # Keep last N lines
            kept_lines = lines[-keep_lines:]
            new_content = "\n".join(kept_lines) + "\n"

            file_path.write_text(new_content)
            return True
        except:
            return False
