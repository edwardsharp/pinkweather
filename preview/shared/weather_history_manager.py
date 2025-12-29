"""
Efficient weather history handling for preview system
Handles both live API scenarios and bulk CSV processing
"""

import json
from pathlib import Path


class CSVHistoryDataSource:
    """Data source for weather history using CSV data"""

    def __init__(self, csv_loader):
        self.csv_loader = csv_loader
        self._in_memory_comparisons = {}

    def get_yesterday_data(self, current_timestamp):
        """Get yesterday's data from CSV historical context"""
        yesterday_timestamp = current_timestamp - 86400

        # Check if we have a pre-computed comparison
        if current_timestamp in self._in_memory_comparisons:
            comparison_data = self._in_memory_comparisons[current_timestamp]
            return {
                "current": comparison_data["yesterday_current"],
                "high": comparison_data["yesterday_current"],  # Simplified for now
                "low": comparison_data["yesterday_current"],  # Simplified for now
            }
        return None

    def store_today_data(self, timestamp, current_temp, high_temp, low_temp):
        """Store data - for CSV mode this is handled by compute_comparison"""
        return True  # Always succeeds in CSV mode

    def compute_comparison(self, current_timestamp, historical_context):
        """Compute and store comparison from historical context"""
        if not historical_context:
            return

        # Find yesterday's data (approximately 24 hours ago)
        yesterday_timestamp = current_timestamp - 86400
        yesterday_data = None

        for h in historical_context:
            h_timestamp = h.get("timestamp", 0)
            if abs(h_timestamp - yesterday_timestamp) < 3600:  # Within 1 hour
                yesterday_data = h
                break

        if not yesterday_data:
            return

        # Find current temperature
        current_temp = None
        for h in reversed(historical_context):
            h_timestamp = h.get("timestamp", 0)
            time_diff = abs(h_timestamp - current_timestamp)
            if time_diff < 1800:  # Within 30 min
                current_temp = h.get("temperature")
                break

        if current_temp is None:
            # If no exact match, use the most recent record in context
            if historical_context:
                last_record = historical_context[-1]
                current_temp = last_record.get("temperature")

        if current_temp is not None:
            yesterday_temp = yesterday_data.get("temperature", 20)

            # Import and use the existing comparison logic
            import sys
            from pathlib import Path

            hardware_path = (
                Path(__file__).parent.parent.parent / "300x400" / "CIRCUITPY"
            )
            if str(hardware_path) not in sys.path:
                sys.path.insert(0, str(hardware_path))

            from weather.weather_history import generate_temperature_comparison

            comparison = generate_temperature_comparison(current_temp, yesterday_temp)

            if comparison:
                self._in_memory_comparisons[current_timestamp] = {
                    "current": current_temp,
                    "yesterday_current": yesterday_temp,
                    "comparison": comparison,
                }

    def get_comparison(self, current_timestamp):
        """Get the computed comparison text"""
        if current_timestamp in self._in_memory_comparisons:
            return self._in_memory_comparisons[current_timestamp]["comparison"]
        return None


class WeatherHistoryManager:
    """Manages weather history data efficiently"""

    def __init__(self, csv_loader=None):
        self.csv_loader = csv_loader
        self.history_cache = {}  # In-memory cache for bulk processing
        self.csv_data_source = CSVHistoryDataSource(csv_loader) if csv_loader else None

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
        if not historical_context:
            return

        # Use the CSV data source to compute comparison
        if self.csv_data_source:
            self.csv_data_source.compute_comparison(
                current_timestamp, historical_context
            )

    def setup_csv_history_data_source(self):
        """Set up the CSV data source for weather history in the hardware module"""
        if self.csv_data_source:
            import sys
            from pathlib import Path

            hardware_path = (
                Path(__file__).parent.parent.parent / "300x400" / "CIRCUITPY"
            )
            if str(hardware_path) not in sys.path:
                sys.path.insert(0, str(hardware_path))

            from weather.weather_history import set_history_data_source

            set_history_data_source(self.csv_data_source)

    def get_in_memory_comparison(self, current_timestamp):
        """Get in-memory historical comparison for CSV batch mode"""
        if self.csv_data_source:
            return self.csv_data_source.get_comparison(current_timestamp)
        return None

    def clear_cache(self):
        """Clear history cache to free memory"""
        self.history_cache.clear()
        if self.csv_data_source:
            self.csv_data_source._in_memory_comparisons.clear()
