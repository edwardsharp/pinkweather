"""
Efficient CSV loading using existing open_meteo_converter
"""

import sys
from pathlib import Path

# Add preview directory to path for imports
preview_dir = Path(__file__).parent.parent
if str(preview_dir) not in sys.path:
    sys.path.insert(0, str(preview_dir))

from shared.open_meteo_converter import OpenMeteoConverter


class CSVWeatherLoader:
    """CSV loader using existing open-meteo converter"""

    def __init__(self, csv_file):
        self.csv_file = Path(csv_file)
        self.converter = OpenMeteoConverter(str(csv_file))
        print(f"Loaded Open-Meteo CSV from {csv_file}")

    def get_records(self, limit=None):
        """Get records as list of dicts, optionally limited"""
        try:
            # Parse CSV to get hourly data
            self.converter._parse_csv()

            if not self.converter.hourly_data:
                return []

            records = []
            for i, row in enumerate(self.converter.hourly_data):
                if limit and i >= limit:
                    break

                # Convert to timestamp and create record
                timestamp = self.converter._parse_timestamp(row["time"])
                if timestamp:
                    record = {
                        "timestamp": timestamp,
                        "temperature": self.converter._safe_float(
                            row.get("temperature_2m (°C)", 20)
                        ),
                        "humidity": self.converter._safe_int(
                            row.get("relative_humidity_2m (%)", 65)
                        ),
                        "weather_code": self.converter._safe_int(
                            row.get("weather_code (wmo code)", 0)
                        ),
                        "is_day": self.converter._safe_int(row.get("is_day ()", 1)),
                        "wind_speed": self.converter._safe_float(
                            row.get("wind_speed_10m (km/h)", 0)
                        ),
                        "description": "Clear sky",  # Will be generated from weather_code
                    }
                    records.append(record)

            print(f"Extracted {len(records)} records from CSV")
            return records

        except Exception as e:
            print(f"Error parsing CSV: {e}")
            return []

    def find_record_by_timestamp(self, target_timestamp, tolerance_seconds=1800):
        """Find record closest to target timestamp within tolerance"""
        try:
            # Use converter's existing method
            index = self.converter.find_closest_timestamp_index(target_timestamp)
            if index is not None:
                row = self.converter.hourly_data[index]
                timestamp = self.converter._parse_timestamp(row["time"])

                # Check tolerance
                if abs(timestamp - target_timestamp) <= tolerance_seconds:
                    return {
                        "timestamp": timestamp,
                        "temperature": self.converter._safe_float(
                            row.get("temperature_2m (°C)", 20)
                        ),
                        "humidity": self.converter._safe_int(
                            row.get("relative_humidity_2m (%)", 65)
                        ),
                        "weather_code": self.converter._safe_int(
                            row.get("weather_code (wmo code)", 0)
                        ),
                        "description": "Clear sky",
                    }
            return None
        except Exception:
            return None

    def _convert_openweather_to_intermediate_format(self, openweather_data):
        """Convert OpenWeatherMap API format to intermediate format expected by get_display_variables"""
        if not openweather_data or "list" not in openweather_data:
            return None

        forecast_items = openweather_data["list"]
        if not forecast_items:
            return None

        # Get current weather from first forecast item
        first_item = forecast_items[0]

        # Extract current weather data
        current_weather = {
            "current_temp": int(first_item["main"]["temp"]),
            "feels_like": int(first_item["main"]["feels_like"]),
            "high_temp": int(first_item["main"]["temp_max"]),
            "low_temp": int(first_item["main"]["temp_min"]),
            "weather_desc": first_item["weather"][0]["description"],
            "weather_icon": first_item["weather"][0]["icon"],
            "humidity": first_item["main"]["humidity"],
            "wind_speed": first_item["wind"]["speed"],
            "wind_gust": first_item["wind"].get("gust", 0),
            "current_timestamp": first_item["dt"],
        }

        # Add sunrise/sunset if available from city data
        if "city" in openweather_data and openweather_data["city"]:
            city = openweather_data["city"]
            if "sunrise" in city and "sunset" in city:
                current_weather["sunrise_timestamp"] = city["sunrise"]
                current_weather["sunset_timestamp"] = city["sunset"]

        # Convert forecast items to expected format
        forecast_data = []
        for item in forecast_items:
            forecast_item = {
                "dt": item["dt"],
                "temp": int(item["main"]["temp"]),
                "feels_like": int(item["main"]["feels_like"]),
                "icon": item["weather"][0]["icon"],
                "description": item["weather"][0]["description"],
                "pop": item.get("pop", 0),
            }
            forecast_data.append(forecast_item)

        return {
            "current": current_weather,
            "forecast": forecast_data,
            "city": openweather_data.get("city", {}),
        }

    def transform_record(self, record):
        """Transform CSV record to hardware module format using existing converter logic"""
        timestamp = int(record["timestamp"])

        try:
            # Use converter to get full weather data at this timestamp (OpenWeather API format)
            raw_weather_data = self.converter.get_data_at_timestamp(
                timestamp, hours_count=20
            )

            # Convert OpenWeatherMap format to intermediate format
            intermediate_data = self._convert_openweather_to_intermediate_format(
                raw_weather_data
            )
            if not intermediate_data:
                raise ValueError("Failed to convert OpenWeatherMap format")

            # Import weather_api module to process the data into display format
            hardware_path = preview_dir.parent / "300x400" / "CIRCUITPY"
            if str(hardware_path) not in sys.path:
                sys.path.insert(0, str(hardware_path))

            from weather import weather_api

            # Transform from intermediate format to display variables format
            display_data = weather_api.get_display_variables(intermediate_data)

            if display_data:
                return display_data
            else:
                # If transformation failed, fall back to basic format
                raise ValueError("Display data transformation failed")

        except Exception as e:
            print(f"Error transforming record: {e}")
            # Fallback transformation
            return {
                "current_timestamp": timestamp,
                "forecast_data": [
                    {"dt": timestamp + 3600, "temp": 20, "pop": 0.1, "icon": "01d"},
                    {"dt": timestamp + 7200, "temp": 22, "pop": 0.2, "icon": "02d"},
                ],
                "weather_desc": record.get("description", "Clear sky"),
                "day_name": "MON",
                "day_num": 15,
                "month_name": "DEC",
                "air_quality": {"aqi_text": "GOOD"},
                "zodiac_sign": "CAP",
                "indoor_temp_humidity": f"{record.get('temperature', 20):.0f}° 65%",
            }
