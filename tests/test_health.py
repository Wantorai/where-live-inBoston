"""Check the health endpoint through the HTTP application interface."""

from fastapi.testclient import TestClient

from boston_map.api.main import app


def test_health_returns_successful_json_response():
    with TestClient(app) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    assert response.json() == {"status": "ok"}
