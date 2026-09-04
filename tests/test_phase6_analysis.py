"""Tests for Phase 6: Deterministic Metrics, Segmentation & Opportunity Engine."""
import pytest
from database.db import get_db
from analysis.metrics import MetricsEngine
from analysis.segmentation import SegmentationEngine
from analysis.opportunity import OpportunityEngine


@pytest.fixture(scope="module")
def setup_phase6_data():
    """Setup test data in SQLite for Phase 6 verification."""
    db = get_db()

    # Ensure a test problem cluster exists
    db.execute_write("""
        INSERT OR IGNORE INTO problem_clusters (cluster_id, level_1_category, level_2_category, cluster_label, cluster_description, created_at)
        VALUES (999, 'Sizing & Fit', 'Size Guide Ambiguity', 'Size Conversion Uncertainty', 'Users unsure of sizes across brands', CURRENT_TIMESTAMP)
    """)

    # Insert mock raw feedback
    db.execute_write("""
        INSERT OR IGNORE INTO raw_feedback (feedback_id, source, source_type, text, collection_timestamp)
        VALUES 
        ('test_p6_1', 'youtube', 'comment', 'Sizing is confusing on Myntra', CURRENT_TIMESTAMP),
        ('test_p6_2', 'reddit', 'post', 'Size chart did not match actual dress', CURRENT_TIMESTAMP),
        ('test_p6_3', 'web', 'review', 'Fit was too loose so I postponed buying', CURRENT_TIMESTAMP)
    """)

    # Insert mock processed feedback linked to cluster 999
    db.execute_write("""
        INSERT OR IGNORE INTO processed_feedback (
            feedback_id, relevance_score, purchase_barrier, uncertainty_type, decision_stage, 
            purchase_outcome, evidence_type, product_category, price_sensitivity, fit_concern, 
            cluster_id, processing_timestamp
        ) VALUES 
        ('test_p6_1', 3, 'Size chart mismatch', 'fit_uncertainty', 'Consideration', 'hesitated', 'explicit', 'Apparel', 'Budget', 1, 999, CURRENT_TIMESTAMP),
        ('test_p6_2', 3, 'Inaccurate sizing', 'fit_uncertainty', 'Comparison', 'postponed', 'inferred', 'Apparel', 'Mid', 1, 999, CURRENT_TIMESTAMP),
        ('test_p6_3', 3, 'Loose fit fear', 'fit_uncertainty', 'Research', 'abandoned', 'explicit', 'Footwear', 'Budget', 1, 999, CURRENT_TIMESTAMP)
    """)

    yield db

    # Teardown
    db.execute_write("DELETE FROM processed_feedback WHERE feedback_id LIKE 'test_p6_%'")
    db.execute_write("DELETE FROM raw_feedback WHERE feedback_id LIKE 'test_p6_%'")
    db.execute_write("DELETE FROM cluster_metrics WHERE cluster_id = 999")
    db.execute_write("DELETE FROM opportunity_scores WHERE cluster_id = 999")
    db.execute_write("DELETE FROM problem_clusters WHERE cluster_id = 999")


def test_metrics_engine(setup_phase6_data):
    db = setup_phase6_data
    engine = MetricsEngine(db=db)

    metrics = engine.compute_cluster_metrics(999)
    assert metrics["cluster_id"] == 999
    assert metrics["frequency"] == 3
    assert metrics["prevalence_pct"] > 0.0
    assert metrics["source_breadth"] == 3 # youtube, reddit, web
    assert metrics["explicit_evidence_rate"] == round((2 / 3 * 100.0), 2)
    assert metrics["purchase_linkage_score"] == 100.0 # all 3 had purchase barriers/hesitation


def test_segmentation_engine(setup_phase6_data):
    db = setup_phase6_data
    seg_engine = SegmentationEngine(db=db)

    cats = seg_engine.get_category_breakdown()
    assert isinstance(cats, list)
    assert len(cats) > 0

    prices = seg_engine.get_price_tier_breakdown()
    assert isinstance(prices, list)

    funnel = seg_engine.get_decision_stage_funnel()
    assert isinstance(funnel, list)


def test_opportunity_engine(setup_phase6_data):
    db = setup_phase6_data
    opp_engine = OpportunityEngine(db=db)

    opportunities = opp_engine.prioritize_and_store_opportunities()
    assert isinstance(opportunities, list)
    assert len(opportunities) > 0

    top_opp = opportunities[0]
    assert "opportunity_score" in top_opp
    assert "priority_rank" in top_opp
    assert 0 <= top_opp["opportunity_score"] <= 100
    assert "rationale" in top_opp
    assert top_opp["priority_rank"] == 1
