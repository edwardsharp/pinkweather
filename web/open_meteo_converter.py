"""
Open-Meteo CSV to OpenWeatherMap API format converter
Integrates with existing mock weather data system for web preview
"""

import csv
import json
import os
from datetime import datetime


class OpenMeteoConverter:
    """Convert Open-Meteo CSV data to OpenWeatherMap API format"""

    def __init__(self, csv_filepath, city_name=None, lat=None, lon=None):
        self.csv_filepath = csv_filepath
        self.hourly_data = []
        self.daily_data = []
        self._parsed = False

        # Extract city info from filepath or use provided values
        if city_name and lat and lon:
            self.city_name = city_name
            self.lat = lat
            self.lon = lon
        else:
            self._extract_location_from_filepath()

        # WMO weather code to OpenWeatherMap icon/description mapping
        self.wmo_to_openweather = {
            0: {
                "description": "clear sky",
                "icon_day": "01d",
                "icon_night": "01n",
                "main": "Clear",
            },
            1: {
                "description": "mainly clear",
                "icon_day": "01d",
                "icon_night": "01n",
                "main": "Clear",
            },
            2: {
                "description": "partly cloudy",
                "icon_day": "02d",
                "icon_night": "02n",
                "main": "Clouds",
            },
            3: {
                "description": "overcast",
                "icon_day": "04d",
                "icon_night": "04n",
                "main": "Clouds",
            },
            45: {
                "description": "fog",
                "icon_day": "50d",
                "icon_night": "50n",
                "main": "Fog",
            },
            48: {
                "description": "depositing rime fog",
                "icon_day": "50d",
                "icon_night": "50n",
                "main": "Fog",
            },
            51: {
                "description": "light drizzle",
                "icon_day": "09d",
                "icon_night": "09n",
                "main": "Drizzle",
            },
            53: {
                "description": "moderate drizzle",
                "icon_day": "09d",
                "icon_night": "09n",
                "main": "Drizzle",
            },
            55: {
                "description": "dense drizzle",
                "icon_day": "09d",
                "icon_night": "09n",
                "main": "Drizzle",
            },
            56: {
                "description": "light freezing drizzle",
                "icon_day": "09d",
                "icon_night": "09n",
                "main": "Drizzle",
            },
            57: {
                "description": "dense freezing drizzle",
                "icon_day": "09d",
                "icon_night": "09n",
                "main": "Drizzle",
            },
            61: {
                "description": "slight rain",
                "icon_day": "10d",
                "icon_night": "10n",
                "main": "Rain",
            },
            63: {
                "description": "moderate rain",
                "icon_day": "10d",
                "icon_night": "10n",
                "main": "Rain",
            },
            65: {
                "description": "heavy rain",
                "icon_day": "10d",
                "icon_night": "10n",
                "main": "Rain",
            },
            66: {
                "description": "light freezing rain",
                "icon_day": "13d",
                "icon_night": "13n",
                "main": "Rain",
            },
            67: {
                "description": "heavy freezing rain",
                "icon_day": "13d",
                "icon_night": "13n",
                "main": "Rain",
            },
            71: {
                "description": "slight snow fall",
                "icon_day": "13d",
                "icon_night": "13n",
                "main": "Snow",
            },
            73: {
                "description": "moderate snow fall",
                "icon_day": "13d",
                "icon_night": "13n",
                "main": "Snow",
            },
            75: {
                "description": "heavy snow fall",
                "icon_day": "13d",
                "icon_night": "13n",
                "main": "Snow",
            },
            77: {
                "description": "snow grains",
                "icon_day": "13d",
                "icon_night": "13n",
                "main": "Snow",
            },
            80: {
                "description": "slight rain showers",
                "icon_day": "09d",
                "icon_night": "09n",
                "main": "Rain",
            },
            81: {
                "description": "moderate rain showers",
                "icon_day": "09d",
                "icon_night": "09n",
                "main": "Rain",
            },
            82: {
                "description": "violent rain showers",
                "icon_day": "09d",
                "icon_night": "09n",
                "main": "Rain",
            },
            85: {
                "description": "slight snow showers",
                "icon_day": "13d",
                "icon_night": "13n",
                "main": "Snow",
            },
            86: {
                "description": "heavy snow showers",
                "icon_day": "13d",
                "icon_night": "13n",
                "main": "Snow",
            },
            95: {
                "description": "slight thunderstorm",
                "icon_day": "11d",
                "icon_night": "11n",
                "main": "Thunderstorm",
            },
            96: {
                "description": "thunderstorm with slight hail",
                "icon_day": "11d",
                "icon_night": "11n",
                "main": "Thunderstorm",
            },
            99: {
                "description": "thunderstorm with heavy hail",
                "icon_day": "11d",
                "icon_night": "11n",
                "main": "Thunderstorm",
            },
        }

    def _parse_csv(self):
        """Parse the Open-Meteo CSV file into hourly and daily data sections"""
        if self._parsed:
            return

        with open(self.csv_filepath, "r", encoding="utf-8") as f:
            content = f.read()

        lines = content.strip().split("\n")
        current_section = None

        for line in lines:
            if not line.strip():
                continue

            # Detect section type by header
            if line.startswith("time,temperature_2m"):
                current_section = "hourly"
                hourly_reader = csv.DictReader([line])
                hourly_fieldnames = hourly_reader.fieldnames
                continue
            elif line.startswith("time,sunrise"):
                current_section = "daily"
                daily_reader = csv.DictReader([line])
                daily_fieldnames = daily_reader.fieldnames
                continue

            # Parse data based on current section
            if current_section == "hourly":
                try:
                    row_dict = dict(zip(hourly_fieldnames, line.split(",")))
                    self.hourly_data.append(row_dict)
                except:
                    continue
            elif current_section == "daily":
                try:
                    row_dict = dict(zip(daily_fieldnames, line.split(",")))
                    self.daily_data.append(row_dict)
                except:
                    continue

        self._parsed = True

    def _extract_location_from_filepath(self):
        """Extract location info from Open-Meteo filename pattern"""
        filename = os.path.basename(self.csv_filepath)

        # Parse pattern: open-meteo-LAT.DDN/SLON.DDW/EELEVm.csv
        if "40.65N73.98W" in filename:
            self.city_name = "New York"
            self.lat = 40.65
            self.lon = -73.98
        elif "43.70N79.40W" in filename:
            self.city_name = "Toronto"
            self.lat = 43.70
            self.lon = -79.40
        else:
            # Default fallback
            self.city_name = "Unknown"
            self.lat = 40.0
            self.lon = -74.0

    def _get_weather_condition(self, wmo_code, is_day):
        """Convert WMO weather code to OpenWeather format"""
        try:
            code = int(float(wmo_code))
        except (ValueError, TypeError):
            code = 0  # Default to clear sky

        weather_info = self.wmo_to_openweather.get(code, self.wmo_to_openweather[0])

        return {
            "id": code + 800,  # Offset to avoid conflicts with OpenWeather IDs
            "main": weather_info["main"],
            "description": weather_info["description"],
            "icon": weather_info["icon_day"] if is_day else weather_info["icon_night"],
        }

    def _parse_timestamp(self, time_str):
        """Convert Open-Meteo timestamp to Unix timestamp"""
        try:
            # Handle both "2024-01-01T00:00" and "2024-01-01" formats
            if "T" in time_str:
                dt = datetime.fromisoformat(time_str)
            else:
                dt = datetime.fromisoformat(f"{time_str}T00:00")
            return int(dt.timestamp())
        except:
            return 0

    def _safe_float(self, value, default=0.0):
        """Safely convert string to float, handling NaN and empty values"""
        try:
            if value.lower() in ("nan", "", "null"):
                return default
            return float(value)
        except (ValueError, AttributeError):
            return default

    def _safe_int(self, value, default=0):
        """Safely convert string to int, handling NaN and empty values"""
        try:
            if value.lower() in ("nan", "", "null"):
                return default
            return int(float(value))
        except (ValueError, AttributeError):
            return default

    def find_closest_timestamp_index(self, target_timestamp):
        """Find the index of the hourly data closest to target timestamp"""
        self._parse_csv()

        if not self.hourly_data:
            return 0

        best_index = 0
        best_diff = float("inf")

        for i, row in enumerate(self.hourly_data):
            row_timestamp = self._parse_timestamp(row["time"])
            diff = abs(row_timestamp - target_timestamp)
            if diff < best_diff:
                best_diff = diff
                best_index = i

        return best_index

    def get_data_at_timestamp(self, base_timestamp, hours_count=40):
        """Get weather data starting from closest timestamp to base_timestamp"""
        self._parse_csv()

        if not self.hourly_data:
            raise ValueError("No hourly data found in CSV")

        # Find starting point
        start_index = self.find_closest_timestamp_index(base_timestamp)

        # Get forecast items
        forecast_items = []
        end_index = min(start_index + hours_count, len(self.hourly_data))

        for i in range(start_index, end_index):
            row = self.hourly_data[i]

            timestamp = self._parse_timestamp(row["time"])
            temp = self._safe_float(row["temperature_2m (°C)"])
            feels_like = self._safe_float(row["apparent_temperature (°C)"])
            humidity = self._safe_int(row["relative_humidity_2m (%)"])
            wind_speed = self._safe_float(row["wind_speed_10m (km/h)"])
            wind_gust = self._safe_float(row["wind_gusts_10m (km/h)"])
            weather_code = self._safe_int(row["weather_code (wmo code)"])
            is_day = self._safe_int(row["is_day ()"]) == 1
            cloud_cover = self._safe_int(row["cloud_cover (%)"])
            visibility = self._safe_float(row["visibility (m)"], 10000)

            # Convert weather condition
            weather_condition = self._get_weather_condition(weather_code, is_day)

            # Build forecast item in OpenWeather format
            item = {
                "dt": timestamp,
                "main": {
                    "temp": temp,
                    "feels_like": feels_like,
                    "temp_min": temp,  # Use actual temp as requested
                    "temp_max": temp,  # Use actual temp as requested
                    "pressure": 1013,  # Default atmospheric pressure
                    "sea_level": 1013,
                    "grnd_level": 1013,
                    "humidity": humidity,
                    "temp_kf": 0,
                },
                "weather": [weather_condition],
                "clouds": {"all": cloud_cover},
                "wind": {
                    "speed": wind_speed
                    / 3.6,  # Convert km/h to m/s to match OpenWeather
                    "deg": 0,  # Wind direction not available in Open-Meteo data
                    "gust": wind_gust / 3.6,  # Convert km/h to m/s
                },
                "visibility": int(visibility),
                "pop": 0,  # Precipitation probability - could be enhanced from daily data
                "sys": {"pod": "d" if is_day else "n"},
                "dt_txt": datetime.fromtimestamp(timestamp).strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
            }

            # Add precipitation data if present
            rain = self._safe_float(row["rain (mm)"])
            snow = self._safe_float(row["snowfall (cm)"])
            if rain > 0:
                item["rain"] = {"3h": rain}
            if snow > 0:
                item["snow"] = {"3h": snow}

            forecast_items.append(item)

        # Get sunrise/sunset from daily data for the start date
        sunrise_ts = sunset_ts = None
        if self.daily_data and forecast_items:
            start_date = datetime.fromtimestamp(forecast_items[0]["dt"]).date()

            for daily_row in self.daily_data:
                try:
                    daily_date = datetime.fromisoformat(daily_row["time"]).date()
                    if daily_date == start_date:
                        sunrise_ts = self._parse_timestamp(
                            daily_row["sunrise (iso8601)"]
                        )
                        sunset_ts = self._parse_timestamp(daily_row["sunset (iso8601)"])
                        break
                except:
                    continue

        # Default sunrise/sunset if not found (approximate NYC winter times)
        if not sunrise_ts or not sunset_ts:
            start_dt = (
                datetime.fromtimestamp(forecast_items[0]["dt"])
                if forecast_items
                else datetime.now()
            )
            start_date = start_dt.date()
            sunrise_ts = int(
                datetime.combine(start_date, datetime.min.time())
                .replace(hour=7, minute=19)
                .timestamp()
            )
            sunset_ts = int(
                datetime.combine(start_date, datetime.min.time())
                .replace(hour=17, minute=38)
                .timestamp()
            )

        # Build city data using detected location
        city_id = 5128581 if self.city_name == "New York" else 6167865  # Toronto
        country = "US" if self.city_name == "New York" else "CA"
        population = 8175133 if self.city_name == "New York" else 2930000
        timezone_offset = -18000 if self.city_name == "New York" else -18000  # Both EST

        city_data = {
            "id": city_id,
            "name": self.city_name,
            "coord": {"lat": self.lat, "lon": self.lon},
            "country": country,
            "population": population,
            "timezone": timezone_offset,
            "sunrise": sunrise_ts,
            "sunset": sunset_ts,
        }

        # Return OpenWeather API format
        return {
            "cod": "200",
            "message": 0,
            "cnt": len(forecast_items),
            "list": forecast_items,
            "city": city_data,
        }

    def get_data_range(self):
        """Get the first and last timestamps available in the data"""
        self._parse_csv()

        if not self.hourly_data:
            return None, None

        first_ts = self._parse_timestamp(self.hourly_data[0]["time"])
        last_ts = self._parse_timestamp(self.hourly_data[-1]["time"])

        return first_ts, last_ts


# Global converter instances (initialized when first needed)
_converters = {}


def get_converter(dataset="ny_2024"):
    """Get or create converter instance for specified dataset"""
    global _converters
    if dataset not in _converters:
        if dataset == "ny_2024":
            csv_path = os.path.join(
                os.path.dirname(__file__), "../misc/open-meteo-40.65N73.98W25m.csv"
            )
            city_info = ("New York", 40.65, -73.98)
        elif dataset == "toronto_2025":
            csv_path = os.path.join(
                os.path.dirname(__file__), "../misc/open-meteo-43.70N79.40W165m.csv"
            )
            city_info = ("Toronto", 43.70, -79.40)
        else:
            print(f"Unknown dataset: {dataset}")
            return None

        if os.path.exists(csv_path):
            _converters[dataset] = OpenMeteoConverter(csv_path, *city_info)
        else:
            print(f"Warning: Open-Meteo CSV not found at {csv_path}")
            _converters[dataset] = None
    return _converters[dataset]


def generate_historical_weather_data(base_timestamp, dataset="ny_2024"):
    """Generate weather data from historical CSV for given timestamp

    This function integrates with the existing mock_weather_data.py system
    """
    converter = get_converter(dataset)
    if not converter:
        # Fallback to synthetic data if CSV not available
        from mock_weather_data import MockWeatherGenerator

        generator = MockWeatherGenerator(base_timestamp)
        return generator.generate_mock_forecast("winter_clear")

    # Generate weather data for the requested timestamp
    weather_data = converter.get_data_at_timestamp(base_timestamp)

    # Also generate and store yesterday's weather history for narrative comparisons
    _store_yesterday_history(converter, base_timestamp)

    return weather_data


def _store_yesterday_history(converter, current_timestamp):
    """Store yesterday's weather data in history for narrative comparisons"""
    try:
        # Calculate yesterday's timestamp (24 hours ago)
        yesterday_timestamp = current_timestamp - 86400

        # Get yesterday's weather data from CSV
        yesterday_data = converter.get_data_at_timestamp(
            yesterday_timestamp, hours_count=24
        )

        if not yesterday_data or not yesterday_data.get("list"):
            return

        # Extract temperatures from yesterday's data
        yesterday_items = yesterday_data["list"]
        temps = [item["main"]["temp"] for item in yesterday_items]

        if not temps:
            return

        # Calculate yesterday's stats
        current_temp = yesterday_items[0]["main"]["temp"]  # First item as "current"
        high_temp = max(temps)
        low_temp = min(temps)

        # Store in weather history using the same system as the narrative
        import os
        import sys

        # Add CircuitPython path for weather_history import
        circuitpy_path = os.path.join(
            os.path.dirname(__file__), "..", "300x400", "CIRCUITPY"
        )
        if circuitpy_path not in sys.path:
            sys.path.insert(0, circuitpy_path)

        from weather_history import store_today_temperatures

        # Store yesterday's data as if it were "today" at that time
        store_today_temperatures(yesterday_timestamp, current_temp, high_temp, low_temp)

        print(
            f"DEBUG: Stored yesterday's history - temp: {current_temp}°, high: {high_temp}°, low: {low_temp}°"
        )

    except Exception as e:
        print(f"Warning: Could not store yesterday's history: {e}")


def get_historical_data_range(dataset="ny_2024"):
    """Get the available timestamp range for historical data"""
    converter = get_converter(dataset)
    if not converter:
        return None, None
    return converter.get_data_range()
