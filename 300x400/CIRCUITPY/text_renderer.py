"""
Core text rendering functionality with markup support and hard word wrapping
"""

import displayio
import terminalio
from adafruit_display_text import label
from adafruit_bitmap_font import bitmap_font
import re

# Display constants
DISPLAY_WIDTH = 400
DISPLAY_HEIGHT = 300
BLACK = 0x000000
WHITE = 0xFFFFFF
RED = 0xFF0000


class TextRenderer:
    def __init__(self, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT):
        self.width = width
        self.height = height

        # Load fonts with fallback
        try:
            # Vollkorn fonts for body text
            self.font_regular = bitmap_font.load_font("vollkorn20reg.pcf")
            self.font_bold = bitmap_font.load_font("vollkorn20black.pcf")
            self.font_italic = bitmap_font.load_font("vollkorn20italic.pcf")
            self.font_bold_italic = bitmap_font.load_font("vollkorn20blackitalic.pcf")

            # Atkinson Hyperlegible fonts for headers
            self.header_font_regular = bitmap_font.load_font("hyperl20reg.pcf")
            self.header_font_bold = bitmap_font.load_font("hyperl20bold.pcf")
        except Exception as e:
            # Fallback to terminal font
            self.font_regular = terminalio.FONT
            self.font_bold = terminalio.FONT
            self.font_italic = terminalio.FONT
            self.font_bold_italic = terminalio.FONT
            self.header_font_regular = terminalio.FONT
            self.header_font_bold = terminalio.FONT

        # Get font metrics
        test_label = label.Label(self.font_regular, text="M", color=BLACK)
        self.char_width = test_label.bounding_box[2] if test_label.bounding_box else 10
        self.char_height = test_label.bounding_box[3] if test_label.bounding_box else 16
        self.line_height = int(self.char_height * 1.5)  # 50% spacing between lines

        # Calculate approximate capacity (for estimates only, since font is not monospaced)
        avg_char_width = self.measure_text_width("abcdefghijklmnopqrstuvwxyz", 'regular') / 26
        self.chars_per_line = int(self.width // avg_char_width)
        self.lines_per_screen = self.height // self.line_height
        self.total_char_capacity = self.chars_per_line * self.lines_per_screen

    def get_font_for_style(self, style):
        """Get the appropriate font for a style"""
        if style == 'bold':
            return self.font_bold
        elif style == 'italic':
            return self.font_italic
        elif style == 'bold_italic':
            return self.font_bold_italic
        elif style == 'header':
            return self.header_font_regular
        elif style == 'header_bold':
            return self.header_font_bold
        else:
            return self.font_regular

    def measure_text_width(self, text, style):
        """Measure the actual width of text in pixels by rendering it"""
        if not text:
            return 0
        font = self.get_font_for_style(style)
        test_label = label.Label(font, text=text, color=BLACK)
        return test_label.bounding_box[2] if test_label.bounding_box else len(text) * self.char_width

    def should_break_word(self, word, remaining_width, style):
        """Determine if a word should be broken based on smart rules"""
        word_width = self.measure_text_width(word, style)

        # Rule 1: If word is shorter than 5 characters, don't break it
        if len(word) < 5:
            return False

        # Rule 2: If remaining space is very small (1-2 chars worth), don't break
        min_break_width = self.measure_text_width('ab-', style)
        if remaining_width < min_break_width:
            return False

        # Rule 3: If breaking would leave only 1-2 chars on next line, don't break
        hyphen_width = self.measure_text_width('-', style)

        # Find where we would break
        for i in range(2, len(word) - 2):  # At least 2 chars before and after
            test_part = word[:i] + '-'
            test_width = self.measure_text_width(test_part, style)

            if test_width <= remaining_width:
                remaining_chars = len(word) - i
                if remaining_chars >= 3:  # At least 3 chars left for next line
                    return True

        return False

    def parse_markup(self, text):
        """Parse markup tags and return list of (text, style, color) tuples"""
        segments = []
        patterns = {
            'bi': (r'<bi>(.*?)</bi>', 'bold_italic'),
            'b': (r'<b>(.*?)</b>', 'bold'),
            'i': (r'<i>(.*?)</i>', 'italic'),
            'red': (r'<red>(.*?)</red>', 'red'),
            'h': (r'<h>(.*?)</h>', 'header'),
            'hb': (r'<hb>(.*?)</hb>', 'header_bold'),
        }

        current_pos = 0
        while current_pos < len(text):
            # Find the next markup tag
            next_match = None
            next_pos = len(text)
            next_style = None

            for style_name, (pattern, style) in patterns.items():
                match = re.search(pattern, text[current_pos:])
                if match and current_pos + match.start() < next_pos:
                    next_match = match
                    next_pos = current_pos + match.start()
                    next_style = style

            # Add text before the next tag (if any)
            if next_pos > current_pos:
                plain_text = text[current_pos:next_pos]
                if plain_text:
                    segments.append((plain_text, 'regular', BLACK))

            # Add the styled text
            if next_match:
                styled_text = next_match.group(1)
                color = RED if next_style == 'red' else BLACK
                font_style = next_style if next_style != 'red' else 'regular'
                segments.append((styled_text, font_style, color))
                current_pos = next_pos + len(next_match.group(0))
            else:
                # No more matches, move to end to avoid duplicate processing
                current_pos = len(text)
                break

        # Add any remaining text (this should only execute if we stopped mid-text due to matches)
        if current_pos < len(text):
            remaining_text = text[current_pos:]
            if remaining_text:
                segments.append((remaining_text, 'regular', BLACK))

        return segments

    def hard_wrap_text(self, segments):
        """Hard wrap text segments with smart word breaking and hyphenation rules"""
        wrapped_lines = []
        current_line = []
        current_width = 0

        for text_content, style, color in segments:
            # Handle newlines
            text_parts = text_content.split('\n')

            for part_idx, text_part in enumerate(text_parts):
                if part_idx > 0:  # Start new line for newlines
                    if current_line:
                        wrapped_lines.append(current_line)
                    current_line = []
                    current_width = 0

                if not text_part.strip():  # Skip empty parts
                    continue

                words = text_part.split(' ')

                for word_idx, word in enumerate(words):
                    if not word:  # Skip empty words
                        continue

                    # Add space before word (except at line start)
                    if current_width > 0:
                        space_width = self.measure_text_width(' ', style)
                        if current_width + space_width <= self.width:
                            current_line.append((' ', style, color))
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
                        should_break = self.should_break_word(word, self.width - current_width, style)

                        if should_break and current_line:  # Only break if line has content
                            # Break the word
                            remaining_width = self.width - current_width
                            hyphen_width = self.measure_text_width('-', style)

                            best_break = 2
                            for i in range(2, len(word) - 2):
                                test_part = word[:i] + '-'
                                test_width = self.measure_text_width(test_part, style)
                                if test_width <= remaining_width:
                                    best_break = i
                                else:
                                    break

                            # Add first part with hyphen
                            first_part = word[:best_break] + '-'
                            current_line.append((first_part, style, color))
                            wrapped_lines.append(current_line)

                            # Continue with remaining part on new line
                            remaining_word = word[best_break:]
                            current_line = [(remaining_word, style, color)]
                            current_width = self.measure_text_width(remaining_word, style)
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

    def render_text(self, markup_text):
        """Render marked-up text to a display group"""
        # Parse markup
        segments = self.parse_markup(markup_text)

        # Hard wrap the text
        wrapped_lines = self.hard_wrap_text(segments)

        # Create display group
        group = displayio.Group()

        # Create white background
        background_bitmap = displayio.Bitmap(self.width, self.height, 1)
        background_palette = displayio.Palette(1)
        background_palette[0] = WHITE
        background_sprite = displayio.TileGrid(background_bitmap, pixel_shader=background_palette)
        group.append(background_sprite)

        # Use proper font-based line height
        y_position = self.line_height  # Start at first line height

        for line_segments in wrapped_lines:
            if y_position > self.height - (self.line_height // 2):
                break  # Don't render beyond screen with smaller margin

            x_position = 0

            for text_content, style, color in line_segments:
                if not text_content.strip():  # Skip whitespace-only segments at line start
                    if x_position == 0:
                        continue

                font = self.get_font_for_style(style)
                text_label = label.Label(font, text=text_content, color=color)
                text_label.x = x_position
                text_label.y = y_position

                group.append(text_label)

                # Update x position for next segment
                if text_label.bounding_box:
                    x_position += text_label.bounding_box[2]
                else:
                    x_position += len(text_content) * self.char_width

            y_position += self.line_height

        return group

    def render_text_no_background(self, markup_text):
        """Render marked-up text to a display group without white background"""
        # Parse markup
        segments = self.parse_markup(markup_text)

        # Hard wrap the text
        wrapped_lines = self.hard_wrap_text(segments)

        # Create display group (no background)
        group = displayio.Group()

        # Use proper font-based line height
        y_position = self.line_height  # Start at first line height

        for line_segments in wrapped_lines:
            if y_position > self.height - (self.line_height // 2):
                break  # Don't render beyond screen with smaller margin

            x_position = 0

            for text_content, style, color in line_segments:
                if not text_content.strip():  # Skip whitespace-only segments at line start
                    if x_position == 0:
                        continue

                font = self.get_font_for_style(style)
                text_label = label.Label(font, text=text_content, color=color)
                text_label.x = x_position
                text_label.y = y_position

                group.append(text_label)

                # Update x position for next segment
                if text_label.bounding_box:
                    x_position += text_label.bounding_box[2]
                else:
                    x_position += len(text_content) * self.char_width

            y_position += self.line_height

        return group


def get_text_capacity():
    """Get approximate text capacity for the display"""
    renderer = TextRenderer()
    return {
        'chars_per_line': renderer.chars_per_line,
        'lines_per_screen': renderer.lines_per_screen,
        'total_capacity': renderer.total_char_capacity,
        'char_width': renderer.char_width,
        'char_height': renderer.char_height,
        'line_height': renderer.line_height
    }
