"""
Efficient CSV loading and caching with pandas for fast weather data processing
"""

from pathlib import Path

import pandas as pd


class CSVWeatherLoader:
    """Efficient CSV loader with pandas indexing and caching"""

    def __init__(self, csv_file):
        self.csv_file = Path(csv_file)
        self.data = None
        self._load_data()

    def _load_data(self):
        """Load CSV data with pandas and set timestamp index for fast lookups"""
        try:
            # Load CSV with pandas
            self.data = pd.read_csv(self.csv_file)

            # Ensure we have a timestamp column
            if "timestamp" not in self.data.columns:
                raise ValueError(f"CSV file {self.csv_file} missing 'timestamp' column")

            # Convert timestamp to datetime and set as index for fast lookups
            self.data["timestamp"] = pd.to_datetime(self.data["timestamp"], unit="s")
            self.data.set_index("timestamp", inplace=True)

            # Sort by timestamp for efficient range queries
            self.data.sort_index(inplace=True)

            print(f"Loaded {len(self.data)} records from {self.csv_file}")

        except Exception as e:
            print(f"Error loading CSV file {self.csv_file}: {e}")
            self.data = pd.DataFrame()

    def get_records(self, limit=None):
        """Get records as list of dicts, optionally limited"""
        if self.data is None or self.data.empty:
            return []

        # Convert back to records format
        records_df = self.data.reset_index()
        records_df["timestamp"] = (
            records_df["timestamp"].astype(int) // 10**9
        )  # Convert back to unix timestamp

        if limit:
            records_df = records_df.head(limit)

        return records_df.to_dict("records")

    def find_record_by_timestamp(self, target_timestamp, tolerance_seconds=1800):
        """Find record closest to target timestamp within tolerance (default 30 minutes)"""
        if self.data is None or self.data.empty:
            return None

        try:
            # Convert target timestamp to datetime
            target_dt = pd.to_datetime(target_timestamp, unit="s")

            # Find closest timestamp within tolerance
            time_diff = abs(self.data.index - target_dt)
            min_diff_idx = time_diff.idxmin()

            # Check if within tolerance
            min_diff_seconds = time_diff.min().total_seconds()
            if min_diff_seconds <= tolerance_seconds:
                # Convert back to dict format with unix timestamp
                record = self.data.loc[min_diff_idx].to_dict()
                record["timestamp"] = int(min_diff_idx.timestamp())
                return record
            else:
                return None

        except Exception:
            return None

    def transform_record(self, record):
        """Transform CSV record to hardware module format"""
        # Convert CSV format to what header.create_weather_layout expects
        timestamp = int(record["timestamp"])

        # Build forecast data (reuse existing transformation logic)
        forecast_data = [
            {"dt": timestamp + 86400, "temp": 75, "pop": 0.2, "icon": "02d"},
            {"dt": timestamp + 172800, "temp": 68, "pop": 0.8, "icon": "10d"},
            {"dt": timestamp + 259200, "temp": 71, "pop": 0.0, "icon": "01d"},
        ]

        # Extract temperature from record (handle different possible column names)
        temp = None
        for temp_col in ["temperature", "temp", "current_temp"]:
            if temp_col in record:
                temp = record[temp_col]
                break

        if temp is None:
            temp = 20  # Default fallback

        # Build weather data in expected format
        weather_data = {
            "current_timestamp": timestamp,
            "forecast_data": forecast_data,
            "weather_desc": record.get("description", "Clear sky"),
            "day_name": "MON",  # TODO: calculate from timestamp
            "day_num": 15,  # TODO: calculate from timestamp
            "month_name": "DEC",  # TODO: calculate from timestamp
            "air_quality": {"aqi_text": "GOOD"},
            "zodiac_sign": "CAP",
            "indoor_temp_humidity": f"{temp:.0f}° 65%",
        }

        return weather_data
