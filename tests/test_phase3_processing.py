"""Unit tests for Phase 3: Cleaning, Deduplication & Relevance Filtering."""
import os
import pytest
from database.db import Database
from processing.cleaning import TextCleaner
from processing.deduplication import Deduplicator
from processing.relevance import RelevanceClassifier


TEST_DB_PATH = "data/test_phase3_db.db"


@pytest.fixture(autouse=True)
def setup_teardown():
    """Setup and teardown test artifacts."""
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
    yield
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)


def test_text_cleaner_html_and_whitespace():
    """Test HTML tag removal and whitespace normalization."""
    cleaner = TextCleaner()
    raw_html = "<div><p>This is a <strong>great dress</strong> but &amp; the sizing is off.</p></div>"
    result = cleaner.clean(raw_html)

    assert result["is_valid"] is True
    assert result["cleaned_text"] == "This is a great dress but & the sizing is off."
    assert len(result["flags"]) == 0


def test_text_cleaner_spam_and_bot_detection():
    """Test detection of bot notifications and affiliate spam."""
    cleaner = TextCleaner()
    
    bot_msg = "I am a bot! This is a reminder to ensure that your recent submission in r/IndianFashionAddicts follows all rules."
    res_bot = cleaner.clean(bot_msg)
    assert res_bot["is_valid"] is False
    assert "bot_or_spam_pattern" in res_bot["flags"]

    short_msg = "Cute."
    res_short = cleaner.clean(short_msg)
    assert res_short["is_valid"] is False
    assert "too_short" in res_short["flags"]


def test_deduplicator_exact_and_near_duplicates():
    """Test exact SHA-256 and Jaccard near-duplicate detection."""
    dedup = Deduplicator(jaccard_threshold=0.80)

    doc1 = "I have had 10 items in my Myntra wishlist for months waiting for the EORS sale."
    doc2 = "I have had 10 items in my Myntra wishlist for months waiting for the EORS sale. "  # exact with extra whitespace
    doc3 = "I have had 10 items in my Myntra wishlist for months waiting for the big EORS sale."  # near duplicate
    doc4 = "The sizing chart on AJIO is completely inaccurate and the return process took 3 weeks."

    # Index doc1
    dedup.add("doc_1", doc1)

    # doc2 exact match
    is_dup, dup_type, matched_id = dedup.check_duplicate(doc2)
    assert is_dup is True
    assert dup_type == "EXACT_SHA256"
    assert matched_id == "doc_1"

    # doc3 near duplicate match
    is_dup_near, dup_type_near, matched_near = dedup.check_duplicate(doc3)
    assert is_dup_near is True
    assert "NEAR_DUPLICATE" in dup_type_near
    assert matched_near == "doc_1"

    # doc4 distinct
    is_dup_4, _, _ = dedup.check_duplicate(doc4)
    assert is_dup_4 is False


def test_relevance_classifier_grading():
    """Test 0-3 relevance grading rules."""
    classifier = RelevanceClassifier()

    # Score 3: High intent / wishlist / hesitation
    res_3 = classifier.score_record("I keep wishlisting dresses on Myntra but hesitate to buy because I am waiting for price drops.")
    assert res_3["relevance_score"] == 3

    # Score 2: Sizing / fabric friction
    res_2 = classifier.score_record("The fabric quality was terrible and the size didn't fit properly so I had to return it.")
    assert res_2["relevance_score"] == 2

    # Score 1: General fashion compliment
    res_1 = classifier.score_record("This is such a pretty dress, love the color and aesthetic look on you!")
    assert res_1["relevance_score"] == 1

    # Score 0: Irrelevant / spam
    res_0 = classifier.score_record("Download Midas Merge game now using my referral link!")
    assert res_0["relevance_score"] == 0


def test_batch_processing_into_processed_feedback():
    """Test processing pipeline from raw_feedback to processed_feedback in SQLite."""
    db = Database(db_path=TEST_DB_PATH)
    classifier = RelevanceClassifier(db=db)

    # Insert raw feedback records
    db.batch_insert_raw_feedback([
        {
            "feedback_id": "test_fb_1",
            "source": "youtube",
            "source_type": "comment",
            "text": "I added this jacket to my wishlist 2 months ago, still waiting for a 50% discount.",
            "collection_timestamp": "2026-08-27T10:00:00Z"
        },
        {
            "feedback_id": "test_fb_2",
            "source": "web",
            "source_type": "forum_discussion",
            "text": "The sizing chart on AJIO is confusing so I had to return both pairs of shoes.",
            "collection_timestamp": "2026-08-27T10:00:00Z"
        }
    ])

    processed_count = classifier.process_raw_feedback_batch(limit=10)
    assert processed_count == 2

    # Verify rows in processed_feedback
    rows = db.execute_query("SELECT * FROM processed_feedback;")
    assert len(rows) == 2
    assert rows[0]["relevance_score"] in [2, 3]
    assert rows[1]["relevance_score"] in [2, 3]
