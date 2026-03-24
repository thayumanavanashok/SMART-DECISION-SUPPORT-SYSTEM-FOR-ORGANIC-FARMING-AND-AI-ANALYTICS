import farm_intelligence as fi


def test_get_farm_intelligence_integration_with_mocked_live_dependencies(monkeypatch):
    farm_data = {
        "soilType": "loamy",
        "landSize": "3",
        "location": "Erode, Tamil Nadu",
        "waterAvailability": "moderate",
        "previousCrops": "Turmeric",
        "issues": "pest observed",
    }

    monkeypatch.setattr(
        fi,
        "geocode_location",
        lambda _location: {
            "name": "Erode",
            "country": "India",
            "latitude": 11.34,
            "longitude": 77.71,
        },
    )
    monkeypatch.setattr(
        fi,
        "fetch_weather_snapshot",
        lambda _lat, _lon: {
            "current": {
                "temperature_c": 31,
                "humidity_pct": 72,
                "precipitation_mm": 1.2,
                "wind_kmph": 11,
            },
            "forecast": [
                {"date": "2026-03-25", "temp_max": 32, "temp_min": 23, "rain_mm": 2},
                {"date": "2026-03-26", "temp_max": 33, "temp_min": 24, "rain_mm": 0},
            ],
        },
    )
    monkeypatch.setattr(
        fi,
        "_get_ai_analysis",
        lambda _ctx: {
            "patterns": ["Pattern A", "Pattern B", "Pattern C"],
            "risks": ["Risk A", "Risk B", "Risk C"],
            "opportunities": ["Opp A", "Opp B", "Opp C"],
            "priority_actions": ["Act 1", "Act 2", "Act 3"],
            "explainability": "Test explainability",
        },
    )

    def fake_scrape(crop):
        return {
            "crop": crop,
            "min": 1500,
            "max": 2200,
            "avg": 1850,
            "currency": "INR",
            "unit": "kg",
            "source": "agmarknet",
            "updated_at": "2026-03-24T10:00:00",
        }

    monkeypatch.setattr(fi, "scrape_market_prices", fake_scrape)

    unified_context, intelligence, recommendations, decision_support, structured = fi.get_farm_intelligence(farm_data)

    assert unified_context["location"]["name"] == "Erode"
    assert intelligence["patterns"][0] == "Pattern A"
    assert len(recommendations) >= 3
    assert structured["market_prices"]
    for _crop, price in structured["market_prices"].items():
        assert price["source"] == "agmarknet"
        assert price["price_min"] == 1500
        assert price["price_max"] == 2200
    assert decision_support["risk_level"] in {"low", "moderate", "high"}
