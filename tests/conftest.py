import pytest

from app import app as flask_app


@pytest.fixture
def app():
    flask_app.config.update(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret-key",
        }
    )
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def farm_session(client):
    with client.session_transaction() as sess:
        sess["farm_data"] = {
            "soilType": "loamy",
            "landSize": "2",
            "location": "Erode, Tamil Nadu",
            "waterAvailability": "moderate",
            "previousCrops": "Turmeric",
            "issues": "",
            "latitude": "11.3410",
            "longitude": "77.7172",
        }
    return client
