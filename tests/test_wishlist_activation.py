"""Unit and Integration Tests for the Wishlist Activation Engine & API Endpoints."""
import pytest
from database.db import get_db
from analysis.wishlist_activation import WishlistActivationEngine
from fastapi.testclient import TestClient
from dashboard.api import app


@pytest.fixture(scope="module")
def activation_engine():
    db = get_db()
    return WishlistActivationEngine(db=db)


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_wishlist_behavioral_metrics(activation_engine):
    """Test quantitative metrics from synthetic wishlist dataset."""
    metrics = activation_engine.get_wishlist_behavioral_metrics()
    
    assert metrics["total_records"] >= 5000
    assert 5.0 <= metrics["overall_30d_conversion_pct"] <= 35.0
    assert metrics["price_drop_conversion_pct"] > metrics["no_price_drop_conversion_pct"]
    assert metrics["price_drop_conversion_lift"] > 0
    assert metrics["price_alert_conversion_pct"] > 0
    assert metrics["avg_days_to_purchase"] > 0
    assert "BEHAVIOURAL" in metrics["epistemic_label"]
    assert "electricsheepafrica" in metrics["data_source"]


def test_ecommerce_funnel_benchmark(activation_engine):
    """Test clickstream progression benchmark with wishlist and cart transitions."""
    bench = activation_engine.get_ecommerce_funnel_benchmark()
    
    assert bench["total_events"] > 0
    assert bench["views"] > 0
    assert bench["carts"] > 0
    assert bench["purchases"] > 0
    assert 5.0 <= bench["view_to_cart_pct"] <= 30.0
    assert 10.0 <= bench["cart_to_purchase_pct"] <= 60.0
    assert bench["view_to_wishlist_pct"] > 0
    assert bench["wishlist_to_cart_pct"] > 0
    assert bench["wishlist_cart_to_purchase_pct"] > 0
    assert "REES46" in bench["data_source"]


def test_exploration_vs_intent_breakdown(activation_engine):
    """Test exploration vs commercial intent model."""
    exp = activation_engine.get_exploration_vs_intent_breakdown()
    
    assert exp["total_voc_analyzed"] > 0
    assert exp["strict_purchase_intent_pct"] >= 0.0
    assert exp["broader_commercial_consideration_pct"] >= exp["strict_purchase_intent_pct"]
    assert exp["exploration_bookmarking_pct"] >= 0.0
    assert "pm_insight" in exp
    assert "why_users_explore" in exp["pm_insight"]


def test_three_core_activation_questions(activation_engine):
    """Test the 3 Core PM Activation Questions."""
    three_q = activation_engine.get_three_core_activation_questions()
    
    assert "why_are_users_saving" in three_q
    assert "what_stops_them" in three_q
    assert "how_users_build_confidence" in three_q
    assert "what_could_reactivate_them" in three_q
    
    assert len(three_q["why_are_users_saving"]) >= 5
    assert len(three_q["what_stops_them"]) >= 3
    assert len(three_q["how_users_build_confidence"]) >= 3
    assert len(three_q["what_could_reactivate_them"]) >= 3


def test_purchase_trigger_matrix(activation_engine):
    """Test candidate trigger comparison matrix."""
    matrix = activation_engine.get_purchase_trigger_matrix()
    assert isinstance(matrix, list)
    assert len(matrix) >= 5
    
    for item in matrix:
        assert "trigger_name" in item
        assert "problem_addressed" in item
        assert "epistemic_classification" in item
        assert item["opportunity_score"] > 0


def test_special_activation_topics(activation_engine):
    """Test deep dives for Price/Sale, Festival, FOMO, and Confidence Building."""
    topics = activation_engine.get_special_activation_topics()
    
    assert "price_sale_analysis" in topics
    assert "festival_reactivation" in topics
    assert "availability_timing_dynamics" in topics
    assert "confidence_building_analysis" in topics
    assert "QUALITATIVE EVIDENCE" in topics["confidence_building_analysis"]["epistemic_label"]


def test_activation_api_endpoints(client):
    """Verify all FastAPI REST endpoints for the Wishlist Activation layer."""
    # 1. Summary
    res = client.get("/api/activation/summary")
    assert res.status_code == 200
    assert "overall_30d_conversion_pct" in res.json()
    assert "price_drop_conversion_lift" in res.json()

    # 2. Wishlist behaviour
    res = client.get("/api/activation/wishlist-behaviour")
    assert res.status_code == 200
    assert "total_records" in res.json()

    # 3. Funnel benchmark
    res = client.get("/api/activation/funnel-benchmark")
    assert res.status_code == 200
    assert "view_to_cart_pct" in res.json()

    # 4. Exploration vs Intent
    res = client.get("/api/activation/exploration-intent")
    assert res.status_code == 200
    assert "broader_commercial_consideration_pct" in res.json()

    # 5. Three questions
    res = client.get("/api/activation/three-questions")
    assert res.status_code == 200
    assert "why_are_users_saving" in res.json()

    # 6. Trigger matrix
    res = client.get("/api/activation/trigger-matrix")
    assert res.status_code == 200
    assert isinstance(res.json(), list)

    # 7. Special topics
    res = client.get("/api/activation/special-topics")
    assert res.status_code == 200
    assert "festival_reactivation" in res.json()

    # 8. Opportunities
    res = client.get("/api/activation/opportunities")
    assert res.status_code == 200
    assert len(res.json()) > 0
