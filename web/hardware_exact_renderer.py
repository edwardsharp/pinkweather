"""
Hardware-exact renderer for web preview
Uses the exact same positioning logic as the hardware CircuitPython code
to ensure pixel-perfect matching between web preview and actual hardware display
"""

from PIL import Image, ImageDraw, ImageFont
import os

# Hardware constants
DISPLAY_WIDTH = 122
DISPLAY_HEIGHT = 250
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)


class AdafruitBitmapFontWrapper:
    """Wrapper to use adafruit_bitmap_font with PIL rendering for hardware-exact fonts"""

    def __init__(self, font_path):
        """Load font using adafruit_bitmap_font (same as hardware)"""
        try:
            from adafruit_bitmap_font import bitmap_font
            self.adafruit_font = bitmap_font.load_font(font_path)
            self.font_path = font_path
            self._glyph_cache = {}
            print(f"Loaded hardware-exact font: {font_path}")
        except ImportError:
            print("Warning: adafruit_bitmap_font not available, falling back to PIL")
            # Fallback to PIL if adafruit library not available
            self.adafruit_font = None
            if font_path.endswith('.pcf'):
                # Try to use corresponding .bdf file
                bdf_path = font_path.replace('.pcf', '.bdf')
                if os.path.exists(bdf_path):
                    self.pil_font = ImageFont.load(bdf_path)
                else:
                    self.pil_font = ImageFont.load_default()
            else:
                self.pil_font = ImageFont.load(font_path)
        except Exception as e:
            print(f"Error loading font {font_path}: {e}")
            # Ultimate fallback
            self.adafruit_font = None
            self.pil_font = ImageFont.load_default()

    def _bitmap_to_pil_image(self, bitmap):
        """Convert displayio.Bitmap to PIL Image"""
        width, height = bitmap.width, bitmap.height

        # Create PIL image (1-bit bitmap)
        pil_image = Image.new('1', (width, height), 0)

        # Copy pixel data - don't invert, use as-is
        for y in range(height):
            for x in range(width):
                pixel = bitmap[x, y]
                # Use pixel as-is (1=foreground, 0=background)
                pil_image.putpixel((x, y), pixel)

        return pil_image

    def _get_glyph_image(self, char):
        """Get PIL image for a character glyph"""
        if char in self._glyph_cache:
            return self._glyph_cache[char]

        if self.adafruit_font:
            try:
                glyph = self.adafruit_font.get_glyph(ord(char))
                glyph_image = self._bitmap_to_pil_image(glyph.bitmap)
                glyph_data = {
                    'image': glyph_image,
                    'width': glyph.width,
                    'height': glyph.height,
                    'dx': glyph.dx,
                    'dy': glyph.dy,
                    'shift_x': glyph.shift_x,
                    'shift_y': glyph.shift_y
                }
                self._glyph_cache[char] = glyph_data
                return glyph_data
            except Exception as e:
                print(f"Error getting glyph for '{char}': {e}")
                return None
        return None

    def draw_text(self, draw, text, xy, fill=BLACK):
        """Draw text using hardware-exact glyph positioning"""
        if not self.adafruit_font:
            # Fallback to PIL font
            draw.text(xy, text, font=self.pil_font, fill=fill)
            return

        x, y = xy
        current_x = x

        for char in text:
            glyph_data = self._get_glyph_image(char)
            if glyph_data:
                # Position glyph exactly as hardware would
                glyph_x = current_x + glyph_data['dx']
                glyph_y = y + glyph_data['dy']

                # Create a temporary image for the glyph
                glyph_img = Image.new('RGBA', (glyph_data['width'], glyph_data['height']), (0, 0, 0, 0))
                glyph_draw = ImageDraw.Draw(glyph_img)

                # Draw the glyph pixels in the specified color
                for gy in range(glyph_data['height']):
                    for gx in range(glyph_data['width']):
                        if glyph_data['image'].getpixel((gx, gy)) == 1:
                            glyph_img.putpixel((gx, gy), fill + (255,))

                # Paste the glyph onto the main image
                draw._image.paste(glyph_img, (glyph_x, glyph_y), glyph_img)

                # Advance to next character position
                current_x += glyph_data['shift_x']
            else:
                # Fallback for missing glyphs
                current_x += 10  # Approximate character width

    def textbbox(self, text):
        """Get text bounding box for layout calculations"""
        if not self.adafruit_font:
            # Fallback to PIL font estimation
            return (0, 0, len(text) * 8, 12)

        if not text:
            return (0, 0, 0, 0)

        total_width = 0
        max_height = 0
        min_dy = 0
        max_height_with_dy = 0

        for char in text:
            glyph_data = self._get_glyph_image(char)
            if glyph_data:
                total_width += glyph_data['shift_x']
                max_height = max(max_height, glyph_data['height'])
                min_dy = min(min_dy, glyph_data['dy'])
                max_height_with_dy = max(max_height_with_dy, glyph_data['height'] + glyph_data['dy'])

        return (0, min_dy, total_width, max_height_with_dy)

class PILFontWrapper:
    """Wrapper for PIL fonts to match AdafruitBitmapFontWrapper interface"""
    def __init__(self, font):
        self.pil_font = font

    def draw_text(self, draw, text, xy, fill=BLACK):
        draw.text(xy, text, font=self.pil_font, fill=fill)

    def textbbox(self, text):
        return (0, 0, len(text) * 6, 8)  # Approximate for monospace

class HardwareExactRenderer:
    def __init__(self):
        """Initialize with hardware-matching fonts"""
        # Change to web directory to find font files
        current_dir = os.getcwd()
        web_dir = os.path.join(os.path.dirname(__file__))
        if web_dir:
            os.chdir(web_dir)

        try:
            # Load exact hardware fonts using same method as CircuitPython
            # Try PCF files first (same as hardware), fallback to BDF
            try:
                self.large_font = AdafruitBitmapFontWrapper("barlowcond60.pcf")
                self.small_font = AdafruitBitmapFontWrapper("barlowcond30.pcf")
            except:
                # Fallback to BDF files
                self.large_font = AdafruitBitmapFontWrapper("barlowcond60.bdf")
                self.small_font = AdafruitBitmapFontWrapper("barlowcond30.bdf")

            # Tiny font - use PIL wrapper for compatibility
            try:
                pil_tiny_font = ImageFont.load("font5x8.bin")
                self.tiny_font = PILFontWrapper(pil_tiny_font)
            except:
                pil_default_font = ImageFont.load_default()
                self.tiny_font = PILFontWrapper(pil_default_font)

            print("Loaded hardware-exact fonts using adafruit_bitmap_font")
        finally:
            # Restore original directory
            os.chdir(current_dir)



    def create_temp_display(self, draw, temp_c, x, y):
        """Create temperature display exactly like hardware"""
        temp_int = int(round(temp_c))
        is_negative = temp_int < 0
        temp_str = str(abs(temp_int))

        current_x = x

        # Minus sign if negative (using small font)
        if is_negative:
            self.small_font.draw_text(draw, "-", (current_x, y), fill=BLACK)
            current_x += 15

        # Number (using large font) - hardware uses y=0 as baseline
        self.large_font.draw_text(draw, temp_str, (current_x, y), fill=BLACK)
        current_x += len(temp_str) * 30  # rough width estimate like hardware

        # Degree symbol (superscript, using small font) - hardware uses y=-10
        self.small_font.draw_text(draw, "°", (current_x + 4, y - 10), fill=BLACK)

    def create_humidity_display(self, draw, humidity, x, y):
        """Create humidity display exactly like hardware"""
        humidity_str = str(int(round(humidity)))

        # Number (using large font) - hardware uses y=0 as baseline
        self.large_font.draw_text(draw, humidity_str, (x, y), fill=RED)

        # Percent symbol - hardware uses len * 30 + 4 spacing and y=15
        percent_x = x + len(humidity_str) * 30 + 4
        self.small_font.draw_text(draw, "%", (percent_x, y + 15), fill=RED)

    def draw_centered_text(self, draw, text, font, color, y, width=DISPLAY_WIDTH):
        """Draw centered text exactly like hardware anchor_point implementation"""
        bbox = font.textbbox(text)
        text_width = bbox[2] - bbox[0]
        x = (width - text_width) // 2
        adjusted_y = y - 6
        font.draw_text(draw, text, (x, adjusted_y), fill=color)

    def create_line_graph(self, draw, data_points, color, y_start, height):
        """Create line graph with thick lines and min/max labels exactly like hardware"""
        if len(data_points) < 2:
            return

        graph_width = DISPLAY_WIDTH  # Full width
        x_step = graph_width // (len(data_points) - 1) if len(data_points) > 1 else 0

        # Normalize data to fit in height
        min_val = min(data_points)
        max_val = max(data_points)
        val_range = max_val - min_val if max_val != min_val else 1

        # Draw thick lines (2px thick)
        for i in range(len(data_points) - 1):
            x1 = 10 + i * x_step
            x2 = 10 + (i + 1) * x_step

            # Scale y values
            y1 = y_start + height - int(((data_points[i] - min_val) / val_range) * height)
            y2 = y_start + height - int(((data_points[i + 1] - min_val) / val_range) * height)

            # Draw two parallel lines for thickness
            draw.line([x1, y1, x2, y2], fill=color, width=1)
            draw.line([x1, y1 + 1, x2, y2 + 1], fill=color, width=1)

        # Add min/max labels with colored backgrounds
        # Max label (top left)
        draw.rectangle([0, y_start - 2, 16, y_start + 12], fill=color)
        self.tiny_font.draw_text(draw, f"{int(max_val)}", (2, y_start - 1), fill=WHITE)

        # Min label (bottom left)
        draw.rectangle([0, y_start + height - 12, 16, y_start + height + 2], fill=color)
        self.tiny_font.draw_text(draw, f"{int(min_val)}", (2, y_start + height - 11), fill=WHITE)

    def get_historical_averages(self, csv_data, current_time_ms):
        """Calculate averages exactly like hardware"""
        if not csv_data:
            return {
                'temp': {'day': 0, 'week': 0, 'month': 0, 'year': 0},
                'humidity': {'day': 0, 'week': 0, 'month': 0, 'year': 0}
            }

        # Time periods in milliseconds
        day_ms = 24 * 60 * 60 * 1000
        week_ms = 7 * day_ms
        month_ms = 30 * day_ms
        year_ms = 365 * day_ms

        periods = {
            'day': current_time_ms - day_ms,
            'week': current_time_ms - week_ms,
            'month': current_time_ms - month_ms,
            'year': current_time_ms - year_ms
        }

        averages = {
            'temp': {'day': 0, 'week': 0, 'month': 0, 'year': 0},
            'humidity': {'day': 0, 'week': 0, 'month': 0, 'year': 0}
        }

        for period_name, cutoff_time in periods.items():
            temp_sum = humidity_sum = count = 0

            for entry in csv_data:
                if entry['timestamp'] >= cutoff_time:
                    temp_sum += entry['temp']
                    humidity_sum += entry['humidity']
                    count += 1

            if count > 0:
                averages['temp'][period_name] = int(temp_sum / count)
                averages['humidity'][period_name] = int(humidity_sum / count)

        return averages

    def get_graph_data(self, csv_data, num_points=60):
        """Get graph data exactly like hardware"""
        if not csv_data:
            return [22] * num_points, [45] * num_points

        # Get the last num_points entries
        recent_entries = csv_data[-num_points:] if len(csv_data) >= num_points else csv_data

        temp_data = [entry['temp'] for entry in recent_entries]
        humidity_data = [entry['humidity'] for entry in recent_entries]

        # Fill with current values if we don't have enough points
        if len(temp_data) < num_points and temp_data:
            first_temp = temp_data[0]
            first_humidity = humidity_data[0]
            while len(temp_data) < num_points:
                temp_data.insert(0, first_temp)
                humidity_data.insert(0, first_humidity)
        elif len(temp_data) == 0:
            temp_data = [22] * num_points
            humidity_data = [45] * num_points

        return temp_data[-num_points:], humidity_data[-num_points:]

    def format_time_short(self, seconds):
        """Format time exactly like hardware"""
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:  # < 1 hour
            return f"{int(seconds/60)}m"
        elif seconds < 86400:  # < 1 day
            return f"{int(seconds/3600)}h"
        elif seconds < 2592000:  # < 30 days
            return f"{int(seconds/86400)}d"
        elif seconds < 31536000:  # < 365 days
            return f"{int(seconds/2592000)}M"
        else:
            return f"{int(seconds/31536000)}y"

    def render_display(self, sensor_data, csv_data, system_status):
        """Render complete display using exact hardware positioning"""
        # Create image
        image = Image.new("RGB", (DISPLAY_WIDTH, DISPLAY_HEIGHT), WHITE)
        draw = ImageDraw.Draw(image)

        # Get historical data
        import time
        current_time_ms = time.time() * 1000
        averages = self.get_historical_averages(csv_data, current_time_ms)
        temp_data, humidity_data = self.get_graph_data(csv_data)

        # Current temperature (top) - exactly like hardware: x=20, y=25
        self.create_temp_display(draw, sensor_data['temp_c'], 20, 25)

        # Temperature averages - exactly like hardware: centered at y=75
        temp_avg_text = f"D:{averages['temp']['day']} W:{averages['temp']['week']} M:{averages['temp']['month']} Y:{averages['temp']['year']}"
        self.draw_centered_text(draw, temp_avg_text, self.tiny_font, BLACK, 75)

        # Temperature graph with border - exactly like hardware
        temp_y_start = 84
        temp_height = 32
        # Border
        draw.rectangle([0, temp_y_start - 2, DISPLAY_WIDTH, temp_y_start + temp_height + 2], outline=BLACK, width=2)
        # Graph
        self.create_line_graph(draw, temp_data, BLACK, temp_y_start, temp_height)

        # Humidity graph with border - exactly like hardware
        humidity_y_start = 124
        humidity_height = 32
        # Border
        draw.rectangle([0, humidity_y_start - 2, DISPLAY_WIDTH, humidity_y_start + humidity_height + 2], outline=RED, width=2)
        # Graph
        self.create_line_graph(draw, humidity_data, RED, humidity_y_start, humidity_height)

        # Humidity averages - exactly like hardware: centered at y=166
        humidity_avg_text = f"D:{averages['humidity']['day']} W:{averages['humidity']['week']} M:{averages['humidity']['month']} Y:{averages['humidity']['year']}"
        self.draw_centered_text(draw, humidity_avg_text, self.tiny_font, RED, humidity_y_start + humidity_height + 10)

        # Current humidity - exactly like hardware: x=20, y=194
        self.create_humidity_display(draw, sensor_data['humidity'], 20, humidity_y_start + humidity_height + 38)

        # Status bar - exactly like hardware
        status_bar_height = 12
        status_bar_y = DISPLAY_HEIGHT - status_bar_height
        draw.rectangle([0, status_bar_y, DISPLAY_WIDTH, DISPLAY_HEIGHT], fill=BLACK)

        # Status text - exactly like hardware: centered at y=244
        sd_status = "SD" if system_status['sd_available'] else "NOD"
        status_text = f"{sd_status} {system_status['sd_total_time']} {system_status['uptime']} {system_status['power_status']} {system_status['battery_status']}"
        self.draw_centered_text(draw, status_text, self.tiny_font, WHITE, status_bar_y + 6)

        return image
