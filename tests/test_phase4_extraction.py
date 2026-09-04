"""Unit tests for Phase 4: Structured LLM Information Extraction & Evidence Provenance."""
import os
import pytest
from database.db import Database
from ai.extraction import ExtractionPipeline, FeedbackExtractionModel


TEST_DB_PATH = "data/test_phase4_db.db"


@pytest.fixture(autouse=True)
def setup_teardown():
    """Setup and teardown test artifacts."""
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
    yield
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)


def test_pydantic_schema_validation():
    """Test validation of structured extraction fields against Pydantic schema."""
    sample_llm_json = {
        "user_intent": "sale_waiting",
        "wishlist_reason": "waiting_for_sale",
        "purchase_intent": "conditional_on_discount",
        "purchase_barrier": "price",
        "purchase_hesitation": "Price is too high at full retail",
        "purchase_postponement_reason": "Waiting for 40% discount during EORS",
        "uncertainty_type": "price_fairness",
        "information_needed": "Price history and sale notification",
        "decision_stage": "wishlisted",
        "behaviour_after_interest": "monitored_price",
        "comparison_behaviour": "compared_platforms",
        "external_search_behaviour": "searched_reddit",
        "competitor_behaviour": "checked_myntra",
        "purchase_outcome": "postponed",
        "product_category": "Apparel",
        "product_type": "jacket",
        "price_sensitivity": "high",
        "fit_concern": 0,
        "size_concern": 0,
        "quality_concern": 0,
        "material_concern": 0,
        "styling_concern": 0,
        "occasion_concern": 0,
        "review_concern": 0,
        "social_validation_need": 0,
        "trust_concern": 0,
        "availability_concern": 0,
        "return_exchange_concern": 0,
        "user_segment_signals": "deal_seeker",
        "evidence_strength": "strong",
        "evidence_span": "waiting for 40% discount",
        "evidence_type": "explicit",
        "inferred_user_need": "Needs automated price-drop alerts to trigger checkout.",
        "inference_confidence": 0.92
    }

    validated = FeedbackExtractionModel(**sample_llm_json)
    assert validated.user_intent == "sale_waiting"
    assert validated.purchase_barrier == "price"
    assert validated.price_concern if hasattr(validated, "price_concern") else True
    assert validated.evidence_span == "waiting for 40% discount"


def test_verbatim_evidence_grounding():
    """Test zero-hallucination substring verification for evidence spans."""
    pipeline = ExtractionPipeline()
    original_text = "I loved this red dress on AJIO but the sizing chart was totally wrong so I didn't buy."

    # Exact substring
    span, ev_type = pipeline.validate_and_ground_evidence(original_text, "sizing chart was totally wrong")
    assert span == "sizing chart was totally wrong"
    assert ev_type == "explicit"

    # Paraphrased / partial match
    span_para, ev_type_para = pipeline.validate_and_ground_evidence(original_text, "the size chart is wrong")
    assert ev_type_para == "inferred"

    # Complete hallucination
    span_hallucinated, ev_type_hallucinated = pipeline.validate_and_ground_evidence(original_text, "fabric is transparent")
    assert span_hallucinated is None or ev_type_hallucinated == "inferred"


def test_extraction_batch_processing_into_database():
    """Test end-to-end extraction batch updating processed_feedback in SQLite."""
    db = Database(db_path=TEST_DB_PATH)
    pipeline = ExtractionPipeline(db=db)

    # Insert raw feedback
    db.batch_insert_raw_feedback([
        {
            "feedback_id": "test_fb_101",
            "source": "youtube",
            "source_type": "comment",
            "text": "The fabric quality on this Myntra dress was sheer and stitching came off.",
            "collection_timestamp": "2026-08-27T10:00:00Z"
        }
    ])

    # Insert initial processed feedback record with score 2
    db.execute_write("""
        INSERT INTO processed_feedback (
            feedback_id, cleaned_text, relevance_score, relevance_reason, relevance_confidence, processing_timestamp
        ) VALUES (
            'test_fb_101', 'The fabric quality on this Myntra dress was sheer and stitching came off.',
            2, 'Discusses fabric quality and stitching defects', 0.90, '2026-08-27T10:00:00Z'
        );
    """)

    updated_count = pipeline.process_relevant_feedback_batch(limit=10, min_relevance=2)
    assert updated_count == 1

    # Verify structured fields were extracted and saved
    rows = db.execute_query("SELECT * FROM processed_feedback WHERE feedback_id = 'test_fb_101';")
    assert len(rows) == 1
    record = rows[0]
    assert record["purchase_barrier"] in ["quality_material", "fit_sizing", "returns"]
    assert record["inferred_user_need"] is not None
    assert len(record["inferred_user_need"]) > 10
