"""
Mock weather data generator for testing weather narratives and display layouts.
Generates realistic OpenWeather API-format data for different seasons and conditions.
"""

import json
import random
import time
from datetime import datetime, timedelta


class MockWeatherGenerator:
    """Generate realistic mock weather data for testing"""

    def __init__(self, base_timestamp=None):
        """Initialize with required base timestamp - no system time allowed"""
        if base_timestamp is None:
            raise ValueError("base_timestamp must be provided - no system time allowed")
        self.base_timestamp = base_timestamp

        # Season-appropriate temperature ranges (Celsius)
        self.season_temps = {
            "winter": {"day": (-15, 2), "night": (-25, -5)},
            "spring": {"day": (5, 18), "night": (-2, 8)},
            "summer": {"day": (18, 32), "night": (12, 22)},
            "fall": {"day": (2, 15), "night": (-5, 5)},
        }

        # Weather condition templates
        self.weather_conditions = {
            "clear": {
                "id": 800,
                "main": "Clear",
                "description": "clear sky",
                "icon_day": "01d",
                "icon_night": "01n",
            },
            "few_clouds": {
                "id": 801,
                "main": "Clouds",
                "description": "few clouds",
                "icon_day": "02d",
                "icon_night": "02n",
            },
            "scattered_clouds": {
                "id": 802,
                "main": "Clouds",
                "description": "scattered clouds",
                "icon_day": "03d",
                "icon_night": "03n",
            },
            "overcast": {
                "id": 804,
                "main": "Clouds",
                "description": "overcast clouds",
                "icon_day": "04d",
                "icon_night": "04n",
            },
            "light_rain": {
                "id": 500,
                "main": "Rain",
                "description": "light rain",
                "icon_day": "10d",
                "icon_night": "10n",
            },
            "moderate_rain": {
                "id": 501,
                "main": "Rain",
                "description": "moderate rain",
                "icon_day": "10d",
                "icon_night": "10n",
            },
            "heavy_rain": {
                "id": 502,
                "main": "Rain",
                "description": "heavy intensity rain",
                "icon_day": "10d",
                "icon_night": "10n",
            },
            "light_snow": {
                "id": 600,
                "main": "Snow",
                "description": "light snow",
                "icon_day": "13d",
                "icon_night": "13n",
            },
            "moderate_snow": {
                "id": 601,
                "main": "Snow",
                "description": "snow",
                "icon_day": "13d",
                "icon_night": "13n",
            },
            "heavy_snow": {
                "id": 602,
                "main": "Snow",
                "description": "heavy snow",
                "icon_day": "13d",
                "icon_night": "13n",
            },
            "mist": {
                "id": 701,
                "main": "Mist",
                "description": "mist",
                "icon_day": "50d",
                "icon_night": "50n",
            },
            "fog": {
                "id": 741,
                "main": "Fog",
                "description": "fog",
                "icon_day": "50d",
                "icon_night": "50n",
            },
            "thunderstorm": {
                "id": 200,
                "main": "Thunderstorm",
                "description": "thunderstorm with light rain",
                "icon_day": "11d",
                "icon_night": "11n",
            },
        }

        # Season-appropriate weather probabilities
        self.season_weather_probs = {
            "winter": {
                "clear": 0.15,
                "few_clouds": 0.1,
                "scattered_clouds": 0.1,
                "overcast": 0.2,
                "light_snow": 0.15,
                "moderate_snow": 0.1,
                "heavy_snow": 0.05,
                "mist": 0.05,
                "fog": 0.1,
                "light_rain": 0.0,
                "moderate_rain": 0.0,
                "heavy_rain": 0.0,
                "thunderstorm": 0.0,
            },
            "spring": {
                "clear": 0.2,
                "few_clouds": 0.15,
                "scattered_clouds": 0.15,
                "overcast": 0.15,
                "light_rain": 0.15,
                "moderate_rain": 0.1,
                "heavy_rain": 0.02,
                "light_snow": 0.03,
                "moderate_snow": 0.02,
                "heavy_snow": 0.01,
                "mist": 0.02,
                "fog": 0.0,
                "thunderstorm": 0.0,
            },
            "summer": {
                "clear": 0.35,
                "few_clouds": 0.25,
                "scattered_clouds": 0.15,
                "overcast": 0.05,
                "light_rain": 0.1,
                "moderate_rain": 0.05,
                "heavy_rain": 0.02,
                "thunderstorm": 0.03,
                "light_snow": 0.0,
                "moderate_snow": 0.0,
                "heavy_snow": 0.0,
                "mist": 0.0,
                "fog": 0.0,
            },
            "fall": {
                "clear": 0.15,
                "few_clouds": 0.1,
                "scattered_clouds": 0.15,
                "overcast": 0.25,
                "light_rain": 0.15,
                "moderate_rain": 0.1,
                "heavy_rain": 0.05,
                "light_snow": 0.02,
                "moderate_snow": 0.01,
                "heavy_snow": 0.0,
                "mist": 0.02,
                "fog": 0.0,
                "thunderstorm": 0.0,
            },
        }

    def get_season_from_timestamp(self, timestamp):
        """Determine season from timestamp"""
        dt = datetime.fromtimestamp(timestamp)
        month = dt.month

        if month in [12, 1, 2]:
            return "winter"
        elif month in [3, 4, 5]:
            return "spring"
        elif month in [6, 7, 8]:
            return "summer"
        else:
            return "fall"

    def is_daytime(self, timestamp, sunrise_ts, sunset_ts):
        """Check if timestamp is during daytime"""
        return sunrise_ts <= timestamp <= sunset_ts

    def generate_weather_condition(self, season, is_day=True):
        """Generate a weather condition based on season and time of day"""
        probs = self.season_weather_probs[season]

        # Weighted random selection
        conditions = list(probs.keys())
        weights = list(probs.values())
        condition_key = random.choices(conditions, weights=weights)[0]

        base_condition = self.weather_conditions[condition_key]

        # Create OpenWeather API format - just id, main, description, icon
        condition = {
            "id": base_condition["id"],
            "main": base_condition["main"],
            "description": base_condition["description"],
            "icon": base_condition["icon_day"]
            if is_day
            else base_condition["icon_night"],
        }

        return condition

    def generate_temperature(self, season, is_day=True, base_temp=None):
        """Generate realistic temperature for season and time"""
        temp_range = self.season_temps[season]["day" if is_day else "night"]

        if base_temp is not None:
            # Vary around base temperature
            temp = base_temp + random.uniform(-3, 3)
        else:
            temp = random.uniform(temp_range[0], temp_range[1])

        return round(temp, 1)

    def generate_precipitation_data(self, weather_condition, intensity_factor=1.0):
        """Generate precipitation amounts based on weather condition"""
        data = {}

        if "rain" in weather_condition["main"].lower():
            if "light" in weather_condition["description"]:
                amount = random.uniform(0.1, 1.0) * intensity_factor
            elif "heavy" in weather_condition["description"]:
                amount = random.uniform(2.0, 8.0) * intensity_factor
            else:  # moderate
                amount = random.uniform(1.0, 3.0) * intensity_factor
            data["rain"] = {"3h": round(amount, 2)}

        elif "snow" in weather_condition["main"].lower():
            if "light" in weather_condition["description"]:
                amount = random.uniform(0.1, 2.0) * intensity_factor
            elif "heavy" in weather_condition["description"]:
                amount = random.uniform(5.0, 15.0) * intensity_factor
            else:  # moderate
                amount = random.uniform(2.0, 6.0) * intensity_factor
            data["snow"] = {"3h": round(amount, 2)}

        return data

    def generate_forecast_item(
        self, timestamp, season, weather_condition=None, base_temp=None
    ):
        """Generate a single forecast item"""
        # Calculate sunrise/sunset (approximations)
        dt = datetime.fromtimestamp(timestamp)
        sunrise_hour = 6 + (
            2 if season in ["winter", "fall"] else -1 if season == "summer" else 0
        )
        sunset_hour = 18 + (
            -2 if season in ["winter", "fall"] else 2 if season == "summer" else 0
        )

        sunrise_ts = int(
            datetime(dt.year, dt.month, dt.day, sunrise_hour, 30).timestamp()
        )
        sunset_ts = int(datetime(dt.year, dt.month, dt.day, sunset_hour, 0).timestamp())

        is_day = self.is_daytime(timestamp, sunrise_ts, sunset_ts)

        if weather_condition is None:
            weather_condition = self.generate_weather_condition(season, is_day)

        temp = self.generate_temperature(season, is_day, base_temp)
        feels_like = temp + random.uniform(-5, 2)  # Wind chill or heat index effect

        # Probability of precipitation
        if any(
            word in weather_condition["main"].lower()
            for word in ["rain", "snow", "thunderstorm"]
        ):
            pop = random.uniform(0.4, 0.9)
        elif "cloud" in weather_condition["main"].lower():
            pop = random.uniform(0.0, 0.3)
        else:
            pop = random.uniform(0.0, 0.1)

        item = {
            "dt": timestamp,
            "main": {
                "temp": temp,  # Use Celsius to match API with units=metric
                "feels_like": feels_like,
                "temp_min": temp - random.uniform(1, 3),
                "temp_max": temp + random.uniform(1, 4),
                "pressure": random.randint(990, 1030),
                "sea_level": random.randint(990, 1030),
                "grnd_level": random.randint(985, 1025),
                "humidity": random.randint(30, 90),
                "temp_kf": random.uniform(-2, 2),
            },
            "weather": [weather_condition],
            "clouds": {"all": random.randint(0, 100)},
            "wind": {
                "speed": random.uniform(0, 15),
                "deg": random.randint(0, 360),
                "gust": random.uniform(0, 20),
            },
            "visibility": random.randint(5000, 10000),
            "pop": pop,
            "sys": {"pod": "d" if is_day else "n"},
            "dt_txt": datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S"),
        }

        # Add precipitation data if applicable
        precip_data = self.generate_precipitation_data(weather_condition)
        item.update(precip_data)

        return item

    def generate_mock_forecast(self, scenario="winter_storm", hours_ahead=40):
        """Generate complete mock forecast data"""
        current_time = self.base_timestamp
        season = self.get_season_from_timestamp(current_time)

        # Override season for specific scenarios
        if "winter" in scenario:
            season = "winter"
        elif "summer" in scenario:
            season = "summer"
        elif "spring" in scenario:
            season = "spring"
        elif "fall" in scenario:
            season = "fall"

        forecast_items = []

        # Generate forecast items every 3 hours
        for i in range(hours_ahead // 3):
            item_timestamp = current_time + (i * 3 * 3600)

            # Apply scenario-specific weather patterns
            # Determine if it's daytime for proper icon selection
            dt = datetime.fromtimestamp(item_timestamp)
            sunrise_hour = 6 + (
                2 if season in ["winter", "fall"] else -1 if season == "summer" else 0
            )
            sunset_hour = 18 + (
                -2 if season in ["winter", "fall"] else 2 if season == "summer" else 0
            )
            is_day = sunrise_hour <= dt.hour <= sunset_hour

            if scenario == "winter_storm":
                if i < 3:
                    # Start overcast
                    base_condition = self.weather_conditions["overcast"]
                elif i < 6:
                    # Light snow begins
                    base_condition = self.weather_conditions["light_snow"]
                else:
                    # Heavy snow develops
                    base_condition = self.weather_conditions["heavy_snow"]

                # Convert to proper API format with correct icon
                condition = {
                    "id": base_condition["id"],
                    "main": base_condition["main"],
                    "description": base_condition["description"],
                    "icon": base_condition["icon_day"]
                    if is_day
                    else base_condition["icon_night"],
                }
            elif scenario == "summer_heat":
                base_condition = self.weather_conditions["clear"]
                condition = {
                    "id": base_condition["id"],
                    "main": base_condition["main"],
                    "description": base_condition["description"],
                    "icon": base_condition["icon_day"]
                    if is_day
                    else base_condition["icon_night"],
                }
            elif scenario == "spring_rain":
                if i < 4:
                    base_condition = self.weather_conditions["scattered_clouds"]
                else:
                    base_condition = self.weather_conditions["moderate_rain"]

                condition = {
                    "id": base_condition["id"],
                    "main": base_condition["main"],
                    "description": base_condition["description"],
                    "icon": base_condition["icon_day"]
                    if is_day
                    else base_condition["icon_night"],
                }
            else:
                condition = (
                    None  # Let it be random (will use generate_weather_condition)
                )

            base_temp = (
                -8 if "winter" in scenario else 25 if "summer" in scenario else None
            )
            item = self.generate_forecast_item(
                item_timestamp, season, condition, base_temp
            )
            forecast_items.append(item)

        # Create city data
        city_data = {
            "id": 5128581,
            "name": "New York",
            "coord": {"lat": 40.7128, "lon": -74.0060},
            "country": "US",
            "population": 8175133,
            "timezone": -18000,
            "sunrise": current_time - (current_time % 86400) + (7 * 3600),  # 7 AM
            "sunset": current_time - (current_time % 86400) + (17 * 3600),  # 5 PM
        }

        return {
            "cod": "200",
            "message": 0,
            "cnt": len(forecast_items),
            "list": forecast_items,
            "city": city_data,
        }


def get_predefined_scenarios():
    """Get list of predefined weather scenarios for testing"""
    return {
        "ny_2024": "New York 2024 Historical Data",
        "toronto_2025": "Toronto 2025 Historical Data",
        "winter_clear": "Clear winter day, very cold",
        "winter_storm": "Developing winter storm with heavy snow",
        "winter_mixed": "Mixed winter conditions",
        "spring_mild": "Mild spring day with some clouds",
        "spring_rain": "Spring rain developing",
        "spring_variable": "Variable spring conditions",
        "summer_hot": "Hot summer day",
        "summer_storms": "Summer thunderstorms",
        "summer_humid": "Humid summer conditions",
        "fall_crisp": "Crisp fall day",
        "fall_rain": "Fall rain and wind",
        "fall_variable": "Variable fall conditions",
    }


def generate_scenario_data(scenario_name, base_timestamp=None):
    """Generate mock data for a specific scenario"""
    # Handle historical data scenarios
    if scenario_name in ["ny_2024", "toronto_2025"]:
        try:
            from open_meteo_converter import generate_historical_weather_data

            forecast_data = generate_historical_weather_data(
                base_timestamp, scenario_name
            )

            # Add fake air quality data for testing
            fake_air_quality_data = {
                "list": [
                    {
                        "main": {"aqi": 2},  # Fair air quality
                        "components": {
                            "co": 233.5,
                            "no": 0.12,
                            "no2": 19.2,
                            "o3": 51.3,
                            "so2": 4.1,
                            "pm2_5": 7.2,
                            "pm10": 10.5,
                            "nh3": 1.8,
                        },
                    }
                ]
            }

            # Return data in new format with both forecast and air quality
            return {"forecast": forecast_data, "air_quality": fake_air_quality_data}

        except ImportError:
            print(
                "Warning: Could not import open_meteo_converter, falling back to synthetic data"
            )
            # Fall back to winter scenario
            scenario_name = "winter_clear"

    generator = MockWeatherGenerator(base_timestamp)
    forecast_data = generator.generate_mock_forecast(scenario_name)

    # Add fake air quality data for synthetic scenarios too
    fake_air_quality_data = {
        "list": [
            {
                "main": {"aqi": 1},  # Good air quality for synthetic data
                "components": {
                    "co": 200.0,
                    "no": 0.0,
                    "no2": 15.5,
                    "o3": 45.2,
                    "so2": 2.8,
                    "pm2_5": 5.1,
                    "pm10": 7.3,
                    "nh3": 1.2,
                },
            }
        ]
    }

    return {"forecast": forecast_data, "air_quality": fake_air_quality_data}


# Test function
if __name__ == "__main__":
    # Generate sample data for testing
    generator = MockWeatherGenerator()
    sample_data = generator.generate_mock_forecast("winter_storm")

    print("Generated sample winter storm data:")
    print(f"City: {sample_data['city']['name']}")
    print(f"Number of forecast items: {len(sample_data['list'])}")
    print(
        f"First item: {sample_data['list'][0]['dt_txt']} - {sample_data['list'][0]['weather'][0]['description']}"
    )
