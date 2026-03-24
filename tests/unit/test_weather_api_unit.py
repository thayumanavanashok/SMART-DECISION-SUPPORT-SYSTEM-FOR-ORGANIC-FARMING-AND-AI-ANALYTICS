from weather_api import _parse_weather_response, _parse_forecast_response, get_agricultural_weather_advisory


def test_parse_weather_response_extracts_expected_fields():
    payload = {
        "name": "Erode",
        "sys": {"country": "IN", "sunrise": 1711260000, "sunset": 1711303600},
        "coord": {"lat": 11.34, "lon": 77.71},
        "main": {
            "temp": 31.2,
            "feels_like": 35.0,
            "temp_min": 28.0,
            "temp_max": 33.4,
            "humidity": 79,
            "pressure": 1008,
        },
        "weather": [{"main": "Clouds", "description": "broken clouds"}],
        "wind": {"speed": 4.5, "deg": 250},
        "clouds": {"all": 65},
        "visibility": 7000,
        "dt": 1711270000,
        "timezone": 19800,
    }

    result = _parse_weather_response(payload)

    assert result["location"]["city"] == "Erode"
    assert result["current"]["temperature"] == 31.2
    assert result["current"]["description"] == "Clouds"
    assert result["wind"]["speed"] == 4.5


def test_parse_forecast_response_maps_entries():
    payload = {
        "city": {"name": "Erode", "country": "IN", "coord": {"lat": 11.34, "lon": 77.71}},
        "list": [
            {
                "dt": 1711270000,
                "main": {"temp": 30, "feels_like": 33, "humidity": 70, "pressure": 1009},
                "weather": [{"main": "Rain", "description": "light rain"}],
                "wind": {"speed": 3.2, "deg": 260},
                "clouds": {"all": 80},
                "rain": {"3h": 2.5},
                "visibility": 6000,
                "pop": 0.52,
            }
        ],
    }

    result = _parse_forecast_response(payload)

    assert result["location"]["city"] == "Erode"
    assert result["count"] == 1
    assert result["forecasts"][0]["rain_probability"] == 52.0


def test_weather_advisory_generates_alerts():
    weather_data = {
        "location": {"city": "Erode", "country": "IN"},
        "current": {
            "temperature": 38,
            "humidity": 86,
            "rainfall": 12,
            "description": "Thunderstorm",
            "details": "thunderstorm with heavy rain",
            "timestamp": "2026-03-24T08:00:00",
        },
    }

    advisory = get_agricultural_weather_advisory(weather_data)

    assert advisory["total_alerts"] >= 3
    categories = {item["category"] for item in advisory["advisories"]}
    assert "Temperature" in categories
    assert "Humidity" in categories
