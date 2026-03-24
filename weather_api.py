"""
Weather data integration using OpenWeather API
"""
import requests
import logging
import json
import os
from typing import Dict, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)

# OpenWeather API Configuration
OPENWEATHER_API_KEY = "734e6e7554ce3f640d2690a14295e6f8"
OPENWEATHER_BASE_URL = "https://api.openweathermap.org/data/2.5"
OPENWEATHER_GEO_BASE_URL = "https://api.openweathermap.org/geo/1.0"
COWIN_LOCATION_BASE_URL = "https://cdn-api.co-vin.in/api/v2/admin/location"
INDIA_LOCATIONS_FILE = os.path.join(os.path.dirname(__file__), "india_locations.json")

# Simple in-memory cache to avoid repeated calls for static geography metadata.
_india_locations_cache: Optional[List[Dict]] = None


def _normalize_india_locations(india_payload: Dict) -> List[Dict]:
    """Normalize India locations payload to a flat state/UT list used by the UI."""
    result: List[Dict] = []

    india = india_payload.get("india", {}) if isinstance(india_payload, dict) else {}
    states = india.get("states", [])
    union_territories = india.get("union_territories", [])

    for item in states:
        state_name = item.get("state") or item.get("name")
        district_names = item.get("districts", [])
        if not state_name:
            continue

        districts = [
            {"district_id": idx + 1, "name": district_name}
            for idx, district_name in enumerate(district_names)
            if isinstance(district_name, str) and district_name.strip()
        ]

        result.append(
            {
                "state_id": None,
                "name": state_name,
                "region_type": "state",
                "districts": districts,
            }
        )

    for item in union_territories:
        ut_name = item.get("name") or item.get("state")
        district_names = item.get("districts", [])
        if not ut_name:
            continue

        districts = [
            {"district_id": idx + 1, "name": district_name}
            for idx, district_name in enumerate(district_names)
            if isinstance(district_name, str) and district_name.strip()
        ]

        result.append(
            {
                "state_id": None,
                "name": ut_name,
                "region_type": "union_territory",
                "districts": districts,
            }
        )

    result.sort(key=lambda item: (item.get("name") or "").lower())
    return result


def _load_india_locations_from_file() -> List[Dict]:
    """Load India locations from local JSON file if present."""
    if not os.path.exists(INDIA_LOCATIONS_FILE):
        return []

    try:
        with open(INDIA_LOCATIONS_FILE, "r", encoding="utf-8") as file:
            payload = json.load(file)

        return _normalize_india_locations(payload)
    except Exception as e:
        logger.error(f"Error reading local India locations file: {str(e)}")
        return []


def search_locations_in_india(query: str, limit: int = 20) -> List[Dict]:
    """
    Search available Indian locations using OpenWeather Geocoding API.

    Args:
        query: City or area name to search (for example, 'del', 'mumbai')
        limit: Maximum number of matching locations

    Returns:
        List of matching locations with coordinates
    """
    if not query:
        return []

    try:
        url = f"{OPENWEATHER_GEO_BASE_URL}/direct"

        params = {
            "q": f"{query},IN",
            "limit": max(1, min(limit, 50)),
            "appid": OPENWEATHER_API_KEY,
        }

        response = requests.get(url, params=params, timeout=10)
        if response.status_code != 200:
            logger.error(f"OpenWeather geocoding API error: {response.status_code}")
            return []

        locations = []
        for item in response.json():
            locations.append(
                {
                    "name": item.get("name"),
                    "state": item.get("state"),
                    "country": item.get("country"),
                    "latitude": item.get("lat"),
                    "longitude": item.get("lon"),
                }
            )

        return locations

    except Exception as e:
        logger.error(f"Error searching India locations: {str(e)}")
        return []


def get_india_states_and_districts(force_refresh: bool = False) -> List[Dict]:
    """
    Get all Indian states/UTs and their districts.

    Data source: CoWIN public location APIs.

    Args:
        force_refresh: If True, bypass cache and re-fetch from source API

    Returns:
        List of state dictionaries with district arrays
    """
    global _india_locations_cache

    if _india_locations_cache is not None and not force_refresh:
        return _india_locations_cache

    # Prefer local file data in the provided schema, if available.
    local_locations = _load_india_locations_from_file()
    if local_locations:
        _india_locations_cache = local_locations
        return local_locations

    try:
        headers = {
            "User-Agent": "organicfarming-weather-app/1.0",
            "Accept": "application/json",
        }

        states_response = requests.get(
            f"{COWIN_LOCATION_BASE_URL}/states",
            headers=headers,
            timeout=15,
        )
        if states_response.status_code != 200:
            logger.error(f"CoWIN states API error: {states_response.status_code}")
            return []

        states = states_response.json().get("states", [])
        result: List[Dict] = []

        for state in states:
            state_id = state.get("state_id")
            if state_id is None:
                continue

            districts_response = requests.get(
                f"{COWIN_LOCATION_BASE_URL}/districts/{state_id}",
                headers=headers,
                timeout=15,
            )
            if districts_response.status_code != 200:
                logger.error(
                    f"CoWIN districts API error for state_id {state_id}: {districts_response.status_code}"
                )
                districts = []
            else:
                districts = districts_response.json().get("districts", [])

            district_items = [
                {
                    "district_id": d.get("district_id"),
                    "name": d.get("district_name"),
                }
                for d in districts
                if d.get("district_name")
            ]

            result.append(
                {
                    "state_id": state_id,
                    "name": state.get("state_name"),
                    "region_type": "state",
                    "districts": district_items,
                }
            )

        result.sort(key=lambda item: (item.get("name") or "").lower())
        _india_locations_cache = result
        return result

    except Exception as e:
        logger.error(f"Error fetching India states/districts: {str(e)}")
        return []


def get_current_weather(latitude: float, longitude: float) -> Optional[Dict]:
    """
    Get current weather data for a location using OpenWeather API
    
    Args:
        latitude: Location latitude
        longitude: Location longitude
        
    Returns:
        Dictionary with weather information or None if API call fails
    """
    try:
        url = f"{OPENWEATHER_BASE_URL}/weather"
        
        params = {
            "lat": latitude,
            "lon": longitude,
            "appid": OPENWEATHER_API_KEY,
            "units": "metric"  # Use Celsius
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            return _parse_weather_response(data)
        else:
            logger.error(f"OpenWeather API error: {response.status_code}")
            
    except Exception as e:
        logger.error(f"Error fetching weather data: {str(e)}")
    
    return None


def get_weather_forecast(latitude: float, longitude: float, days: int = 7) -> Optional[Dict]:
    """
    Get weather forecast for multiple days
    
    Args:
        latitude: Location latitude
        longitude: Location longitude
        days: Number of days to forecast (1-7 for free tier)
        
    Returns:
        Dictionary with forecast data
    """
    try:
        url = f"{OPENWEATHER_BASE_URL}/forecast"
        
        params = {
            "lat": latitude,
            "lon": longitude,
            "appid": OPENWEATHER_API_KEY,
            "units": "metric",
            "cnt": days * 8  # 3-hour intervals, 8 per day
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            return _parse_forecast_response(data)
        else:
            logger.error(f"OpenWeather forecast API error: {response.status_code}")
            
    except Exception as e:
        logger.error(f"Error fetching forecast data: {str(e)}")
    
    return None


def _parse_weather_response(data: Dict) -> Dict:
    """
    Parse OpenWeather API response to extract useful information
    """
    try:
        weather = data.get("main", {})
        wind = data.get("wind", {})
        clouds = data.get("clouds", {})
        weather_desc = data.get("weather", [{}])[0]
        
        return {
            "location": {
                "city": data.get("name"),
                "country": data.get("sys", {}).get("country"),
                "latitude": data.get("coord", {}).get("lat"),
                "longitude": data.get("coord", {}).get("lon")
            },
            "current": {
                "temperature": weather.get("temp"),
                "feels_like": weather.get("feels_like"),
                "temp_min": weather.get("temp_min"),
                "temp_max": weather.get("temp_max"),
                "humidity": weather.get("humidity"),  # Percentage
                "pressure": weather.get("pressure"),  # hPa
                "description": weather_desc.get("main"),
                "details": weather_desc.get("description")
            },
            "wind": {
                "speed": wind.get("speed"),  # m/s
                "direction": wind.get("deg"),
                "gust": wind.get("gust")
            },
            "cloud_cover": clouds.get("all"),  # Percentage
            "visibility": data.get("visibility"),  # Meters
            "rainfall": data.get("rain", {}).get("1h"),  # Last 1 hour in mm
            "sunrise": datetime.fromtimestamp(data.get("sys", {}).get("sunrise", 0)).isoformat() if data.get("sys", {}).get("sunrise") else None,
            "sunset": datetime.fromtimestamp(data.get("sys", {}).get("sunset", 0)).isoformat() if data.get("sys", {}).get("sunset") else None,
            "timestamp": datetime.fromtimestamp(data.get("dt", 0)).isoformat() if data.get("dt") else None,
            "timezone": data.get("timezone")
        }
        
    except Exception as e:
        logger.error(f"Error parsing weather response: {str(e)}")
        return {}


def _parse_forecast_response(data: Dict) -> Dict:
    """
    Parse forecast response from OpenWeather API
    """
    try:
        forecasts = []
        
        for item in data.get("list", []):
            weather = item.get("main", {})
            weather_desc = item.get("weather", [{}])[0]
            wind = item.get("wind", {})
            
            forecast_item = {
                "timestamp": datetime.fromtimestamp(item.get("dt", 0)).isoformat(),
                "temperature": weather.get("temp"),
                "feels_like": weather.get("feels_like"),
                "humidity": weather.get("humidity"),
                "pressure": weather.get("pressure"),
                "description": weather_desc.get("main"),
                "details": weather_desc.get("description"),
                "wind_speed": wind.get("speed"),
                "wind_direction": wind.get("deg"),
                "cloud_cover": item.get("clouds", {}).get("all"),
                "rainfall": item.get("rain", {}).get("3h"),  # 3-hour forecast
                "visibility": item.get("visibility"),
                "rain_probability": item.get("pop") * 100 if item.get("pop") else 0  # Probability of precipitation
            }
            
            forecasts.append(forecast_item)
        
        return {
            "location": {
                "city": data.get("city", {}).get("name"),
                "country": data.get("city", {}).get("country"),
                "latitude": data.get("city", {}).get("coord", {}).get("lat"),
                "longitude": data.get("city", {}).get("coord", {}).get("lon")
            },
            "forecasts": forecasts,
            "count": len(forecasts)
        }
        
    except Exception as e:
        logger.error(f"Error parsing forecast response: {str(e)}")
        return {"forecasts": []}


def get_weather_for_farm(farm_data: Dict) -> Optional[Dict]:
    """
    Get weather information for a farm location
    
    Args:
        farm_data: Dictionary containing farm location information
                  Should have 'latitude' and 'longitude' keys
                  
    Returns:
        Weather data for the farm location
    """
    latitude = farm_data.get("latitude")
    longitude = farm_data.get("longitude")
    
    if not latitude or not longitude:
        logger.warning("No location data provided for farm weather")
        return None
    
    try:
        weather = get_current_weather(float(latitude), float(longitude))
        forecast = get_weather_forecast(float(latitude), float(longitude), days=7)
        
        return {
            "current": weather,
            "forecast": forecast
        }
        
    except Exception as e:
        logger.error(f"Error getting farm weather: {str(e)}")
        return None


def get_weather_by_city(city_name: str, country_code: str = None) -> Optional[Dict]:
    """
    Get weather by city name
    
    Args:
        city_name: Name of the city
        country_code: Optional ISO 3166 country code
        
    Returns:
        Weather data for the city
    """
    try:
        url = f"{OPENWEATHER_BASE_URL}/weather"
        
        # Construct query
        if country_code:
            query = f"{city_name},{country_code}"
        else:
            query = city_name
        
        params = {
            "q": query,
            "appid": OPENWEATHER_API_KEY,
            "units": "metric"
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            return _parse_weather_response(response.json())
        else:
            logger.error(f"Weather by city API error: {response.status_code}")
            
    except Exception as e:
        logger.error(f"Error fetching weather by city: {str(e)}")
    
    return None


def get_agricultural_weather_advisory(weather_data: Dict) -> Dict:
    """
    Generate agricultural advisory based on weather conditions
    
    Args:
        weather_data: Current weather data
        
    Returns:
        Advisory messages for farming operations
    """
    if not weather_data or "current" not in weather_data:
        return {}
    
    current = weather_data.get("current", {})
    advisories = []
    
    # Temperature advisories
    temp = current.get("temperature")
    if temp and temp > 35:
        advisories.append({
            "category": "Temperature",
            "alert": "HIGH",
            "message": f"High temperature ({temp}°C). Ensure proper irrigation and mulching.",
            "actions": ["Increase irrigation frequency", "Provide shade if needed", "Monitor soil moisture"]
        })
    elif temp and temp < 5:
        advisories.append({
            "category": "Temperature",
            "alert": "WARNING",
            "message": f"Low temperature ({temp}°C). Risk of frost damage.",
            "actions": ["Protect sensitive crops", "Avoid frost-prone areas", "Monitor weather updates"]
        })
    
    # Humidity advisories
    humidity = current.get("humidity")
    if humidity and humidity > 80:
        advisories.append({
            "category": "Humidity",
            "alert": "WARNING",
            "message": f"High humidity ({humidity}%). Increased disease risk.",
            "actions": ["Improve air circulation", "Avoid overhead watering", "Monitor for fungal diseases"]
        })
    
    # Rain advisories
    rainfall = current.get("rainfall")
    if rainfall and rainfall > 10:
        advisories.append({
            "category": "Rainfall",
            "alert": "INFO",
            "message": f"Recent rainfall ({rainfall}mm). Good for crops.",
            "actions": ["Reduce irrigation", "Monitor soil drainage", "Check for waterlogging"]
        })
    
    # Wind advisories
    wind_speed = current.get("wind", {}).get("speed")
    if wind_speed and wind_speed > 30:
        advisories.append({
            "category": "Wind",
            "alert": "WARNING",
            "message": f"Strong wind ({wind_speed} m/s). Risk to crops.",
            "actions": ["Stake tall crops", "Check for lodging", "Protect young plants"]
        })
    
    # Description-based advisories
    description = current.get("description", "").lower()
    if "rain" in description or "storm" in description:
        advisories.append({
            "category": "Severe Weather",
            "alert": "WARNING",
            "message": f"Severe weather expected: {current.get('details')}",
            "actions": ["Prepare field drainage", "Protect equipment", "Monitor weather updates"]
        })
    
    return {
        "timestamp": current.get("timestamp"),
        "location": weather_data.get("location"),
        "advisories": advisories,
        "total_alerts": len(advisories)
    }
