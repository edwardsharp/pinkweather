import time
import board
import busio
import digitalio
import displayio
import fourwire
import terminalio
from adafruit_display_text import label
from adafruit_bitmap_font import bitmap_font
import adafruit_ssd1683
import re

# Release any previously used displays
displayio.release_displays()

# Pin assignments for Pico 2W
# SPI pins: SCK=GP18, MOSI=GP19, MISO=GP16
# CS pin: GP17
spi = busio.SPI(clock=board.GP18, MOSI=board.GP19, MISO=board.GP16)

# Pin assignments for FourWire (use Pin objects directly)
cs_pin = board.GP17
dc_pin = board.GP20  # You'll need to wire this DC pin!

# Reset and Busy pins (optional but recommended)
rst_pin = None  # board.GP21
busy_pin = None  # digitalio.DigitalInOut(board.GP22) if you wire it

# Create the display bus
display_bus = fourwire.FourWire(
    spi,
    command=dc_pin,
    chip_select=cs_pin,
    reset=rst_pin,
    baudrate=1000000
)

# Wait a moment for the bus to initialize
time.sleep(1)

# Create the display
display = adafruit_ssd1683.SSD1683(
    display_bus,
    width=400,
    height=300,
    highlight_color=0xFF0000,
    busy_pin=busy_pin
)

# Rotate display 180 degrees
display.rotation = 180

# Display dimensions and colors
DISPLAY_WIDTH = 400
DISPLAY_HEIGHT = 300
BLACK = 0x000000
WHITE = 0xFFFFFF
RED = 0xFF0000

# Load custom fonts
try:
    font_regular = bitmap_font.load_font("vollkorn20reg.pcf")
    font_bold = bitmap_font.load_font("vollkorn20black.pcf")
    font_italic = bitmap_font.load_font("vollkorn20italic.pcf")
    font_bold_italic = bitmap_font.load_font("vollkorn20blackitalic.pcf")
    print("Custom fonts loaded successfully")
except Exception as e:
    print(f"Error loading fonts: {e}")
    # Fallback to terminal font
    font_regular = terminalio.FONT
    font_bold = terminalio.FONT
    font_italic = terminalio.FONT
    font_bold_italic = terminalio.FONT

class TextRenderer:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.font_regular = font_regular
        self.font_bold = font_bold
        self.font_italic = font_italic
        self.font_bold_italic = font_bold_italic

        # Get approximate character dimensions from regular font
        test_label = label.Label(self.font_regular, text="M", color=BLACK)
        self.char_width = test_label.bounding_box[2] if test_label.bounding_box else 10
        self.char_height = test_label.bounding_box[3] if test_label.bounding_box else 16

        # Calculate proper line height (font height + some spacing)
        self.line_height = int(self.char_height * 1.5)  # 50% spacing between lines for better readability

        # Calculate rough capacity
        self.chars_per_line = self.width // self.char_width
        self.lines_per_screen = self.height // self.line_height
        self.total_char_capacity = self.chars_per_line * self.lines_per_screen

        print(f"Font metrics: {self.char_width}w x {self.char_height}h, line height: {self.line_height}")
        print(f"Capacity: ~{self.chars_per_line} chars/line, ~{self.lines_per_screen} lines")
        print(f"Total capacity: ~{self.total_char_capacity} characters")

    def parse_markup(self, text):
        """Parse markup tags and return list of (text, style, color) tuples"""
        segments = []

        # Define markup patterns
        patterns = {
            'bi': (r'<bi>(.*?)</bi>', 'bold_italic'),
            'b': (r'<b>(.*?)</b>', 'bold'),
            'i': (r'<i>(.*?)</i>', 'italic'),
            'red': (r'<red>(.*?)</red>', 'red'),
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
                break

        # Add any remaining text
        if current_pos < len(text):
            remaining_text = text[current_pos:]
            if remaining_text:
                segments.append((remaining_text, 'regular', BLACK))

        return segments

    def get_font_for_style(self, style):
        """Get the appropriate font for a style"""
        if style == 'bold':
            return self.font_bold
        elif style == 'italic':
            return self.font_italic
        elif style == 'bold_italic':
            return self.font_bold_italic
        else:
            return self.font_regular

    def measure_text_width(self, text, style):
        """Measure the width of text in pixels"""
        font = self.get_font_for_style(style)
        test_label = label.Label(font, text=text, color=BLACK)
        return test_label.bounding_box[2] if test_label.bounding_box else len(text) * self.char_width

    def hard_wrap_text(self, segments):
        """Hard wrap text segments with aggressive word breaking and hyphenation"""
        wrapped_lines = []
        current_line = []
        current_width = 0

        for text_content, style, color in segments:
            i = 0
            while i < len(text_content):
                char = text_content[i]

                # Handle newlines
                if char == '\n':
                    if current_line:
                        wrapped_lines.append(current_line)
                    current_line = []
                    current_width = 0
                    i += 1
                    continue

                # Skip multiple spaces
                if char == ' ' and current_width == 0:
                    i += 1
                    continue

                # Build characters into words, but break aggressively
                word = ""
                word_start_i = i

                # Collect non-space characters
                while i < len(text_content) and text_content[i] not in [' ', '\n']:
                    char = text_content[i]
                    char_width = self.measure_text_width(char, style)

                    # Check if adding this character would exceed line width
                    if current_width + self.measure_text_width(word + char, style) > self.width:
                        # Need to break here
                        if word:
                            # Add current word with hyphen
                            current_line.append((word + '-', style, color))
                            wrapped_lines.append(current_line)
                            current_line = []
                            current_width = 0
                            word = ""
                        # Continue building from this character

                    word += char
                    i += 1

                # Add the completed word if it fits
                if word:
                    word_width = self.measure_text_width(word, style)
                    if current_width + word_width <= self.width:
                        current_line.append((word, style, color))
                        current_width += word_width
                    else:
                        # Word still doesn't fit, force break it
                        while word:
                            if current_line:
                                wrapped_lines.append(current_line)
                                current_line = []
                                current_width = 0

                            # Find max chars that fit with hyphen
                            max_chars = 1
                            hyphen_width = self.measure_text_width('-', style)

                            for j in range(1, len(word) + 1):
                                test_part = word[:j]
                                test_width = self.measure_text_width(test_part, style)
                                if j < len(word):
                                    test_width += hyphen_width

                                if test_width <= self.width:
                                    max_chars = j
                                else:
                                    break

                            if max_chars < len(word):
                                current_line.append((word[:max_chars] + '-', style, color))
                                wrapped_lines.append(current_line)
                                current_line = []
                                current_width = 0
                                word = word[max_chars:]
                            else:
                                current_line.append((word, style, color))
                                current_width = self.measure_text_width(word, style)
                                word = ""

                # Handle space after word
                if i < len(text_content) and text_content[i] == ' ':
                    space_width = self.measure_text_width(' ', style)
                    if current_width + space_width <= self.width:
                        current_line.append((' ', style, color))
                        current_width += space_width
                    i += 1

        # Add final line
        if current_line:
            wrapped_lines.append(current_line)

        return wrapped_lines

    def render_text(self, markup_text):
        """Render marked-up text to a display group"""
        # Parse markup
        segments = self.parse_markup(markup_text)
        print(f"Parsed {len(segments)} text segments")

        # Hard wrap the text
        wrapped_lines = self.hard_wrap_text(segments)
        print(f"Created {len(wrapped_lines)} lines")

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
            if y_position >= self.height - self.line_height:
                break  # Don't render beyond screen

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

# Create text renderer
renderer = TextRenderer(DISPLAY_WIDTH, DISPLAY_HEIGHT)

# Weather forecast sample text with markup
sample_text = """<red>Cloudy</red> conditions with <i>rain</i> expected around <b>2am</b>. Wind gusts up to <b>25mph</b> making it feel like <red>-2°C</red>.

<b>Tmrrw:</b> <red>Sunny</red> and <b>4°C</b> with light winds from the <i>west</i> at 10 k/ph.

<b>Weekend:</b> <bi>Partly cloudy</bi> with temperatures reaching <b>6°C</b>."""

# Render the text
print("Rendering text...")
text_group = renderer.render_text(sample_text)

# Set the root group and refresh the display
display.root_group = text_group
display.refresh()

print("Display refreshed with formatted text!")

# Wait for the refresh to complete
time.sleep(display.time_to_refresh + 2)
print("Refresh complete")

# Keep the program running
while True:
    time.sleep(10)
