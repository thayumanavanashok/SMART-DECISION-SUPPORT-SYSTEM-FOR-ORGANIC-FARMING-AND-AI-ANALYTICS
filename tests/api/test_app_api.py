import app as app_module


def test_weather_api_returns_data_when_session_present(farm_session, monkeypatch):
    monkeypatch.setattr(
        app_module,
        "get_weather_for_farm",
        lambda _farm_data: {"current": {"temperature": 30, "description": "Clouds"}},
    )

    response = farm_session.get("/api/weather")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["current"]["temperature"] == 30


def test_weather_api_requires_session(client):
    response = client.get("/api/weather")

    assert response.status_code == 400
    assert "error" in response.get_json()


def test_india_states_districts_api_returns_list(client, monkeypatch):
    monkeypatch.setattr(
        app_module,
        "get_india_states_and_districts",
        lambda force_refresh=False: [
            {
                "state_id": 1,
                "name": "Tamil Nadu",
                "region_type": "state",
                "districts": [{"district_id": 1, "name": "Erode"}],
            }
        ],
    )

    response = client.get("/api/india/states-districts")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["count"] == 1
    assert payload["states"][0]["name"] == "Tamil Nadu"


def test_weather_locations_api_validates_query(client):
    response = client.get("/api/weather/locations/india")

    assert response.status_code == 400
    assert response.get_json()["error"] == "Query parameter q is required"
