"""
Common weather data model for all providers
Keeps API-specific details contained within provider modules
"""

from utils.logger import log


class WeatherData:
    """Standard weather data model used throughout application"""

    def __init__(self):
        # Current conditions
        self.current_temp = 0.0
        self.current_humidity = 0.0
        self.current_description = ""
        self.current_icon = "01d"

        # Forecast data
        self.forecast = []  # List of ForecastData objects

        # Additional metadata
        self.timestamp = 0
        self.location = ""

    def to_display_format(self):
        """Convert to format expected by display modules"""
        return {
            "current_timestamp": self.timestamp,
            "forecast_data": [f.to_dict() for f in self.forecast],
            "weather_desc": self.current_description,
            "day_name": "FRI",  # TODO: calculate from timestamp
            "day_num": 27,  # TODO: calculate from timestamp
            "month_name": "DEC",  # TODO: calculate from timestamp
            "air_quality": {"aqi_text": "GOOD"},
            "zodiac_sign": "CAP",
            "indoor_temp_humidity": f"{self.current_temp:.0f}°{self.current_humidity:.0f}%",
        }


class ForecastData:
    """Single forecast data point"""

    def __init__(self):
        self.dt = 0  # Timestamp
        self.temp = 0.0  # Temperature
        self.pop = 0.0  # Precipitation probability (0.0-1.0)
        self.icon = "01d"  # Weather icon code

    def to_dict(self):
        return {"dt": self.dt, "temp": self.temp, "pop": self.pop, "icon": self.icon}


class APIValidator:
    """Simple validator following existing code patterns"""

    def __init__(self, data, source_name):
        self.data = data
        self.source = source_name

    def require(self, key):
        """Get required field, raise if missing"""
        if key not in self.data:
            raise KeyError(f"Required field '{key}' missing from {self.source}")
        return self.data[key]

    def optional(self, key, fallback=None):
        """Get optional field with fallback and logging"""
        if key in self.data:
            return self.data[key]
        else:
            if fallback is not None:
                # Import here to avoid circular imports
                try:
                    log(
                        f"Missing '{key}' from {self.source}, using fallback: {fallback}"
                    )
                except ImportError:
                    print(
                        f"Missing '{key}' from {self.source}, using fallback: {fallback}"
                    )
            return fallback
