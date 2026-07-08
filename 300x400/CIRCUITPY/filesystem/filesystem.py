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

    def cleanup_tmp_files(self):
        """Remove any .tmp files left behind by a previously interrupted write.

        Should be called once at boot before any writes. Returns the number
        of files removed.
        """
        if not self.is_available():
            return 0

        removed = 0
        try:
            for entry in os.listdir(self.base_path):
                if entry.endswith(".tmp"):
                    try:
                        os.remove(f"{self.base_path}/{entry}")
                        removed += 1
                    except OSError:
                        pass
        except Exception:
            pass
        return removed

    def append_text(self, filename, content):
        """Append text to file (for logging).

        Appending preserves existing data on a partial write, so no temp-file
        pattern is needed here.
        """
        if not self.is_available():
            return False

        try:
            with open(f"{self.base_path}/{filename}", "a") as f:
                f.write(content + "\n")
            return True
        except:
            return False

    def write_json(self, filename, data):
        """Write JSON data atomically using a temp file.

        Writes the full payload to <filename>.tmp first, then renames it over
        the real file. A power cut during the write leaves the original file
        intact; any orphaned .tmp is cleaned up by cleanup_tmp_files() on the
        next boot.
        """
        if not self.is_available():
            return False

        final_path = f"{self.base_path}/{filename}"
        tmp_path = f"{self.base_path}/{filename}.tmp"

        try:
            with open(tmp_path, "w") as f:
                json.dump(data, f)

            # Rename over the real file. Some FAT drivers won't overwrite an
            # existing destination, so fall back to remove + rename if needed.
            try:
                os.rename(tmp_path, final_path)
            except OSError:
                os.remove(final_path)
                os.rename(tmp_path, final_path)

            return True
        except Exception:
            # Clean up the orphaned tmp so the next boot doesn't see stale data
            try:
                os.remove(tmp_path)
            except OSError:
                pass
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
        """Keep only the last N lines of a text file, written atomically.

        Reads the existing file, writes the kept lines to <filename>.tmp,
        then renames it over the original. A power cut during the write
        leaves the original file intact.
        """
        if not self.is_available():
            return False

        final_path = f"{self.base_path}/{filename}"
        tmp_path = f"{self.base_path}/{filename}.tmp"

        try:
            with open(final_path, "r") as f:
                lines = f.readlines()

            if len(lines) <= keep_lines:
                return True  # Nothing to do

            kept_lines = lines[-keep_lines:]

            with open(tmp_path, "w") as f:
                f.writelines(kept_lines)

            try:
                os.rename(tmp_path, final_path)
            except OSError:
                os.remove(final_path)
                os.rename(tmp_path, final_path)

            return True
        except Exception:
            try:
                os.remove(tmp_path)
            except OSError:
                pass
            return False
