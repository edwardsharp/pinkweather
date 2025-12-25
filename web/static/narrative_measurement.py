"""
Text measurement system for narrative optimization using PIL fonts
Measures text dimensions and line wrapping behavior identical to text_renderer.py
"""

import os
import re
import sys
from contextlib import contextmanager

from PIL import Image, ImageDraw, ImageFont

# Add 300x400 CIRCUITPY to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))  # web/static/
web_dir = os.path.dirname(current_dir)  # web/
project_root = os.path.dirname(web_dir)  # project root
circuitpy_400x300_path = os.path.join(project_root, "300x400", "CIRCUITPY")

# Constants from text_renderer
DISPLAY_WIDTH = 400
DISPLAY_HEIGHT = 300
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)


class NarrativeMeasurer:
    def __init__(self, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT):
        self.width = width
        self.height = height

        # Load fonts from CIRCUITPY directory
        self.fonts = self._load_fonts()

        # Calculate font metrics
        self._calculate_metrics()

    def _load_fonts(self):
        """Load actual PCF fonts used by the text renderer"""
        fonts = {}

        @contextmanager
        def change_to_circuitpy():
            """Context manager to change to CIRCUITPY directory for font loading"""
            current_dir = os.getcwd()
            try:
                os.chdir(circuitpy_400x300_path)
                yield
            finally:
                os.chdir(current_dir)

        try:
            # Import the actual font loading modules used by the renderer
            if circuitpy_400x300_path not in sys.path:
                sys.path.insert(0, circuitpy_400x300_path)

            from adafruit_bitmap_font import bitmap_font
            from adafruit_display_text import label

            # Load the actual PCF fonts in the correct directory
            with change_to_circuitpy():
                fonts["regular"] = bitmap_font.load_font("vollkorn20reg.pcf")
                fonts["bold"] = bitmap_font.load_font("vollkorn20black.pcf")
                fonts["italic"] = bitmap_font.load_font("vollkorn20italic.pcf")
                fonts["bold_italic"] = bitmap_font.load_font(
                    "vollkorn20blackitalic.pcf"
                )
                fonts["header"] = bitmap_font.load_font("hyperl20reg.pcf")
                fonts["header_bold"] = bitmap_font.load_font("hyperl20bold.pcf")

            print("Successfully loaded actual PCF fonts for measurement")

        except Exception as e:
            print(f"Warning: Could not load PCF fonts, falling back to defaults: {e}")
            # Fallback to default font for all styles
            default_font = ImageFont.load_default()
            fonts = {
                "regular": default_font,
                "bold": default_font,
                "italic": default_font,
                "bold_italic": default_font,
                "header": default_font,
                "header_bold": default_font,
            }

        return fonts

    def _calculate_metrics(self):
        """Calculate character and line metrics using actual font rendering"""
        try:
            # Import label for measuring actual rendered dimensions
            from adafruit_display_text import label

            # Use the same method as text_renderer for measuring
            test_label = label.Label(self.fonts["regular"], text="M", color=0x000000)
            self.char_width = (
                test_label.bounding_box[2] if test_label.bounding_box else 10
            )
            self.char_height = (
                test_label.bounding_box[3] if test_label.bounding_box else 16
            )
            self.line_height = int(
                self.char_height * 1.5
            )  # 50% spacing like text_renderer

            # Calculate average character width using actual font measurement
            avg_text = "abcdefghijklmnopqrstuvwxyz"
            avg_label = label.Label(
                self.fonts["regular"], text=avg_text, color=0x000000
            )
            avg_char_width = (
                (avg_label.bounding_box[2] / 26)
                if avg_label.bounding_box
                else self.char_width
            )

            self.chars_per_line = int(self.width // avg_char_width)
            self.lines_per_screen = self.height // self.line_height
            self.total_char_capacity = self.chars_per_line * self.lines_per_screen

            print(
                f"Font metrics: char={self.char_width}px, height={self.char_height}px, line={self.line_height}px"
            )

        except Exception as e:
            print(f"Warning: Font metrics calculation failed, using defaults: {e}")
            # Fallback to reasonable defaults
            self.char_width = 10
            self.char_height = 16
            self.line_height = 24
            self.chars_per_line = 40
            self.lines_per_screen = 12
            self.total_char_capacity = 480

    def get_font_for_style(self, style):
        """Get the appropriate font for a style"""
        return self.fonts.get(style, self.fonts["regular"])

    def measure_text_width(self, text, style="regular"):
        """Measure the actual width of text in pixels using actual font rendering"""
        if not text:
            return 0

        try:
            # Use the same label-based measurement as the renderer
            from adafruit_display_text import label

            font = self.get_font_for_style(style)
            test_label = label.Label(font, text=text, color=0x000000)
            width = (
                test_label.bounding_box[2]
                if test_label.bounding_box
                else len(text) * self.char_width
            )
            return width

        except Exception as e:
            # Fallback to estimated width
            return len(text) * self.char_width

    def should_break_word(self, word, remaining_width, style):
        """Determine if a word should be broken based on smart rules"""
        # Rule 0: Never break markup tags
        if word.startswith("<") or word.endswith(">") or "<" in word or ">" in word:
            return False

        # Rule 1: If word is shorter than 5 characters, don't break it
        if len(word) < 5:
            return False

        # Rule 2: If remaining space is very small (1-2 chars worth), don't break
        min_break_width = self.measure_text_width("ab-", style)
        if remaining_width < min_break_width:
            return False

        # Rule 3: Find where we would break
        for i in range(2, len(word) - 2):  # At least 2 chars before and after
            test_part = word[:i] + "-"
            test_width = self.measure_text_width(test_part, style)
            if test_width <= remaining_width:
                continue  # This part fits, keep trying longer
            else:
                return True  # Found a viable break point

        return False

    def parse_markup(self, text):
        """Parse markup tags and return list of (text, style, color) tuples"""
        # Simple regex-based parser for basic markup
        segments = []

        # Define tag patterns and their styles
        tag_patterns = [
            (r"<b>(.*?)</b>", "bold"),
            (r"<i>(.*?)</i>", "italic"),
            (r"<bi>(.*?)</bi>", "bold_italic"),
            (r"<h>(.*?)</h>", "header"),
            (r"<hb>(.*?)</hb>", "header_bold"),
            (r"<red>(.*?)</red>", "regular"),  # Special case for color
        ]

        # For now, simplified parsing - just extract plain text
        # TODO: Implement full markup parsing similar to text_renderer

        # Remove all markup tags for basic measurement
        clean_text = re.sub(r"<[^>]+>", "", text)
        segments.append((clean_text, "regular", BLACK))

        return segments

    def hard_wrap_text(self, segments):
        """Hard wrap text segments with smart word breaking"""
        wrapped_lines = []
        current_line = []
        current_width = 0

        for text_content, style, color in segments:
            # Handle newlines
            text_parts = text_content.split("\n")

            for part_idx, text_part in enumerate(text_parts):
                if part_idx > 0:  # Start new line for newlines
                    if current_line:
                        wrapped_lines.append(current_line)
                    current_line = []
                    current_width = 0

                if not text_part.strip():  # Skip empty parts
                    continue

                words = text_part.split(" ")

                for word_idx, word in enumerate(words):
                    if not word:  # Skip empty words
                        continue

                    # Add space before word (except at line start)
                    if current_width > 0:
                        space_width = self.measure_text_width(" ", style)
                        if current_width + space_width <= self.width:
                            current_line.append((" ", style, color))
                            current_width += space_width
                        else:
                            # Start new line if space doesn't fit
                            wrapped_lines.append(current_line)
                            current_line = []
                            current_width = 0

                    # Process the word
                    word_width = self.measure_text_width(word, style)

                    # If word fits on current line, add it
                    if current_width + word_width <= self.width:
                        current_line.append((word, style, color))
                        current_width += word_width
                    else:
                        # Word doesn't fit - decide whether to break or wrap
                        is_markup = (
                            "<" in word
                            or ">" in word
                            or word.startswith("<")
                            or word.endswith(">")
                        )

                        should_break = not is_markup and self.should_break_word(
                            word, self.width - current_width, style
                        )

                        if (
                            should_break and current_line
                        ):  # Only break if line has content
                            # Break the word
                            remaining_width = self.width - current_width

                            best_break = 2
                            for i in range(2, len(word) - 2):
                                test_part = word[:i] + "-"
                                test_width = self.measure_text_width(test_part, style)
                                if test_width <= remaining_width:
                                    best_break = i
                                else:
                                    break

                            # Add first part with hyphen
                            first_part = word[:best_break] + "-"
                            current_line.append((first_part, style, color))
                            wrapped_lines.append(current_line)

                            # Continue with remaining part on new line
                            remaining_word = word[best_break:]
                            current_line = [(remaining_word, style, color)]
                            current_width = self.measure_text_width(
                                remaining_word, style
                            )
                        else:
                            # Move word to next line
                            if current_line:
                                wrapped_lines.append(current_line)
                            current_line = [(word, style, color)]
                            current_width = word_width

        # Add final line if not empty
        if current_line:
            wrapped_lines.append(current_line)

        return wrapped_lines

    def measure_narrative_text(self, narrative):
        """
        Measure narrative text and return comprehensive metrics

        Returns dict with:
        - text_width_px: maximum line width in pixels
        - text_height_px: total height in pixels
        - line_count: number of lines after wrapping
        - fits_display: boolean if text fits within display bounds
        - char_count: total character count
        - overflow_lines: number of lines that overflow
        """
        # Parse markup
        segments = self.parse_markup(narrative)

        # Hard wrap the text
        wrapped_lines = self.hard_wrap_text(segments)

        # Calculate metrics
        max_width = 0
        total_height = len(wrapped_lines) * self.line_height

        # Calculate actual width of each line
        for line_segments in wrapped_lines:
            line_width = 0
            for text_content, style, color in line_segments:
                line_width += self.measure_text_width(text_content, style)
            max_width = max(max_width, line_width)

        # Check if text fits display
        fits_width = max_width <= self.width
        fits_height = total_height <= self.height
        fits_display = fits_width and fits_height

        # Calculate overflow
        max_lines_that_fit = self.height // self.line_height
        overflow_lines = max(0, len(wrapped_lines) - max_lines_that_fit)

        # Character count (excluding markup)
        plain_text = re.sub(r"<[^>]+>", "", narrative)
        char_count = len(plain_text)

        return {
            "text_width_px": max_width,
            "text_height_px": total_height,
            "line_count": len(wrapped_lines),
            "fits_display": fits_display,
            "char_count": char_count,
            "overflow_lines": overflow_lines,
            "max_lines_that_fit": max_lines_that_fit,
        }


def fits_display(text_metrics, display_bounds=(400, 300)):
    """Check if text fits within display constraints"""
    width_limit, height_limit = display_bounds
    return (
        text_metrics["text_width_px"] <= width_limit
        and text_metrics["text_height_px"] <= height_limit
    )


def test_measurement():
    """Test the measurement system with sample text"""
    measurer = NarrativeMeasurer()

    test_texts = [
        "Simple test text",
        "This is a longer piece of text that should wrap across multiple lines to test the wrapping behavior",
        "<b>Bold text</b> and <i>italic text</i> mixed together",
        "Very long single word: supercalifragilisticexpialidocious should break with hyphenation",
    ]

    for text in test_texts:
        print(f"\nTesting: {text[:50]}...")
        metrics = measurer.measure_narrative_text(text)
        print(f"  Width: {metrics['text_width_px']}px")
        print(f"  Height: {metrics['text_height_px']}px")
        print(f"  Lines: {metrics['line_count']}")
        print(f"  Fits: {metrics['fits_display']}")
        print(f"  Chars: {metrics['char_count']}")


if __name__ == "__main__":
    test_measurement()
