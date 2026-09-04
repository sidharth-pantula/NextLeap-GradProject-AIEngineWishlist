"""Unit tests for Phase 2: Collectors, Quota Managers & Schema Normalization."""
import os
import shutil
import pytest
from database.db import Database
from collectors.youtube_quota_manager import YouTubeQuotaManager
from collectors.youtube_collector import YouTubeCollector
from collectors.serper_budget_manager import SerperBudgetManager
from collectors.hf_dataset_loader import HFDatasetLoader
from collectors.reddit_collector import RedditCollector


TEST_DB_PATH = "data/test_phase2_db.db"


@pytest.fixture(autouse=True)
def setup_teardown():
    """Setup and teardown test artifacts."""
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
    yield
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)


def test_youtube_quota_manager(monkeypatch):
    """Test YouTube quota estimation and pre-flight safety cutoff."""
    monkeypatch.setenv("YOUTUBE_API_KEY", "dummy_yt_key")
    db = Database(db_path=TEST_DB_PATH)
    manager = YouTubeQuotaManager(daily_quota_limit=200, initial_test_quota_limit=150, db=db)

    # Initial state
    assert manager.get_estimated_quota_used() == 0
    allowed, msg = manager.can_make_request("search.list", is_initial_test=True)
    assert allowed is True

    # Record 1 search call (100 units)
    manager.record_request("search.list", "Myntra wishlist", "SUCCESS", result_count=5)
    assert manager.get_estimated_quota_used() == 100

    # Second search call requires 100 units, but 100+100 > 150 (initial test limit)
    allowed, msg = manager.can_make_request("search.list", is_initial_test=True)
    assert allowed is False
    assert "Quota limit reached" in msg

    # But commentThreads.list requires only 1 unit, 100+1 <= 150, so it is allowed
    allowed, msg = manager.can_make_request("commentThreads.list", is_initial_test=True)
    assert allowed is True


def test_youtube_metadata_relevance_scoring():
    """Test video metadata scoring algorithm."""
    collector = YouTubeCollector(db=Database(db_path=TEST_DB_PATH))
    
    score_high = collector.score_video_metadata_relevance(
        title="Why I didn't buy items from my Myntra wishlist",
        description="Explaining my hesitation and sizing uncertainties.",
        category="wishlist"
    )
    assert score_high == 4

    score_med = collector.score_video_metadata_relevance(
        title="Myntra Winter Clothing Haul and Sizing Review",
        description="Trying out jackets and comparing fits.",
        category="fit"
    )
    assert score_med == 3

    score_low = collector.score_video_metadata_relevance(
        title="Everyday Morning Routine and Outfit",
        description="What I wear to college.",
        category="general"
    )
    assert score_low == 2


def test_youtube_normalization_to_raw_feedback():
    """Test converting raw YouTube comment into raw_feedback schema."""
    db = Database(db_path=TEST_DB_PATH)
    collector = YouTubeCollector(db=db)

    raw_comment = {
        "comment_id": "comment_abc_123",
        "video_id": "vid_xyz_789",
        "text": "I really wanted to buy this dress but the size chart makes no sense.",
        "published_at": "2026-08-25T10:00:00Z",
        "like_count": 14,
        "author_name": "FashionShopper",
        "url": "https://youtube.com/watch?v=vid_xyz_789&lc=comment_abc_123",
        "search_query": "Myntra sizing problem",
        "research_category": "G_fit_and_size",
        "collection_timestamp": "2026-08-27T10:00:00Z"
    }

    norm = collector.normalize_record(raw_comment)
    assert norm["feedback_id"] == "yt_comment_abc_123"
    assert norm["source"] == "youtube"
    assert norm["source_type"] == "comment"
    assert norm["engagement"] == 14
    assert norm["category"] == "G_fit_and_size"

    # Save and verify
    saved = collector.save_normalized([norm])
    assert saved == 1

    counts = db.get_summary_counts()
    assert counts["raw_feedback"] == 1


def test_hf_loader_normalization():
    """Test Hugging Face review normalization."""
    db = Database(db_path=TEST_DB_PATH)
    loader = HFDatasetLoader(db=db)

    raw_review = {
        "id": "hf_rev_101",
        "text": "Fabric is sheer and stitching came off after one wear. Disappointed.",
        "product_name": "Floral Summer Dress",
        "category": "Apparel",
        "rating": 1.0,
        "helpful_votes": 8
    }

    norm = loader.normalize_record(raw_review)
    assert norm["feedback_id"] == "hf_hf_rev_101"
    assert norm["source"] == "huggingface"
    assert norm["source_type"] == "product_review"
    assert norm["rating"] == 1.0

    saved = loader.save_normalized([norm])
    assert saved == 1


def test_reddit_loader_normalization():
    """Test Reddit post normalization."""
    db = Database(db_path=TEST_DB_PATH)
    collector = RedditCollector(db=db)

    raw_post = {
        "id": "rd_post_999",
        "title": "Why do you guys keep clothes in wishlist forever?",
        "text": "I currently have 45 items in my AJIO wishlist. Mostly waiting for a 60% sale.",
        "subreddit": "IndianFashionAddicts",
        "score": 35,
        "num_comments": 18
    }

    norm = collector.normalize_record(raw_post)
    assert norm["feedback_id"] == "rd_rd_post_999"
    assert norm["source"] == "reddit"
    assert norm["engagement"] == 35

    saved = collector.save_normalized([norm])
    assert saved == 1
