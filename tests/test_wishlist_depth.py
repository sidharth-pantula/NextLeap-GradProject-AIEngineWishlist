"""Unit tests for Wishlist Depth and Dormancy Analytics."""
import pytest
from database.db import get_db
from analysis.wishlist_depth import WishlistDepthEngine
from fastapi.testclient import TestClient
from dashboard.api import app


@pytest.fixture
def depth_engine():
    db = get_db()
    return WishlistDepthEngine(db=db)


@pytest.fixture
def client():
    return TestClient(app)


def test_depth_engine_kpis(depth_engine):
    data = depth_engine.get_depth_and_dormancy_analysis()
    assert "summary_kpis" in data
    kpis = data["summary_kpis"]
    
    assert kpis["total_wishlist_users"] == 1200
    assert kpis["total_saved_items"] == 5000
    assert kpis["avg_items_per_user"] > 0
    assert kpis["users_with_5_plus_items_pct"] == 58.4
    assert kpis["users_with_5_to_50_plus_items_pct"] == 58.4
    assert kpis["dormant_items_30d_pct"] == 70.7
    assert kpis["avg_days_unpurchased"] > kpis["avg_days_to_purchase"]


def test_size_distribution_tiers(depth_engine):
    data = depth_engine.get_depth_and_dormancy_analysis()
    assert "size_distribution" in data
    dist = data["size_distribution"]
    assert len(dist) == 3
    assert "10+" in dist[0]["tier"]
    assert dist[0]["user_pct"] == 64.2
    assert "25+" in dist[1]["tier"]
    assert dist[1]["user_pct"] == 41.5
    assert "50+" in dist[2]["tier"]
    assert dist[2]["user_pct"] == 23.8


def test_dormancy_decay_dynamics(depth_engine):
    data = depth_engine.get_depth_and_dormancy_analysis()
    assert "dormancy_analysis" in data
    dormancy = data["dormancy_analysis"]
    assert dormancy["dormant_30d_count"] == 3534
    assert dormancy["dormant_60d_count"] == 2419
    assert dormancy["timeline_comparison"]["avg_days_unpurchased"] == 67.8
    assert dormancy["timeline_comparison"]["avg_days_to_purchase"] == 23.7


def test_comparison_behaviour_metrics(depth_engine):
    data = depth_engine.get_depth_and_dormancy_analysis()
    assert "comparison_behaviour" in data
    comp = data["comparison_behaviour"]
    assert comp["purchasing_session_pages"] == 32.8
    assert comp["non_purchasing_session_pages"] == 22.0
    assert comp["comparison_lift_pct"] == 49.1


def test_api_depth_dormancy_endpoint(client):
    res = client.get("/api/wishlist/depth-dormancy")
    assert res.status_code == 200
    data = res.json()
    assert "summary_kpis" in data
    assert data["summary_kpis"]["total_wishlist_users"] == 1200
