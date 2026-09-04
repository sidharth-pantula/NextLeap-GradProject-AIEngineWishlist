"""Unit tests for Phase 8: FastAPI Stitch Dashboard & Backend Endpoints."""
import pytest
from fastapi.testclient import TestClient
from dashboard.api import app


@pytest.fixture(scope="module")
def client():
    """Create test client for Dashboard FastAPI app."""
    return TestClient(app)


def test_serve_dashboard_html(client):
    res = client.get("/")
    assert res.status_code == 200
    assert "wishlist purchase discovery" in res.text.lower()
    assert "<html" in res.text


def test_get_kpis_api(client):
    res = client.get("/api/kpis")
    assert res.status_code == 200
    data = res.json()
    assert "total_analyzed" in data
    assert "relevant_analyzed" in data
    assert "non_conversion_rate_pct" in data
    assert "high_intent_pct" in data
    assert "problem_clusters_count" in data


def test_get_coverage_api(client):
    res = client.get("/api/coverage")
    assert res.status_code == 200
    data = res.json()
    assert "total_items" in data
    assert "sources" in data
    assert len(data["sources"]) > 0


def test_get_behaviours_api(client):
    res = client.get("/api/behaviours")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "percentage" in data[0]


def test_get_barriers_api(client):
    res = client.get("/api/barriers")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "prevalence_pct" in data[0]
    assert "confidence_pct" in data[0]


def test_get_opportunities_api(client):
    res = client.get("/api/opportunities")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "opportunity_score" in data[0]
    assert "rank" in data[0]


def test_get_triggers_api(client):
    res = client.get("/api/triggers")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) > 0


def test_get_evidence_api(client):
    res = client.get("/api/evidence")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "quote" in data[0]


def test_ask_ai_chat_api(client):
    res = client.post("/api/chat", json={"query": "Why do users hesitate to buy?"})
    assert res.status_code == 200
    data = res.json()
    assert "query" in data
    assert "answer" in data
    assert len(data["answer"]) > 0
