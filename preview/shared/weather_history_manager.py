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

    def get_history_for_csv_record(self, record, timestamp):
        """Get efficient history data for CSV batch processing"""
        if self.csv_loader is None:
            return {}

        # Use efficient lookups instead of recomputing each time
        cache_key = f"history_{timestamp}"
        if cache_key in self.history_cache:
            return self.history_cache[cache_key]

        # Compute history efficiently
        history_data = self._compute_csv_history(record, timestamp)
        self.history_cache[cache_key] = history_data

        return history_data

    def _compute_csv_history(self, record, timestamp):
        """Efficiently compute history from CSV data"""
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

    def clear_cache(self):
        """Clear history cache to free memory"""
        self.history_cache.clear()
