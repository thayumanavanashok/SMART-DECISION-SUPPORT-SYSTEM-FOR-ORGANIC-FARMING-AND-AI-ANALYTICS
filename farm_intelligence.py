import datetime
import json
import os
from urllib.parse import quote_plus

import requests
from market_scraper import scrape_market_prices

try:
    import google.generativeai as genai
except Exception:
    genai = None


def _safe_float(value, fallback=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _season_from_month(month):
    if month in (3, 4, 5):
        return "summer"
    if month in (6, 7, 8, 9):
        return "monsoon"
    if month in (10, 11):
        return "post-monsoon"
    return "winter"


def _estimate_market_window(crop_name, season):
    crop = (crop_name or "").lower()

    high_demand = {
        "tomato": "Sell in early morning at local market for better freshness premium.",
        "onion": "Store in ventilated shade and wait for stable weekly rates.",
        "rice": "Compare mandi rates for 7 days before bulk sale.",
        "wheat": "Plan sale after moisture-safe storage to avoid distress pricing.",
        "millet": "Target health-food buyers and farmer collectives for better margin.",
        "turmeric": "Cure and dry properly before sale to increase value.",
    }

    if crop in high_demand:
        return high_demand[crop]

    seasonal_hint = {
        "summer": "Harvest early to avoid heat stress and quality loss.",
        "monsoon": "Use short storage buffers because wet markets can delay transport.",
        "post-monsoon": "Sort produce by grade and sell in batches for better pricing.",
        "winter": "Use dry storage and monitor weekly demand spikes in nearby mandis.",
    }
    return seasonal_hint.get(season, "Track weekly mandi rates and stagger selling over 2 to 3 rounds.")


def _risk_level(score):
    if score >= 75:
        return "low"
    if score >= 50:
        return "moderate"
    return "high"


def geocode_location(location):
    if not location:
        return None

    url = (
        "https://geocoding-api.open-meteo.com/v1/search?name="
        + quote_plus(location)
        + "&count=1&language=en&format=json"
    )

    try:
        response = requests.get(url, timeout=8)
        response.raise_for_status()
        data = response.json()
        results = data.get("results") or []
        if not results:
            return None

        first = results[0]
        return {
            "name": first.get("name", location),
            "country": first.get("country", "India"),
            "latitude": first.get("latitude"),
            "longitude": first.get("longitude"),
        }
    except Exception:
        return None


def fetch_weather_snapshot(latitude, longitude):
    if latitude is None or longitude is None:
        return None

    weather_url = (
        "https://api.open-meteo.com/v1/forecast?"
        f"latitude={latitude}&longitude={longitude}"
        "&current=temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m"
        "&daily=temperature_2m_max,temperature_2m_min,precipitation_sum"
        "&timezone=auto&forecast_days=5"
    )

    try:
        response = requests.get(weather_url, timeout=8)
        response.raise_for_status()
        payload = response.json()

        current = payload.get("current", {})
        daily = payload.get("daily", {})
        dates = daily.get("time", [])

        forecast = []
        for idx, day in enumerate(dates):
            forecast.append(
                {
                    "date": day,
                    "temp_max": (daily.get("temperature_2m_max") or [None])[idx],
                    "temp_min": (daily.get("temperature_2m_min") or [None])[idx],
                    "rain_mm": (daily.get("precipitation_sum") or [0])[idx],
                }
            )

        return {
            "current": {
                "temperature_c": current.get("temperature_2m"),
                "humidity_pct": current.get("relative_humidity_2m"),
                "precipitation_mm": current.get("precipitation"),
                "wind_kmph": current.get("wind_speed_10m"),
            },
            "forecast": forecast,
        }
    except Exception:
        return None


def estimate_crop_health(farm_data):
    issues = (farm_data.get("issues") or "").strip().lower()
    soil = (farm_data.get("soilType") or "").lower()
    water = (farm_data.get("waterAvailability") or "").lower()
    soil_ph = _safe_float(farm_data.get("soilPH"), 7.0)

    score = 78
    alerts = []

    if "disease" in issues or "fung" in issues:
        score -= 20
        alerts.append("Disease-like symptoms reported")
    if "pest" in issues or "insect" in issues:
        score -= 15
        alerts.append("Pest pressure risk detected")
    if "yellow" in issues or "wilting" in issues:
        score -= 10
        alerts.append("Possible nutrient or moisture stress")

    if soil == "sandy":
        score -= 5
        alerts.append("Sandy soil may require frequent organic moisture support")
    if water == "limited":
        score -= 8
        alerts.append("Limited water availability can reduce crop vigor")
    if soil_ph < 5.5 or soil_ph > 8.0:
        score -= 7
        alerts.append("Soil pH appears outside optimal range for many crops")

    score = max(20, min(96, score))

    return {
        "health_score": score,
        "risk_level": _risk_level(score),
        "alerts": alerts,
    }


def build_unified_farm_context(farm_data):
    now = datetime.datetime.now()
    season = _season_from_month(now.month)

    location_data = geocode_location(farm_data.get("location"))
    weather_data = None
    if location_data:
        weather_data = fetch_weather_snapshot(location_data.get("latitude"), location_data.get("longitude"))

    crop_health = estimate_crop_health(farm_data)

    if weather_data and weather_data.get("forecast"):
        total_rain = sum(day.get("rain_mm", 0) or 0 for day in weather_data["forecast"])
        avg_max_temp = sum(day.get("temp_max", 0) or 0 for day in weather_data["forecast"]) / max(
            len(weather_data["forecast"]), 1
        )
    else:
        total_rain = None
        avg_max_temp = None

    decision_score = 100
    if crop_health["risk_level"] == "high":
        decision_score -= 35
    elif crop_health["risk_level"] == "moderate":
        decision_score -= 20

    if total_rain is not None and total_rain > 70:
        decision_score -= 10
    if avg_max_temp is not None and avg_max_temp > 35:
        decision_score -= 8

    decision_score = max(25, min(95, int(decision_score)))

    data_sources = {
        "soil_profile": {
            "available": True,
            "fields": [
                "soil_type",
                "soil_ph",
                "soil_nutrients",
                "land_size_acres",
                "water_availability",
            ],
        },
        "weather": {
            "available": bool(weather_data),
            "provider": "open-meteo" if weather_data else None,
            "forecast_days": len((weather_data or {}).get("forecast") or []),
        },
        "crop_health": {
            "available": True,
            "method": "heuristic-screening",
            "alert_count": len(crop_health.get("alerts") or []),
        },
    }

    unified_index = {
        "source_count": len(data_sources),
        "available_count": sum(1 for source in data_sources.values() if source.get("available")),
        "completeness_ratio": round(
            sum(1 for source in data_sources.values() if source.get("available")) / max(len(data_sources), 1), 2
        ),
    }

    return {
        "timestamp": now.isoformat(),
        "season": season,
        "data_acquisition": {
            "sources": data_sources,
            "unified_index": unified_index,
        },
        "farm_profile": {
            "soil_type": farm_data.get("soilType"),
            "soil_ph": _safe_float(farm_data.get("soilPH"), 0),
            "soil_nutrients": farm_data.get("nutrients") or "Not specified",
            "land_size_acres": _safe_float(farm_data.get("landSize"), 0),
            "location": farm_data.get("location"),
            "water_availability": farm_data.get("waterAvailability"),
            "previous_crops": farm_data.get("previousCrops"),
            "issues": farm_data.get("issues"),
        },
        "location": location_data,
        "weather": weather_data,
        "crop_health": crop_health,
        "derived_metrics": {
            "forecast_rain_total_mm": round(total_rain, 1) if total_rain is not None else None,
            "forecast_avg_max_temp_c": round(avg_max_temp, 1) if avg_max_temp is not None else None,
            "decision_readiness_score": decision_score,
            "risk_level": _risk_level(decision_score),
        },
    }


def _build_market_prices_for_crops(crop_list):
    """Fetch market price info for all recommended crops."""
    market_prices = {}
    for crop in crop_list:
        live_price = scrape_market_prices(crop)

        if live_price:
            market_prices[crop] = {
                "crop_name": crop,
                "price_min": live_price.get("min"),
                "price_max": live_price.get("max"),
                "price_avg": live_price.get("avg"),
                "unit": live_price.get("unit", "kg"),
                "currency": live_price.get("currency", "INR"),
                "source": live_price.get("source", "market"),
                "updated_at": live_price.get("updated_at"),
            }

    return market_prices


def build_rule_based_recommendations(unified_context, ai_analysis):
    farm = unified_context.get("farm_profile", {})
    weather = unified_context.get("weather") or {}
    current_weather = weather.get("current") or {}
    crop_health = unified_context.get("crop_health") or {}

    soil = (farm.get("soil_type") or "").lower()
    water = (farm.get("water_availability") or "").lower()
    season = unified_context.get("season")

    crop_options = {
        "loamy": ["Tomato", "Chili", "Turmeric"],
        "clay": ["Rice", "Okra", "Spinach"],
        "sandy": ["Groundnut", "Millet", "Watermelon"],
        "silt": ["Wheat", "Mustard", "Coriander"],
        "peat": ["Ginger", "Carrot", "Cabbage"],
    }

    suggested_crops = crop_options.get(soil, ["Millet", "Pigeon Pea", "Spinach"])

    if water == "limited":
        suggested_crops = [crop for crop in suggested_crops if crop not in {"Rice", "Watermelon"}]
        if "Millet" not in suggested_crops:
            suggested_crops.insert(0, "Millet")

    pest_plan = [
        "Apply neem oil spray every 7 to 10 days during pest-prone weeks.",
        "Use yellow sticky traps around field boundaries to monitor insect load.",
        "Introduce marigold and basil as companion crops for natural repellent action.",
    ]

    if crop_health.get("risk_level") == "high":
        pest_plan.insert(0, "Prepare jeevamrut and spray as a foliar booster for stressed plants.")

    temp = current_weather.get("temperature_c")
    harvest_timing = "Track local mandi rates and harvest in early morning for better shelf life."
    if temp is not None and temp > 33:
        harvest_timing = "Harvest before 9 AM to reduce heat stress and preserve quality during transport."

    selling_timing = _estimate_market_window(suggested_crops[0] if suggested_crops else "", season)

    ai_priority_actions = ai_analysis.get("priority_actions") if isinstance(ai_analysis, dict) else None
    if not ai_priority_actions:
        ai_priority_actions = [
            "Strengthen soil with compost and mulch before next sowing window.",
            "Set up weekly pest scouting and log observations.",
            "Align irrigation with 5-day rain outlook to reduce water waste.",
        ]

    market_prices = _build_market_prices_for_crops(suggested_crops[:3])

    return {
        "crop_selection": suggested_crops[:3],
        "organic_pest_disease_plan": pest_plan,
        "harvest_timing": harvest_timing,
        "selling_timing": selling_timing,
        "priority_actions": ai_priority_actions,
        "market_prices": market_prices,
    }


def _build_local_analysis(unified_context):
    farm = unified_context.get("farm_profile", {})
    weather = unified_context.get("weather") or {}
    current = weather.get("current") or {}
    health = unified_context.get("crop_health") or {}
    metrics = unified_context.get("derived_metrics") or {}

    soil = (farm.get("soil_type") or "mixed").lower()
    water = (farm.get("water_availability") or "moderate").lower()
    location = farm.get("location") or "your region"

    patterns = [
        f"Seasonal pattern indicates {unified_context.get('season', 'current-season')} planning for {location}.",
        f"Soil profile ({soil}) combined with water availability ({water}) suggests targeted crop rotation.",
        f"Crop health score is {health.get('health_score', 0)}/100 with {health.get('risk_level', 'moderate')} field risk.",
    ]

    risks = []
    if (health.get("risk_level") or "").lower() in {"high", "moderate"}:
        risks.append("Crop stress indicators require stronger pest and nutrition monitoring.")
    if (metrics.get("forecast_rain_total_mm") or 0) > 70:
        risks.append("Heavy rainfall in short window may increase fungal pressure and nutrient leaching.")
    if (current.get("temperature_c") or 0) > 33:
        risks.append("High day temperatures can reduce fruit quality if harvesting is delayed.")
    if not risks:
        risks.append("No severe near-term risk detected, but continue weekly field scouting.")

    opportunities = [
        "Use organic mulching and composting to improve moisture retention and soil carbon.",
        "Align irrigation with 5-day forecast to reduce water waste.",
        "Batch harvesting and graded selling can improve market realization.",
    ]

    return {
        "patterns": patterns,
        "risks": risks,
        "opportunities": opportunities,
        "priority_actions": [
            "Apply compost + mulch before next sowing cycle.",
            "Perform pest scouting twice weekly and update a field log.",
            "Use forecast-based irrigation scheduling.",
        ],
        "explainability": "Insights are derived from farm profile, weather forecast, and crop-health heuristics.",
    }


def _normalize_ai_analysis(ai_analysis, fallback):
    if not isinstance(ai_analysis, dict):
        return fallback

    def _list_or(default_key):
        value = ai_analysis.get(default_key)
        if isinstance(value, list) and value:
            return [str(item) for item in value if str(item).strip()]
        return fallback[default_key]

    explainability = ai_analysis.get("explainability")
    if not isinstance(explainability, str) or not explainability.strip():
        explainability = fallback["explainability"]

    return {
        "patterns": _list_or("patterns"),
        "risks": _list_or("risks"),
        "opportunities": _list_or("opportunities"),
        "priority_actions": _list_or("priority_actions"),
        "explainability": explainability,
    }


def _get_ai_analysis(unified_context):
    if genai is None:
        return None

    api_key = os.getenv("VITE_GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None

    prompt = (
        "You are an organic farming analytics expert. Analyze the provided unified farm context and respond ONLY "
        "as a valid JSON object with these keys: patterns (array of 3), risks (array of 3), opportunities "
        "(array of 3), priority_actions (array of 3), explainability (string). Keep each item practical and concise."
        f"\n\nUnified context JSON:\n{json.dumps(unified_context, ensure_ascii=True)}"
    )

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        raw = (response.text or "").replace("```json", "").replace("```", "").strip()
        return json.loads(raw)
    except Exception:
        return None


def get_farm_intelligence(farm_data):
    unified_context = build_unified_farm_context(farm_data or {})

    local_analysis = _build_local_analysis(unified_context)
    ai_analysis = _get_ai_analysis(unified_context)
    intelligence = _normalize_ai_analysis(ai_analysis, local_analysis)

    recommendations = build_rule_based_recommendations(unified_context, intelligence)

    recommendation_cards = [
        "Crop selection: " + ", ".join(recommendations.get("crop_selection") or []),
        "Organic pest and disease strategy: "
        + " ".join(recommendations.get("organic_pest_disease_plan") or []),
        "Harvest timing: " + recommendations.get("harvest_timing", ""),
        "Selling window: " + recommendations.get("selling_timing", ""),
    ]

    structured_recommendations = {
        "crop_selection": recommendations.get("crop_selection") or [],
        "organic_pest_disease_plan": recommendations.get("organic_pest_disease_plan") or [],
        "harvest_timing": recommendations.get("harvest_timing", ""),
        "selling_timing": recommendations.get("selling_timing", ""),
        "priority_actions": recommendations.get("priority_actions") or intelligence.get("priority_actions", []),
        "market_prices": recommendations.get("market_prices", {}),
    }

    decision_support = {
        "priority_actions": recommendations.get("priority_actions") or intelligence.get("priority_actions", []),
        "risk_level": unified_context.get("derived_metrics", {}).get("risk_level", "moderate"),
        "sustainability_score": unified_context.get("derived_metrics", {}).get("decision_readiness_score", 60),
        "resource_efficiency_hint": "Prioritize composting, moisture conservation, and low-input biological controls.",
        "explainability": intelligence.get("explainability"),
    }

    return unified_context, intelligence, recommendation_cards, decision_support, structured_recommendations
