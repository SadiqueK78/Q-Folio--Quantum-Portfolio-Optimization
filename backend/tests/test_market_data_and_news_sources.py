"""Tests for per-asset/all-asset price series endpoints and RSS source labeling."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from fastapi.testclient import TestClient

from app.api.main import app
from app.agents.news_agents import friendly_source_name

client = TestClient(app)


def test_price_series_known_symbol_returns_data():
    r = client.get("/api/prices/TCS.NS?range=1y")
    assert r.status_code == 200
    body = r.json()
    assert body["symbol"] == "TCS.NS"
    assert len(body["series"]) > 0


def test_price_series_unknown_symbol_returns_404():
    r = client.get("/api/prices/NOPE.NS")
    assert r.status_code == 404


def test_price_series_invalid_range_returns_400():
    r = client.get("/api/prices/TCS.NS?range=nonsense")
    assert r.status_code == 400


def test_all_prices_normalized_to_100_at_start():
    r = client.get("/api/prices?range=6m")
    assert r.status_code == 200
    body = r.json()
    first_date = min(body["series"].keys())
    first_row = body["series"][first_date]
    for value in first_row.values():
        if value is not None:
            assert value == pytest.approx(100.0, abs=0.01)


def test_friendly_source_name_maps_known_domains():
    assert friendly_source_name("https://www.cnbc.com/id/12345/rss.html") == "CNBC"
    assert friendly_source_name("https://feeds.reuters.com/reuters/businessNews") == "Reuters"


def test_friendly_source_name_unknown_passthrough():
    assert friendly_source_name("https://unknown-source.example.com/rss") == "https://unknown-source.example.com/rss"
