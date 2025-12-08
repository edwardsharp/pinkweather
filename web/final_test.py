#!/usr/bin/env python3
"""
Final test - render the actual hardware display output to PNG using fixed renderer
This uses the exact same shared code as the hardware.
"""

import sys
import os

# Add CIRCUITPY to path
circuitpy_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'CIRCUITPY')
sys.path.insert(0, circuitpy_path)

from debug_renderer import render_displayio_group_to_image

def render_hardware_display_final():
    """Use the exact hardware update_display function with fixed renderer"""

    # Change to CIRCUITPY directory for font loading
    current_dir = os.getcwd()

    try:
        os.chdir(circuitpy_path)

        # Import exactly the same modules as hardware
        import displayio
        import time
        import terminalio
        from adafruit_display_text import label
        from adafruit_bitmap_font import bitmap_font
        from adafruit_display_shapes.rect import Rect
        from adafruit_display_shapes.line import Line

        # Load fonts exactly like hardware
        font = bitmap_font.load_font("barlowcond60.pcf")
        small_font = bitmap_font.load_font("barlowcond30.pcf")

        # Constants exactly like hardware
        BLACK = 0x000000
        WHITE = 0xFFFFFF
        RED = 0xFF0000
        DISPLAY_WIDTH = 122
        DISPLAY_HEIGHT = 250

        # EXACT same helper functions from hardware
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
            degree.x = x + 6
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
            # Generate realistic test data with variation
            import math
            temp_data = []
            humidity_data = []
            for i in range(num_points):
                # Create sine wave with noise for temperature (18-26°C range)
                temp = 22 + 4 * math.sin(i * 0.3) + (i % 3) - 1
                temp_data.append(max(18, min(26, temp)))

                # Create different pattern for humidity (40-60% range)
                humidity = 50 + 8 * math.cos(i * 0.2) + (i % 5) - 2
                humidity_data.append(max(40, min(60, humidity)))

            return temp_data, humidity_data

        def create_line_graph(data_points, color, y_start, height):
            if len(data_points) < 2:
                return displayio.Group()

            group = displayio.Group()
            graph_width = DISPLAY_WIDTH - 20  # Leave margins
            x_step = graph_width // (len(data_points) - 1) if len(data_points) > 1 else 0

            min_val = min(data_points)
            max_val = max(data_points)
            val_range = max_val - min_val if max_val != min_val else 1

            for i in range(len(data_points) - 1):
                x1 = 10 + i * x_step
                x2 = 10 + (i + 1) * x_step

                y1 = y_start + height - int(((data_points[i] - min_val) / val_range) * height)
                y2 = y_start + height - int(((data_points[i + 1] - min_val) / val_range) * height)

                # Draw thick lines (2px thick)
                line1 = Line(x1, y1, x2, y2, color)
                line2 = Line(x1, y1 + 1, x2, y2 + 1, color)
                group.append(line1)
                group.append(line2)

            # Min/max labels with backgrounds
            max_bg = Rect(0, y_start - 2, 22, 14, fill=color, outline=color)
            group.append(max_bg)
            max_label = label.Label(terminalio.FONT, text=f"{int(max_val)}", color=WHITE)
            max_label.x = 2
            max_label.y = y_start + 5
            group.append(max_label)

            min_bg = Rect(0, y_start + height - 12, 22, 14, fill=color, outline=color)
            group.append(min_bg)
            min_label = label.Label(terminalio.FONT, text=f"{int(min_val)}", color=WHITE)
            min_label.x = 2
            min_label.y = y_start + height - 5
            group.append(min_label)

            return group

        def get_sd_total_time():
            return "3d"

        # THIS IS THE EXACT update_display FUNCTION FROM HARDWARE
        def update_display(temp_c, humidity):
            # Create main group
            g = displayio.Group()

            # Background
            bg = Rect(0, 0, DISPLAY_WIDTH, DISPLAY_HEIGHT, fill=WHITE)
            g.append(bg)

            # Get historical averages and graph data
            averages = get_historical_averages()
            temp_data, humidity_data = get_graph_data()

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

            # Temperature line graph
            temp_y_start = 84
            temp_height = 32
            temp_border = Rect(0, temp_y_start - 2, DISPLAY_WIDTH, temp_height + 4, outline=BLACK, stroke=2, fill=WHITE)
            g.append(temp_border)
            temp_graph = create_line_graph(temp_data, BLACK, temp_y_start, temp_height)
            g.append(temp_graph)

            # Humidity line graph
            humidity_y_start = 124
            humidity_height = 32
            humidity_border = Rect(0, humidity_y_start - 2, DISPLAY_WIDTH, humidity_height + 4, outline=RED, stroke=2, fill=WHITE)
            g.append(humidity_border)
            humidity_graph = create_line_graph(humidity_data, RED, humidity_y_start, humidity_height)
            g.append(humidity_graph)

            # Humidity averages
            humidity_avg_text = f"D:{averages['humidity']['day']} W:{averages['humidity']['week']} M:{averages['humidity']['month']} Y:{averages['humidity']['year']}"
            humidity_avg_label = label.Label(terminalio.FONT, text=humidity_avg_text, color=RED)
            humidity_avg_label.anchor_point = (0.5, 0.5)
            humidity_avg_label.anchored_position = (DISPLAY_WIDTH // 2, humidity_y_start + humidity_height + 10)
            g.append(humidity_avg_label)

            # Current humidity (bottom area)
            humidity_group = create_humidity_display(humidity)
            humidity_group.x = 20
            humidity_group.y = humidity_y_start + humidity_height + 38
            g.append(humidity_group)

            # Status bar at bottom
            status_bar_height = 12
            status_bar_y = DISPLAY_HEIGHT - status_bar_height
            status_bar = Rect(0, status_bar_y, DISPLAY_WIDTH, status_bar_height, fill=BLACK)
            g.append(status_bar)

            # Status text
            sd_status = "SD"
            sd_time = get_sd_total_time()
            uptime = format_time_short(7200)  # 2 hours
            power_status = "P"
            battery_status = "B85"

            status_text = f"{sd_status} {sd_time} {uptime} {power_status} {battery_status}"
            status_label = label.Label(terminalio.FONT, text=status_text, color=WHITE)
            status_label.anchor_point = (0.5, 0.5)
            status_label.anchored_position = (DISPLAY_WIDTH // 2, status_bar_y + 6)
            g.append(status_label)

            return g

        # Test with realistic values
        print("Creating hardware display with temp=24.3°C, humidity=58%...")
        display_group = update_display(24.3, 58.0)

        print(f"Created display group with {len(display_group)} items")

    finally:
        os.chdir(current_dir)

    # Render to PNG with our fixed renderer
    print("Rendering display group to PNG...")
    image = render_displayio_group_to_image(display_group, debug=False)

    # Save the final result
    image.save("final_hardware_display.png")
    print("SUCCESS! Saved final_hardware_display.png")

    # Also save a debug version
    debug_image = render_displayio_group_to_image(display_group, debug=True)
    debug_image.save("final_hardware_display_debug.png")
    print("Also saved final_hardware_display_debug.png with debug info")

    return image


if __name__ == "__main__":
    print("=== FINAL TEST: Hardware Display Rendering ===")
    render_hardware_display_final()
    print("Done! Check final_hardware_display.png for the result.")
