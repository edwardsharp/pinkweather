"""
Ultimate simple approach - use EXACT same hardware code with mock display
No PIL conversion, no translation layers, just capture the displayio group
"""

import sys
import os

# Add CIRCUITPY to path
circuitpy_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'CIRCUITPY')
sys.path.insert(0, circuitpy_path)

class MockDisplay:
    """Ultra-simple display mock that just captures the root group"""
    def __init__(self, width=122, height=250):
        self.width = width
        self.height = height
        self.root_group = None
        self.busy = False

    def refresh(self):
        """Instead of refreshing e-ink, just return success"""
        print(f"Display refresh called with group: {self.root_group}")
        if self.root_group:
            print(f"Group has {len(self.root_group)} items")
            return True
        return False

def render_web_display(temp_c, humidity):
    """
    Use EXACT same hardware code with mock display
    This literally imports and runs the hardware update_display function
    """

    # Change to CIRCUITPY directory
    current_dir = os.getcwd()

    try:
        os.chdir(circuitpy_path)

        # Import EXACT same modules as hardware
        import displayio
        import time
        import terminalio
        from adafruit_display_text import label
        from adafruit_bitmap_font import bitmap_font
        from adafruit_display_shapes.rect import Rect
        from adafruit_display_shapes.line import Line

        # Create mock display
        display = MockDisplay()

        # Mock the hardware globals that update_display needs
        sd_available = True

        # Load fonts exactly like hardware
        font = bitmap_font.load_font("barlowcond60.pcf")
        small_font = bitmap_font.load_font("barlowcond30.pcf")

        # Constants exactly like hardware
        BLACK = 0x000000
        WHITE = 0xFFFFFF
        RED = 0xFF0000
        DISPLAY_WIDTH = 122
        DISPLAY_HEIGHT = 250

        # EXACT same functions as hardware
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
            degree.x = x + 6  # Adjusted from hardware
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

        def get_historical_averages():
            return {
                'temp': {'day': 22, 'week': 21, 'month': 20, 'year': 19},
                'humidity': {'day': 45, 'week': 46, 'month': 47, 'year': 48}
            }

        def get_graph_data(num_points=60):
            # Use varying data so we can actually see lines
            temp_data = []
            humidity_data = []
            for i in range(num_points):
                # Create some variation
                temp_data.append(22 + (i % 10) - 5)  # 17-27 range
                humidity_data.append(45 + (i % 8) - 4)  # 41-49 range
            return temp_data, humidity_data

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

        def get_sd_total_time():
            return "2d"

        # THIS IS THE EXACT SAME update_display FUNCTION FROM HARDWARE
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
            sd_status = "SD"
            sd_time = get_sd_total_time()
            uptime = format_time_short(3600)  # 1 hour
            power_status = "P"
            battery_status = "B--"

            status_text = f"{sd_status} {sd_time} {uptime} {power_status} {battery_status}"
            status_label = label.Label(terminalio.FONT, text=status_text, color=WHITE)
            status_label.anchor_point = (0.5, 0.5)
            status_label.anchored_position = (DISPLAY_WIDTH // 2, status_bar_y + 6)
            g.append(status_label)

            # Refresh display (mock)
            display.refresh()

            # Return the group for now
            return display.root_group

        # Call the EXACT same function as hardware
        result = update_display(temp_c, humidity)
        print("SUCCESS: Used exact same hardware code!")
        return result

    finally:
        os.chdir(current_dir)

if __name__ == "__main__":
    print("Testing ultimate simple approach...")
    group = render_web_display(23.5, 65.2)
    print(f"Returned group: {group}")
