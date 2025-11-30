"""
Weather API Integration Example

This example shows how to integrate with OpenWeatherMap API
and use the display renderer for a complete weather station.
"""

import json
import time
from display_renderer import WeatherDisplayRenderer

# Mock weather data for testing (replace with actual API calls)
SAMPLE_WEATHER_DATA = {
    "main": {
        "temp": 72.5,
        "humidity": 65,
        "feels_like": 75.2
    },
    "weather": [
        {
            "main": "Clear",
            "description": "clear sky",
            "icon": "01d"
        }
    ],
    "wind": {
        "speed": 5.2,
        "deg": 315
    },
    "sys": {
        "sunrise": 1640962800,
        "sunset": 1640996400
    },
    "name": "San Francisco"
}

class WeatherStation:
    def __init__(self, api_key=None, location="San Francisco,US"):
        """
        Initialize weather station.

        Args:
            api_key (str): OpenWeatherMap API key
            location (str): Location for weather data
        """
        self.api_key = api_key
        self.location = location
        self.renderer = WeatherDisplayRenderer()

    def fetch_weather_data(self):
        """
        Fetch weather data from OpenWeatherMap API.
        Returns mock data if no API key is provided.
        """
        if not self.api_key:
            print("Using mock weather data (no API key provided)")
            return SAMPLE_WEATHER_DATA

        # TODO: Implement actual API call when ready
        # import requests
        # url = f"http://api.openweathermap.org/data/2.5/weather"
        # params = {
        #     "q": self.location,
        #     "appid": self.api_key,
        #     "units": "imperial"
        # }
        # response = requests.get(url, params=params)
        # return response.json()

        return SAMPLE_WEATHER_DATA

    def format_temperature(self, temp_f):
        """Format temperature for display."""
        return f"{int(temp_f)}°F"

    def format_wind(self, speed_mph, direction_deg):
        """Format wind information."""
        # Convert wind direction to cardinal direction
        directions = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                     "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
        direction_idx = int((direction_deg + 11.25) / 22.5) % 16
        direction = directions[direction_idx]

        return f"{int(speed_mph)}mph {direction}"

    def format_time(self, timestamp):
        """Format timestamp for display."""
        return time.strftime("%I:%M %p", time.localtime(timestamp))

    def create_weather_display(self):
        """Create weather display image."""
        try:
            weather_data = self.fetch_weather_data()

            # Extract data
            temp = weather_data["main"]["temp"]
            condition = weather_data["weather"][0]["main"]
            humidity = weather_data["main"]["humidity"]
            wind_speed = weather_data["wind"]["speed"]
            wind_dir = weather_data["wind"]["deg"]
            location = weather_data["name"]

            # Format display data
            temperature = self.format_temperature(temp)
            wind_info = self.format_wind(wind_speed, wind_dir)

            # Additional info
            additional_info = f"Humidity: {humidity}%\nWind: {wind_info}"

            # Add sunrise/sunset if available
            if "sys" in weather_data:
                sunrise = self.format_time(weather_data["sys"]["sunrise"])
                sunset = self.format_time(weather_data["sys"]["sunset"])
                additional_info += f"\nSunrise: {sunrise}\nSunset: {sunset}"

            # Create display
            image = self.renderer.render_weather_layout(
                temperature=temperature,
                condition=condition,
                location=location,
                additional_info=additional_info
            )

            return image

        except Exception as e:
            # Fallback error display
            error_info = {
                "Error": str(e),
                "Time": time.strftime("%I:%M %p"),
                "Status": "Weather Unavailable"
            }
            return self.renderer.render_debug_display(error_info)

    def create_text_display(self, message):
        """Create simple text display."""
        return self.renderer.render_text_display(message, "Weather Station")

def main():
    """Example usage of weather station."""
    # Initialize weather station
    # For actual use, provide your OpenWeatherMap API key:
    # station = WeatherStation(api_key="your_api_key_here", location="your_city,country")
    station = WeatherStation()

    print("Generating weather display...")

    # Generate weather display
    weather_image = station.create_weather_display()

    # Save preview (helpful for development)
    weather_image.save("weather_preview.png")
    print("Weather preview saved as weather_preview.png")

    # Example of text display
    text_message = "Weather station initialized. Waiting for data updates..."
    text_image = station.create_text_display(text_message)
    text_image.save("text_preview.png")
    print("Text preview saved as text_preview.png")

if __name__ == "__main__":
    main()
