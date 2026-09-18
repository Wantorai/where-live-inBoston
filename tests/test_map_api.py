"""Verify prepared files are served without depending on Census or local secrets."""

import json

from fastapi.testclient import TestClient

from boston_map.api import main


def test_tract_snapshot_is_served(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "DATA_DIR", tmp_path)
    data = {"type": "FeatureCollection", "features": []}
    (tmp_path / "suffolk_density_2024.geojson").write_text(json.dumps(data))
    with TestClient(main.app) as client:
        response = client.get("/api/tracts")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/geo+json"
    assert response.json() == data


def test_missing_data_returns_service_unavailable(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "DATA_DIR", tmp_path)
    with TestClient(main.app) as client:
        for path in ("/api/tracts", "/api/metadata"):
            assert client.get(path).status_code == 503
