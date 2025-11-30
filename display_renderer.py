"""
Weather Display Renderer Module

This module provides shared rendering functionality for both microcontroller
and web development environments. It creates PIL images that can be displayed
on e-ink displays or rendered as web images.
"""

from PIL import Image, ImageDraw, ImageFont
import textwrap
import os

# Color constants for tri-color e-ink display
WHITE = (0xFF, 0xFF, 0xFF)
BLACK = (0x00, 0x00, 0x00)
RED = (0xFF, 0x00, 0x00)

class WeatherDisplayRenderer:
    def __init__(self, width=250, height=122, font_path="AndaleMono.ttf"):
        """
        Initialize the weather display renderer.

        Args:
            width (int): Display width in pixels
            height (int): Display height in pixels
            font_path (str): Path to TTF font file
        """
        self.width = width
        self.height = height
        self.font_path = font_path

        # Default styling
        self.border = 4
        self.font_size = 12
        self.line_spacing = 2
        self.background_color = WHITE
        self.text_color = BLACK
        self.accent_color = RED

    def _get_font(self, size=None):
        """Get font object, fallback to default if font file not found."""
        if size is None:
            size = self.font_size

        try:
            if os.path.exists(self.font_path):
                return ImageFont.truetype(self.font_path, size)
        except (OSError, IOError):
            pass

        # Fallback to default font
        try:
            return ImageFont.load_default()
        except:
            return ImageFont.load_default()

    def _wrap_text(self, text, font, max_width):
        """Wrap text to fit within max_width pixels."""
        words = text.split()
        lines = []
        current_line = ""

        for word in words:
            test_line = current_line + (" " if current_line else "") + word
            bbox = font.getbbox(test_line)
            text_width = bbox[2] - bbox[0]

            if text_width <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                    current_line = word
                else:
                    # Word is too long, force break
                    lines.append(word)
                    current_line = ""

        if current_line:
            lines.append(current_line)

        return lines

    def render_text_display(self, text, title=None):
        """
        Render a text-based display with optional title.

        Args:
            text (str): Main text content to display
            title (str, optional): Title text to display at top

        Returns:
            PIL.Image: Rendered image ready for display
        """
        # Create image
        image = Image.new("RGB", (self.width, self.height), self.background_color)
        draw = ImageDraw.Draw(image)

        # Calculate available area
        content_width = self.width - (2 * self.border)
        content_height = self.height - (2 * self.border)

        y_offset = self.border

        # Draw title if provided
        if title:
            title_font = self._get_font(self.font_size + 2)
            title_bbox = title_font.getbbox(title)
            title_height = title_bbox[3] - title_bbox[1]

            # Center title horizontally
            title_width = title_bbox[2] - title_bbox[0]
            title_x = self.border + (content_width - title_width) // 2

            draw.text(
                (title_x, y_offset),
                title,
                font=title_font,
                fill=self.accent_color
            )

            y_offset += title_height + self.line_spacing * 2
            content_height -= title_height + self.line_spacing * 2

        # Render main text
        font = self._get_font()
        lines = self._wrap_text(text, font, content_width)

        # Calculate line height
        sample_bbox = font.getbbox("Ay")
        line_height = sample_bbox[3] - sample_bbox[1] + self.line_spacing

        # Draw lines
        for line in lines:
            if y_offset + line_height > self.height - self.border:
                break  # Don't overflow display

            draw.text(
                (self.border, y_offset),
                line,
                font=font,
                fill=self.text_color
            )
            y_offset += line_height

        return image

    def render_weather_layout(self, temperature, condition, location, additional_info=""):
        """
        Render a weather-focused display layout.

        Args:
            temperature (str): Temperature display (e.g., "72°F")
            condition (str): Weather condition (e.g., "Sunny")
            location (str): Location name
            additional_info (str): Additional weather info

        Returns:
            PIL.Image: Rendered weather display image
        """
        image = Image.new("RGB", (self.width, self.height), self.background_color)
        draw = ImageDraw.Draw(image)

        y_offset = self.border

        # Location (top, small font)
        location_font = self._get_font(10)
        draw.text(
            (self.border, y_offset),
            location,
            font=location_font,
            fill=self.text_color
        )

        location_bbox = location_font.getbbox(location)
        y_offset += (location_bbox[3] - location_bbox[1]) + self.line_spacing

        # Temperature (large, centered)
        temp_font = self._get_font(28)
        temp_bbox = temp_font.getbbox(temperature)
        temp_width = temp_bbox[2] - temp_bbox[0]
        temp_height = temp_bbox[3] - temp_bbox[1]

        temp_x = self.border + (self.width - 2 * self.border - temp_width) // 2
        draw.text(
            (temp_x, y_offset),
            temperature,
            font=temp_font,
            fill=self.accent_color
        )

        y_offset += temp_height + self.line_spacing

        # Condition (medium, centered)
        condition_font = self._get_font(16)
        condition_bbox = condition_font.getbbox(condition)
        condition_width = condition_bbox[2] - condition_bbox[0]
        condition_height = condition_bbox[3] - condition_bbox[1]

        condition_x = self.border + (self.width - 2 * self.border - condition_width) // 2
        draw.text(
            (condition_x, y_offset),
            condition,
            font=condition_font,
            fill=self.text_color
        )

        y_offset += condition_height + self.line_spacing * 2

        # Additional info (small, wrapped)
        if additional_info:
            info_font = self._get_font(10)
            content_width = self.width - (2 * self.border)
            info_lines = self._wrap_text(additional_info, info_font, content_width)

            info_bbox = info_font.getbbox("Ay")
            info_line_height = info_bbox[3] - info_bbox[1] + self.line_spacing

            for line in info_lines:
                if y_offset + info_line_height > self.height - self.border:
                    break

                draw.text(
                    (self.border, y_offset),
                    line,
                    font=info_font,
                    fill=self.text_color
                )
                y_offset += info_line_height

        return image

    def render_debug_display(self, debug_info):
        """
        Render a debug information display.

        Args:
            debug_info (dict): Dictionary of debug key-value pairs

        Returns:
            PIL.Image: Rendered debug display image
        """
        lines = []
        for key, value in debug_info.items():
            lines.append(f"{key}: {value}")

        debug_text = "\n".join(lines)
        return self.render_text_display(debug_text, "DEBUG INFO")
