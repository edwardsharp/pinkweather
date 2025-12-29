"""
Efficient weather history handling for preview system
Handles both live API scenarios and bulk CSV processing
"""

import json
from pathlib import Path


class WeatherHistoryManager:
    """Manages weather history data efficiently"""

    def __init__(self, csv_loader=None):
        self.csv_loader = csv_loader
        self.history_cache = {}  # In-memory cache for bulk processing

    def get_history_for_live_preview(self, current_weather_data):
        """Get mock history data for live API preview"""
        # For live preview, create reasonable mock history
        # based on current conditions

        current_temp = current_weather_data.get("current_temp", 20)  # Celsius

        return {
            "yesterday_high": current_temp + 3,
            "yesterday_low": current_temp - 5,
            "last_week_avg": current_temp - 1,
            "comparison": "warmer than yesterday",
        }

    def get_history_for_csv_record(self, record, timestamp, historical_context=None):
        """Get efficient history data for CSV batch processing with enhanced context"""
        if self.csv_loader is None:
            return {}

        # Use efficient lookups instead of recomputing each time
        cache_key = f"history_{timestamp}"
        if cache_key in self.history_cache:
            return self.history_cache[cache_key]

        # Compute history efficiently with enhanced context
        history_data = self._compute_csv_history_enhanced(
            record, timestamp, historical_context
        )
        self.history_cache[cache_key] = history_data

        # Inject historical data into weather history system for narrative comparisons
        self._inject_historical_data_for_comparisons(timestamp, historical_context)

        return history_data

    def _compute_csv_history_enhanced(self, record, timestamp, historical_context=None):
        """Efficiently compute enhanced history from CSV data with lookback context"""
        current_temp = record.get("temperature", 20)

        # If we have historical context (previous 10 hours), use it for richer comparisons
        if historical_context and len(historical_context) > 0:
            # Get temperature trends from historical context
            temps = [h.get("temperature", 20) for h in historical_context]

            # Find yesterday's data (around 24 hours ago)
            yesterday_temp = None
            for h in reversed(historical_context):
                h_timestamp = h.get("timestamp", timestamp)
                if (
                    abs(h_timestamp - (timestamp - 86400)) < 3600
                ):  # Within 1 hour of 24h ago
                    yesterday_temp = h.get("temperature")
                    break

            # Calculate trends and averages
            if len(temps) >= 6:  # At least 6 hours of data
                recent_avg = sum(temps[-6:]) / 6  # Last 6 hours average
                earlier_avg = (
                    sum(temps[:6]) / min(6, len(temps[:6]))
                    if len(temps) > 6
                    else recent_avg
                )
                trend = (
                    "warming"
                    if recent_avg > earlier_avg
                    else "cooling"
                    if recent_avg < earlier_avg
                    else "stable"
                )
            else:
                recent_avg = sum(temps) / len(temps) if temps else current_temp
                trend = "stable"

            # Generate comparison text
            if yesterday_temp:
                temp_diff = current_temp - yesterday_temp
                if temp_diff > 2:
                    comparison = f"much warmer than yesterday (+{temp_diff:.1f}°)"
                elif temp_diff > 0.5:
                    comparison = f"warmer than yesterday (+{temp_diff:.1f}°)"
                elif temp_diff < -2:
                    comparison = f"much cooler than yesterday ({temp_diff:.1f}°)"
                elif temp_diff < -0.5:
                    comparison = f"cooler than yesterday ({temp_diff:.1f}°)"
                else:
                    comparison = "similar to yesterday"
            else:
                comparison = f"temperature trending {trend}"

            return {
                "yesterday_high": yesterday_temp if yesterday_temp else current_temp,
                "yesterday_low": yesterday_temp - 5
                if yesterday_temp
                else current_temp - 5,
                "last_week_avg": recent_avg,
                "comparison": comparison,
                "trend": trend,
                "historical_temps": temps[-6:],  # Last 6 hours for context
            }
        else:
            # Fallback to simpler computation if no historical context
            return self._compute_csv_history_fallback(record, timestamp)

    def _compute_csv_history_fallback(self, record, timestamp):
        """Fallback computation when no historical context is available"""
        # Find yesterday's data efficiently
        yesterday_timestamp = timestamp - 86400  # 24 hours ago

        # Use efficient pandas operations if available
        if hasattr(self.csv_loader, "find_record_by_timestamp"):
            yesterday_record = self.csv_loader.find_record_by_timestamp(
                yesterday_timestamp
            )
        else:
            # Fallback to basic lookup
            yesterday_record = None

        if yesterday_record:
            return {
                "yesterday_high": yesterday_record.get("temperature", 20),
                "yesterday_low": yesterday_record.get("temperature", 15),
                "last_week_avg": record.get("temperature", 18),
                "comparison": "similar to yesterday",
            }
        else:
            # No yesterday data available
            return {
                "yesterday_high": record.get("temperature", 20),
                "yesterday_low": record.get("temperature", 15),
                "last_week_avg": record.get("temperature", 18),
                "comparison": "no comparison data",
            }

    def _inject_historical_data_for_comparisons(
        self, current_timestamp, historical_context
    ):
        """Inject historical data into weather history system for narrative comparisons"""
        # print(
        #     f"DEBUG: _inject_historical_data_for_comparisons called with {len(historical_context) if historical_context else 0} records"
        # )
        if not historical_context:
            # print("DEBUG: No historical context, returning")
            return

        try:
            # Import weather history functions
            import sys
            from pathlib import Path

            # Add hardware path for weather history imports
            hardware_path = (
                Path(__file__).parent.parent.parent / "300x400" / "CIRCUITPY"
            )
            if str(hardware_path) not in sys.path:
                sys.path.insert(0, str(hardware_path))

            from weather.weather_history import (
                get_date_string,
                store_today_temperatures,
            )

            # Store yesterday's data if available (look for data ~24 hours ago)
            yesterday_timestamp = current_timestamp - 86400
            yesterday_data = None

            # print(
            #     f"DEBUG: Looking for yesterday timestamp {yesterday_timestamp} (24h before {current_timestamp})"
            # )
            # print(f"DEBUG: Historical context timestamps:")
            for i, h in enumerate(historical_context):
                h_timestamp = h.get("timestamp", 0)
                diff_hours = (current_timestamp - h_timestamp) / 3600
                # print(f"  [{i}] timestamp={h_timestamp}, diff={diff_hours:.1f}h ago")

            # Find closest historical record to yesterday
            for h in historical_context:
                h_timestamp = h.get("timestamp", 0)
                if abs(h_timestamp - yesterday_timestamp) < 3600:  # Within 1 hour
                    yesterday_data = h
                    # print(f"DEBUG: Found yesterday data! timestamp={h_timestamp}")
                    break

            # if not yesterday_data:
            #     print("DEBUG: No yesterday data found in historical context")

            if yesterday_data:
                # Store yesterday's REAL temperature data
                yesterday_temp = yesterday_data.get("temperature", 20)

                # Calculate REAL high/low from ALL yesterday's historical data
                yesterday_day_start = yesterday_timestamp - (
                    yesterday_timestamp % 86400
                )
                yesterday_day_end = yesterday_day_start + 86400

                yesterday_temps = []
                for h in historical_context:
                    h_timestamp = h.get("timestamp", 0)
                    if yesterday_day_start <= h_timestamp < yesterday_day_end:
                        yesterday_temps.append(h.get("temperature", yesterday_temp))

                if yesterday_temps:
                    high_temp = max(yesterday_temps)
                    low_temp = min(yesterday_temps)
                else:
                    # Fallback to current temp if no daily data available
                    high_temp = yesterday_temp
                    low_temp = yesterday_temp

                # Store using the weather history system
                # print(
                #     f"DEBUG: About to inject - yesterday_temp={yesterday_temp}, high={high_temp}, low={low_temp}, timestamp={yesterday_timestamp}"
                # )
                store_today_temperatures(
                    yesterday_timestamp, yesterday_temp, high_temp, low_temp
                )
                # print(f"DEBUG: Injection completed")

        except Exception as e:
            # Show injection errors for debugging
            # print(f"DEBUG: History injection failed: {e}")
            import traceback

            traceback.print_exc()

    def clear_cache(self):
        """Clear history cache to free memory"""
        self.history_cache.clear()
