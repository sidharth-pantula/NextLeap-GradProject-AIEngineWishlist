"""Unit tests for Serper Budget Controller and Free Credit Safeguards."""
import os
import shutil
import pytest
from database.db import Database
from collectors.serper_budget_manager import SerperBudgetManager


TEST_DB_PATH = "data/test_serper_db.db"
TEST_CONFIG_PATH = "config/test_serper_budget_config.json"


@pytest.fixture(autouse=True)
def setup_teardown():
    """Setup and teardown test artifacts."""
    for path in [TEST_DB_PATH, TEST_CONFIG_PATH]:
        if os.path.exists(path):
            os.remove(path)

    # Write a test budget config with small limits
    import json
    with open(TEST_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump({
            "budget_mode": "FREE_ONLY",
            "max_requests": 5,
            "initial_test_requests": 2,
            "pagination_enabled": False,
            "automatic_retry_enabled": False,
            "cache_enabled": True
        }, f)

    yield

    for path in [TEST_DB_PATH, TEST_CONFIG_PATH]:
        if os.path.exists(path):
            os.remove(path)


def test_budget_manager_initial_state(monkeypatch):
    """Test initial budget status with configured limits."""
    monkeypatch.setenv("SERPER_API_KEY", "test_key_123")
    db = Database(db_path=TEST_DB_PATH)
    manager = SerperBudgetManager(config_path=TEST_CONFIG_PATH, db=db)

    summary = manager.get_budget_summary()
    assert summary["budget_mode"] == "FREE_ONLY"
    assert summary["max_requests_ceiling"] == 5
    assert summary["initial_test_limit"] == 2
    assert summary["total_network_requests_made"] == 0
    assert summary["remaining_request_allowance"] == 5


def test_pre_flight_limit_enforcement(monkeypatch):
    """Test pre-flight check blocks requests when limits are met."""
    monkeypatch.setenv("SERPER_API_KEY", "test_key_123")
    db = Database(db_path=TEST_DB_PATH)
    manager = SerperBudgetManager(config_path=TEST_CONFIG_PATH, db=db)

    # Allowed for first request
    allowed, msg = manager.can_make_request(batch_request_count=0, is_initial_test=True)
    assert allowed is True

    # Blocked if initial test batch reaches limit (2)
    blocked, reason = manager.can_make_request(batch_request_count=2, is_initial_test=True)
    assert blocked is False
    assert "Initial test batch limit reached" in reason


def test_hard_ceiling_enforcement(monkeypatch):
    """Test hard max request ceiling (5) completely blocks calls."""
    monkeypatch.setenv("SERPER_API_KEY", "test_key_123")
    db = Database(db_path=TEST_DB_PATH)
    manager = SerperBudgetManager(config_path=TEST_CONFIG_PATH, db=db)

    # Record 5 requests in database
    for i in range(5):
        manager.record_request(
            query=f"query {i}",
            category="test",
            request_number=i + 1,
            status="SUCCESS",
            result_count=10
        )

    assert manager.get_total_api_calls_made() == 5
    blocked, reason = manager.can_make_request(batch_request_count=0, is_initial_test=False)
    assert blocked is False
    assert "Hard ceiling reached" in reason


def test_cache_lookup():
    """Test query caching prevents duplicate requests."""
    db = Database(db_path=TEST_DB_PATH)
    manager = SerperBudgetManager(config_path=TEST_CONFIG_PATH, db=db)

    # Initially empty cache
    assert manager.get_cached_results("Myntra wishlist") is None

    # Insert a fake search result into SQLite
    db.execute_write("""
        INSERT INTO web_search_results (
            query, research_category, search_timestamp, rank, title, url, snippet, domain
        ) VALUES (
            'Myntra wishlist', 'wishlist', '2026-08-27T10:00:00Z', 1, 'Myntra Wishlist Discussion',
            'https://reddit.com/r/test', 'Snippet text', 'reddit.com'
        );
    """)

    cached = manager.get_cached_results("Myntra wishlist")
    assert cached is not None
    assert len(cached) == 1
    assert cached[0]["title"] == "Myntra Wishlist Discussion"
