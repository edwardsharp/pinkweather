"""
Display rendering for 400x300 e-ink display
Handles text layout with markup support and hard word wrapping
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

# Icon positions (shared between hardware and web renderer)
WEATHER_ICON_X = 80
WEATHER_ICON_Y = 5
MOON_ICON_X = 250
MOON_ICON_Y = 5

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


def create_text_display(text_content):
    """Create a text display from marked-up string"""
    renderer = TextRenderer()
    return renderer.render_text(text_content)


def create_weather_layout(day_name="Thu", day_num=11, month_name="Dec",
                         current_temp=-1, feels_like=-7, high_temp=-4, low_temp=-10,
                         sunrise_time="7:31a", sunset_time="4:28p",
                         weather_desc="Cloudy. 40 percent chance of flurries this evening. Periods of snow beginning near midnight. Amount 2 to 4 cm. Wind up to 15 km/h. Low minus 5. Wind chill near -9.",
                         weather_icon_name="01n.bmp", moon_icon_name="moon-waning-crescent-5.bmp"):
    """Create structured weather layout display group"""

    # Create main display group
    main_group = displayio.Group()

    # Create white background
    background_bitmap = displayio.Bitmap(DISPLAY_WIDTH, DISPLAY_HEIGHT, 1)
    background_palette = displayio.Palette(1)
    background_palette[0] = WHITE
    background_sprite = displayio.TileGrid(background_bitmap, pixel_shader=background_palette)
    main_group.append(background_sprite)

    # Create renderer for font access
    renderer = TextRenderer()

    # Create positioned text labels using hyperlegible font
    # Layout: [Day centered]  [Weather Icon]  [High temp]   [Moon Icon]  [Sunrise]
    #         [Date centered]                 [Low temp]                 [Sunset]

    # Header line height (1.5x font size for better spacing)
    header_line_height = int(renderer.char_height * 1.5)

    # Day name - centered in left section (0-80px)
    day_label = label.Label(renderer.header_font_regular, text=day_name, color=BLACK)
    day_label.x = 40 - (day_label.bounding_box[2] // 2) if day_label.bounding_box else 30
    day_label.y = 15
    main_group.append(day_label)

    # Date - centered in left section below day
    date_text = f"{day_num} {month_name}"
    date_label = label.Label(renderer.header_font_regular, text=date_text, color=BLACK)
    date_label.x = 40 - (date_label.bounding_box[2] // 2) if date_label.bounding_box else 20
    date_label.y = 18 + header_line_height
    main_group.append(date_label)

    # High temp - positioned after weather icon space
    high_text = f"<hb>H</hb>{high_temp}°C"
    high_segments = renderer.parse_markup(high_text)
    x_pos = WEATHER_ICON_X + 64
    for text_content, style, color in high_segments:
        font = renderer.get_font_for_style(style)
        high_label = label.Label(font, text=text_content, color=color)
        high_label.x = x_pos
        high_label.y = 15
        main_group.append(high_label)
        if high_label.bounding_box:
            x_pos += high_label.bounding_box[2]

    # Low temp - positioned below high temp
    low_text = f"<hb>L</hb>{low_temp}°C"
    low_segments = renderer.parse_markup(low_text)
    x_pos = WEATHER_ICON_X + 64
    for text_content, style, color in low_segments:
        font = renderer.get_font_for_style(style)
        low_label = label.Label(font, text=text_content, color=color)
        low_label.x = x_pos
        low_label.y = 18 + header_line_height
        main_group.append(low_label)
        if low_label.bounding_box:
            x_pos += low_label.bounding_box[2]

    # Sunrise time - positioned after moon icon
    sunrise_label = label.Label(renderer.header_font_regular, text=sunrise_time, color=BLACK)
    sunrise_label.x = MOON_ICON_X + 64 + 10  # After moon icon + width + margin
    sunrise_label.y = 15
    main_group.append(sunrise_label)

    # Sunset time - positioned below sunrise
    sunset_label = label.Label(renderer.header_font_regular, text=sunset_time, color=BLACK)
    sunset_label.x = MOON_ICON_X + 64 + 10
    sunset_label.y = 18 + header_line_height
    main_group.append(sunset_label)

    # Weather description using text renderer with available height
    available_height = DISPLAY_HEIGHT - 60  # Height minus header section
    desc_renderer = TextRenderer(width=DISPLAY_WIDTH, height=available_height)
    desc_text = desc_renderer.render_text(weather_desc)
    desc_text.y = 60
    main_group.append(desc_text)

    # Note: Icons will be added by the calling code since they require SD card access
    # Icon positions: weather at (WEATHER_ICON_X, WEATHER_ICON_Y), moon at (MOON_ICON_X, MOON_ICON_Y)
    # Layout: [Day/Date 80px] [Weather Icon 64px] [H/L Temps] [Moon Icon 64px] [Sunrise/Sunset]

    return main_group

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
