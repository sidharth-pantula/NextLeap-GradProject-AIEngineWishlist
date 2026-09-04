"""Unit tests for Phase 1: Database and Vector Storage Foundations."""
import os
import shutil
import pytest
from database.db import Database
from database.schema import init_db
from vector.chroma_store import ChromaStore


TEST_DB_PATH = "data/test_discovery_engine.db"
TEST_CHROMA_DIR = "chroma_db_test"


@pytest.fixture(autouse=True)
def cleanup():
    """Setup and teardown test artifacts."""
    for path in [TEST_DB_PATH, TEST_CHROMA_DIR]:
        if os.path.isfile(path):
            os.remove(path)
        elif os.path.isdir(path):
            shutil.rmtree(path, ignore_errors=True)
    yield
    for path in [TEST_DB_PATH, TEST_CHROMA_DIR]:
        if os.path.isfile(path):
            os.remove(path)
        elif os.path.isdir(path):
            shutil.rmtree(path, ignore_errors=True)


def test_database_init_and_tables():
    """Test schema initialization and table creation."""
    db = Database(db_path=TEST_DB_PATH)
    counts = db.get_summary_counts()
    assert counts["raw_feedback"] == 0
    assert counts["processed_feedback"] == 0
    assert counts["shopper_sessions"] == 0


def test_raw_feedback_insert():
    """Test batch inserting normalized raw feedback records."""
    db = Database(db_path=TEST_DB_PATH)
    sample_records = [
        {
            "feedback_id": "yt_12345",
            "source": "youtube",
            "source_type": "comment",
            "source_id": "comment_1",
            "date": "2026-08-25T10:00:00Z",
            "text": "I added the jacket to my wishlist but the sizing chart looks completely off.",
            "title": "Myntra Winter Haul",
            "url": "https://youtube.com/watch?v=12345",
            "product": "Denim Jacket",
            "category": "Apparel",
            "rating": None,
            "engagement": 12,
            "metadata_json": {"author": "shopper_1"},
            "collection_timestamp": "2026-08-26T12:00:00Z"
        },
        {
            "feedback_id": "web_67890",
            "source": "web",
            "source_type": "search_snippet",
            "source_id": "snippet_2",
            "date": "2026-08-24T15:30:00Z",
            "text": "Why do people leave items in wishlist? Mostly waiting for a 50% sale.",
            "title": "Fashion Shopping Forum",
            "url": "https://reddit.com/r/IndianFashionAddicts/123",
            "product": None,
            "category": "Apparel",
            "rating": None,
            "engagement": 5,
            "metadata_json": None,
            "collection_timestamp": "2026-08-26T12:00:00Z"
        }
    ]

    inserted = db.batch_insert_raw_feedback(sample_records)
    assert inserted == 2

    # Check duplicate insertion is ignored safely
    duplicate_inserted = db.batch_insert_raw_feedback(sample_records)
    assert duplicate_inserted == 0

    rows = db.execute_query("SELECT feedback_id, source, text FROM raw_feedback;")
    assert len(rows) == 2
    assert rows[0]["feedback_id"] == "yt_12345"
    assert rows[1]["source"] == "web"


def test_shopper_sessions_insert():
    """Test batch inserting UCI shopper session data."""
    db = Database(db_path=TEST_DB_PATH)
    sample_sessions = [
        {
            "administrative_pages": 2,
            "administrative_duration": 45.0,
            "informational_pages": 4,
            "informational_duration": 180.5,
            "product_related_pages": 15,
            "product_related_duration": 650.0,
            "bounce_rate": 0.02,
            "exit_rate": 0.05,
            "page_value": 12.5,
            "special_day": 0.0,
            "month": "Nov",
            "operating_systems": 2,
            "browser": 2,
            "region": 1,
            "traffic_type": 2,
            "visitor_type": "Returning_Visitor",
            "weekend": 1,
            "revenue_converted": 0
        }
    ]

    inserted = db.batch_insert_shopper_sessions(sample_sessions)
    assert inserted == 1

    counts = db.get_summary_counts()
    assert counts["shopper_sessions"] == 1


def test_chroma_store_operations():
    """Test local ChromaDB upsert and similarity query."""
    store = ChromaStore(persist_dir=TEST_CHROMA_DIR)
    
    feedback_ids = ["fb_1", "fb_2"]
    # Simulated 4-dimensional normalized vectors
    embeddings = [
        [0.1, 0.2, 0.8, 0.9],
        [0.9, 0.8, 0.1, 0.2]
    ]
    documents = [
        "The sizing on this dress is too small.",
        "Waiting for the upcoming Diwali sale before buying."
    ]
    metadatas = [
        {"category": "Apparel", "barrier": "size_uncertainty"},
        {"category": "Apparel", "barrier": "price_waiting"}
    ]

    count = store.add_feedback_embeddings(
        feedback_ids=feedback_ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas
    )
    assert count == 2

    # Query with vector close to fb_1
    query_vec = [0.12, 0.22, 0.78, 0.88]
    results = store.query_feedback(query_embedding=query_vec, top_k=1)
    assert len(results) == 1
    assert results[0]["id"] == "fb_1"
    assert results[0]["metadata"]["barrier"] == "size_uncertainty"
