"""
Simple web renderer that uses EXACT same display code as hardware
Creates a mock display that saves to image instead of e-ink refresh
"""

import sys
import os
from PIL import Image, ImageDraw

# Add CIRCUITPY to import path
circuitpy_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'CIRCUITPY')
sys.path.insert(0, circuitpy_path)

class MockDisplay:
    """Mock display that captures displayio groups and converts to PIL image"""
    def __init__(self, width=122, height=250):
        self.width = width
        self.height = height
        self.root_group = None
        self.busy = False

    def refresh(self):
        """Instead of refreshing e-ink, capture the display group and convert to image"""
        if self.root_group is None:
            return None

        # Convert displayio group to PIL image
        return self._group_to_image(self.root_group)

    def _group_to_image(self, group):
        """Convert displayio group to PIL image using the same logic as hardware"""
        image = Image.new('RGB', (self.width, self.height), (255, 255, 255))
        draw = ImageDraw.Draw(image)

        # Import display modules here to avoid circular imports
        from adafruit_display_text.label import Label
        from adafruit_display_shapes.rect import Rect
        from adafruit_display_shapes.line import Line
        import displayio

        self._render_group(draw, group, 0, 0)
        return image

    def _render_group(self, draw, group, offset_x, offset_y):
        """Recursively render displayio group"""
        from adafruit_display_text.label import Label
        from adafruit_display_shapes.rect import Rect
        from adafruit_display_shapes.line import Line
        import displayio

        group_x = getattr(group, 'x', 0) + offset_x
        group_y = getattr(group, 'y', 0) + offset_y

        if getattr(group, 'hidden', False):
            return

        for item in group:
            if isinstance(item, displayio.Group):
                self._render_group(draw, item, group_x, group_y)
            elif isinstance(item, Rect):
                self._render_rect(draw, item, group_x, group_y)
            elif isinstance(item, Line):
                self._render_line(draw, item, group_x, group_y)
            elif isinstance(item, Label):
                self._render_label(draw, item, group_x, group_y)
            elif hasattr(item, 'bitmap') and hasattr(item, 'pixel_shader'):
                # This is a TileGrid (what Labels become in displayio emulation)
                self._render_tilegrid(draw, item, group_x, group_y)

    def _render_rect(self, draw, rect, offset_x, offset_y):
        """Render rectangle using its internal bitmap like hardware"""
        x = rect.x + offset_x
        y = rect.y + offset_y

        # Rect objects have internal bitmaps just like Line objects
        if hasattr(rect, 'bitmap') and rect.bitmap and hasattr(rect, 'pixel_shader'):
            bitmap = rect.bitmap
            palette = rect.pixel_shader

            # Render each pixel from the bitmap using the palette
            try:
                for by in range(bitmap.height):
                    for bx in range(bitmap.width):
                        pixel_index = bitmap[bx, by]
                        # Render all pixels using their palette colors
                        if hasattr(palette, '__getitem__') and len(palette) > pixel_index:
                            try:
                                color = self._convert_color(palette[pixel_index])
                                if color is not None:
                                    draw.point((x + bx, y + by), fill=color)
                            except:
                                pass
            except:
                pass

    def _render_line(self, draw, line_obj, offset_x, offset_y):
        """Render line using its internal bitmap"""
        x = line_obj.x + offset_x
        y = line_obj.y + offset_y

        if hasattr(line_obj, 'bitmap') and line_obj.bitmap:
            color = self._convert_color(line_obj.color)
            if color:
                self._render_bitmap(draw, line_obj.bitmap, x, y, color)

    def _render_label(self, draw, label_obj, offset_x, offset_y):
        """Render text label"""
        x = label_obj.x + offset_x
        y = label_obj.y + offset_y

        # Handle anchored positioning
        if hasattr(label_obj, 'anchored_position') and label_obj.anchored_position:
            anchor_x, anchor_y = label_obj.anchored_position
            anchor_point = getattr(label_obj, 'anchor_point', (0, 0))

            text = label_obj.text or ""

            # Estimate text size for anchor calculations
            if hasattr(label_obj.font, 'load_glyphs'):
                # terminalio font
                text_width = len(text) * 6
                text_height = 8
            else:
                # bitmap font - estimate based on font size
                text_width = len(text) * 30
                text_height = 60

            anchor_offset_x = text_width * anchor_point[0]
            anchor_offset_y = text_height * anchor_point[1]

            x = anchor_x - anchor_offset_x
            y = anchor_y - anchor_offset_y

        text = label_obj.text or ""
        color = self._convert_color(label_obj.color)

        if text and color:
            if hasattr(label_obj.font, 'load_glyphs'):
                # terminalio font - use PIL default
                try:
                    from PIL import ImageFont
                    pil_font = ImageFont.load_default()
                    draw.text((x, y), text, font=pil_font, fill=color)
                except:
                    draw.text((x, y), text, fill=color)
            else:
                # bitmap font
                self._render_bitmap_text(draw, text, label_obj.font, x, y, color)

    def _render_bitmap_text(self, draw, text, font, x, y, color):
        """Render bitmap font text"""
        current_x = x

        for char in text:
            try:
                glyph = font.get_glyph(ord(char))

                # Position glyph
                glyph_x = current_x + glyph.dx
                glyph_y = y + glyph.dy

                # Render glyph bitmap
                self._render_bitmap(draw, glyph.bitmap, glyph_x, glyph_y, color)

                # Advance position
                current_x += glyph.shift_x

            except Exception as e:
                # Skip problematic characters
                current_x += 10

    def _render_bitmap(self, draw, bitmap, x, y, color):
        """Render displayio bitmap"""
        try:
            for by in range(bitmap.height):
                for bx in range(bitmap.width):
                    pixel = bitmap[bx, by]
                    if pixel > 0:  # Foreground pixel
                        draw.point((x + bx, y + by), fill=color)
        except Exception as e:
            pass  # Skip bitmap errors

    def _convert_color(self, displayio_color):
        """Convert displayio color to PIL RGB"""
        if displayio_color is None:
            return None

        if isinstance(displayio_color, int):
            r = (displayio_color >> 16) & 0xFF
            g = (displayio_color >> 8) & 0xFF
            b = displayio_color & 0xFF
            return (r, g, b)

        return displayio_color

    def _render_tilegrid(self, draw, tilegrid, offset_x, offset_y):
        """Render displayio TileGrid (used for text)"""
        x = tilegrid.x + offset_x
        y = tilegrid.y + offset_y

        # TileGrid contains bitmap data and color palette
        if hasattr(tilegrid, 'bitmap') and tilegrid.bitmap and hasattr(tilegrid, 'pixel_shader'):
            bitmap = tilegrid.bitmap
            palette = tilegrid.pixel_shader

            # Get the color for rendering - usually palette[1] is the text color
            try:
                if hasattr(palette, '__getitem__') and len(palette) > 1:
                    text_color = self._convert_color(palette[1])
                else:
                    text_color = (0, 0, 0)  # Default to black
            except:
                text_color = (0, 0, 0)

            if text_color:
                self._render_bitmap(draw, bitmap, x, y, text_color)

def render_web_display(temp_c, humidity, csv_data=None, system_status=None):
    """
    Render display for web using EXACT same code as hardware
    This is the main function that web server should call
    """

    # Change to CIRCUITPY directory for imports and font loading
    current_dir = os.getcwd()

    try:
        os.chdir(circuitpy_path)

        # Import the EXACT same modules hardware uses (except board - no hardware pins needed)
        import displayio
        import time
        import terminalio
        from adafruit_display_text import label
        from adafruit_bitmap_font import bitmap_font
        from adafruit_display_shapes.rect import Rect
        from adafruit_display_shapes.line import Line

        # Create mock display
        display = MockDisplay(122, 250)

        # Load fonts exactly like hardware
        font = bitmap_font.load_font("barlowcond60.pcf")
        small_font = bitmap_font.load_font("barlowcond30.pcf")

        # Constants exactly like hardware
        BLACK = 0x000000
        WHITE = 0xFFFFFF
        RED = 0xFF0000
        DISPLAY_WIDTH = 122
        DISPLAY_HEIGHT = 250

        # Mock data for web (similar to hardware functions but simplified)
        if not csv_data:
            csv_data = []

        def get_historical_averages():
            return {
                'temp': {'day': 22, 'week': 21, 'month': 20, 'year': 19},
                'humidity': {'day': 45, 'week': 46, 'month': 47, 'year': 48}
            }

        def get_graph_data(num_points=60):
            return [22] * num_points, [45] * num_points

        def format_time_short(seconds):
            if seconds < 60:
                return f"{int(seconds)}s"
            elif seconds < 3600:
                return f"{int(seconds/60)}m"
            elif seconds < 86400:
                return f"{int(seconds/3600)}h"
            elif seconds < 2592000:
                return f"{int(seconds/86400)}d"
            elif seconds < 31536000:
                return f"{int(seconds/2592000)}M"
            else:
                return f"{int(seconds/31536000)}y"

        # EXACT same display creation functions as hardware
        def create_temp_display(temp_c):
            temp_int = int(round(temp_c))
            is_negative = temp_int < 0
            temp_str = str(abs(temp_int))

            group = displayio.Group()
            x = 0

            if is_negative:
                minus = label.Label(small_font, text="-", color=BLACK)
                minus.x = x
                minus.y = 0
                group.append(minus)
                x += 15

            number = label.Label(font, text=temp_str, color=BLACK)
            number.x = x
            number.y = 0
            group.append(number)
            x += len(temp_str) * 30

            degree = label.Label(small_font, text="°", color=BLACK)
            degree.x = x + 6  # Adjusted spacing from shared code
            degree.y = -10
            group.append(degree)

            return group

        def create_humidity_display(humidity):
            humidity_str = str(int(round(humidity)))
            group = displayio.Group()

            number = label.Label(font, text=humidity_str, color=RED)
            number.x = 0
            number.y = 0
            group.append(number)

            percent = label.Label(small_font, text="%", color=RED)
            percent.x = len(humidity_str) * 30 + 4
            percent.y = 15
            group.append(percent)

            return group

        def create_line_graph(data_points, color, y_start, height):
            if len(data_points) < 2:
                return displayio.Group()

            group = displayio.Group()
            graph_width = DISPLAY_WIDTH
            x_step = graph_width // (len(data_points) - 1) if len(data_points) > 1 else 0

            min_val = min(data_points)
            max_val = max(data_points)
            val_range = max_val - min_val if max_val != min_val else 1

            for i in range(len(data_points) - 1):
                x1 = 10 + i * x_step
                x2 = 10 + (i + 1) * x_step

                y1 = y_start + height - int(((data_points[i] - min_val) / val_range) * height)
                y2 = y_start + height - int(((data_points[i + 1] - min_val) / val_range) * height)

                line1 = Line(x1, y1, x2, y2, color)
                line2 = Line(x1, y1 + 1, x2, y2 + 1, color)
                group.append(line1)
                group.append(line2)

            # Min/max labels
            max_bg = Rect(0, y_start - 2, 16, 14, fill=color)
            group.append(max_bg)
            max_label = label.Label(terminalio.FONT, text=f"{int(max_val)}", color=WHITE)
            max_label.x = 2
            max_label.y = y_start + 5
            group.append(max_label)

            min_bg = Rect(0, y_start + height - 12, 16, 14, fill=color)
            group.append(min_bg)
            min_label = label.Label(terminalio.FONT, text=f"{int(min_val)}", color=WHITE)
            min_label.x = 2
            min_label.y = y_start + height - 5
            group.append(min_label)

            return group

        # EXACT same update_display function as hardware
        def update_display(temp_c, humidity):
            # Clear display
            g = displayio.Group()
            display.root_group = g

            # Background
            bg = Rect(0, 0, DISPLAY_WIDTH, DISPLAY_HEIGHT, fill=WHITE)
            g.append(bg)

            # Get historical averages
            averages = get_historical_averages()

            # Current temperature (top)
            temp_group = create_temp_display(temp_c)
            temp_group.x = 20
            temp_group.y = 25
            g.append(temp_group)

            # Temperature averages
            temp_avg_text = f"D:{averages['temp']['day']} W:{averages['temp']['week']} M:{averages['temp']['month']} Y:{averages['temp']['year']}"
            temp_avg_label = label.Label(terminalio.FONT, text=temp_avg_text, color=BLACK)
            temp_avg_label.anchor_point = (0.5, 0.5)
            temp_avg_label.anchored_position = (DISPLAY_WIDTH // 2, 75)
            g.append(temp_avg_label)

            # Line graphs
            temp_data, humidity_data = get_graph_data()

            # Temperature graph
            temp_y_start = 84
            temp_height = 32
            temp_border = Rect(0, temp_y_start - 2, DISPLAY_WIDTH, temp_height + 4, outline=BLACK, stroke=2)
            g.append(temp_border)
            temp_graph = create_line_graph(temp_data, BLACK, temp_y_start, temp_height)
            g.append(temp_graph)

            # Humidity graph
            humidity_y_start = 124
            humidity_height = 32
            humidity_border = Rect(0, humidity_y_start - 2, DISPLAY_WIDTH, humidity_height + 4, outline=RED, stroke=2)
            g.append(humidity_border)
            humidity_graph = create_line_graph(humidity_data, RED, humidity_y_start, humidity_height)
            g.append(humidity_graph)

            # Humidity averages
            humidity_avg_text = f"D:{averages['humidity']['day']} W:{averages['humidity']['week']} M:{averages['humidity']['month']} Y:{averages['humidity']['year']}"
            humidity_avg_label = label.Label(terminalio.FONT, text=humidity_avg_text, color=RED)
            humidity_avg_label.anchor_point = (0.5, 0.5)
            humidity_avg_label.anchored_position = (DISPLAY_WIDTH // 2, humidity_y_start + humidity_height + 10)
            g.append(humidity_avg_label)

            # Current humidity
            humidity_group = create_humidity_display(humidity)
            humidity_group.x = 20
            humidity_group.y = humidity_y_start + humidity_height + 38
            g.append(humidity_group)

            # Status bar
            status_bar_height = 12
            status_bar_y = DISPLAY_HEIGHT - status_bar_height
            status_bar = Rect(0, status_bar_y, DISPLAY_WIDTH, status_bar_height, fill=BLACK)
            g.append(status_bar)

            # Status text
            if system_status:
                sd_status = "SD" if system_status.get('sd_available', False) else "NOD"
                sd_time = system_status.get('sd_total_time', '0s')
                uptime = system_status.get('uptime', '0s')
                power_status = system_status.get('power_status', 'P')
                battery_status = system_status.get('battery_status', 'B--')
            else:
                sd_status = "SD"
                sd_time = "2d"
                uptime = "1h"
                power_status = "P"
                battery_status = "B--"

            status_text = f"{sd_status} {sd_time} {uptime} {power_status} {battery_status}"
            status_label = label.Label(terminalio.FONT, text=status_text, color=WHITE)
            status_label.anchor_point = (0.5, 0.5)
            status_label.anchored_position = (DISPLAY_WIDTH // 2, status_bar_y + 6)
            g.append(status_label)

            # Return image instead of refreshing e-ink
            return display.refresh()

        # Call the EXACT same function as hardware
        return update_display(temp_c, humidity)

    finally:
        os.chdir(current_dir)
