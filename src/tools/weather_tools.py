"""SiteNarrator — Weather data integration.

Fetches weather conditions from OpenWeatherMap API using project GPS coordinates.
Weather data is auto-injected into every report — Superintendents never need
to manually enter temperature, precipitation, or wind conditions.
"""

from __future__ import annotations

import requests

from src.config import get_settings
from src.tools.tracing import traced


@traced("weather.fetch")
def get_weather(lat: float, lon: float, date: str) -> dict:
    """Fetch weather data for a project location and date.

    Uses OpenWeatherMap API with GPS coordinates.
    Returns structured weather data for the report.

    Args:
        lat: Project site latitude
        lon: Project site longitude
        date: Report date (YYYY-MM-DD format)

    Returns:
        Dict with temp_high, temp_low, precipitation_mm, wind_kph,
        humidity, and conditions description.
    """
    settings = get_settings()
    api_key = settings.openweather_api_key

    # Use current weather endpoint (for today/recent dates)
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "lat": lat,
        "lon": lon,
        "appid": api_key,
        "units": "imperial",  # Fahrenheit for US construction
    }

    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()

    # Extract and structure weather data
    main = data.get("main", {})
    wind = data.get("wind", {})
    weather_desc = data.get("weather", [{}])[0]
    rain = data.get("rain", {})
    snow = data.get("snow", {})

    # Convert wind from m/s to kph
    wind_speed_kph = wind.get("speed", 0) * 3.6

    # Precipitation: rain or snow in last 1h/3h
    precip_mm = rain.get("1h", rain.get("3h", 0)) + snow.get(
        "1h", snow.get("3h", 0)
    )

    return {
        "temp_high": main.get("temp_max", 0),
        "temp_low": main.get("temp_min", 0),
        "precipitation_mm": round(precip_mm, 1),
        "wind_kph": round(wind_speed_kph, 1),
        "humidity": main.get("humidity", 0),
        "conditions": weather_desc.get("description", "clear"),
    }
