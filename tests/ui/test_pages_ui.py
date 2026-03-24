from bs4 import BeautifulSoup
import app as app_module


def test_index_page_contains_state_and_district_selects(client):
    response = client.get("/")

    assert response.status_code == 200
    soup = BeautifulSoup(response.data, "html.parser")
    assert soup.select_one("#stateSelect") is not None
    assert soup.select_one("#districtSelect") is not None


def test_suggestions_page_shows_cards_with_live_data(farm_session, monkeypatch):
    monkeypatch.setattr(
        app_module,
        "get_crop_suggestions",
        lambda _farm_data: [
            {
                "name": "Groundnut",
                "confidence": 95,
                "waterNeeds": "Low",
                "sunlight": "Full Sun",
                "temperature": "22-34",
                "description": "Suitable for sandy soils.",
                "organicGuide": {
                    "preparation": ["Step 1"],
                    "planting": ["Step 1"],
                    "maintenance": ["Step 1"],
                    "harvesting": ["Step 1"],
                },
                "marketPrice": {
                    "min": 1400,
                    "max": 2200,
                    "avg": 1800,
                    "unit": "kg",
                    "currency": "INR",
                    "source": "agmarknet",
                    "updated_at": "2026-03-24T10:00:00",
                },
            }
        ],
    )

    response = farm_session.get("/suggestions")

    assert response.status_code == 200
    html = response.data.decode("utf-8")
    assert "Groundnut" in html
    assert "Market Price" in html
    assert "agmarknet" in html


def test_suggestions_page_shows_error_when_live_data_unavailable(farm_session, monkeypatch):
    monkeypatch.setattr(app_module, "get_crop_suggestions", lambda _farm_data: [])

    response = farm_session.get("/suggestions")

    assert response.status_code == 200
    html = response.data.decode("utf-8")
    assert "No real-time suggestion data available right now" in html
