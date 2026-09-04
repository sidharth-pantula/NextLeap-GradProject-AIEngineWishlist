"""Centralized budget controller for Serper API to strictly enforce free-credit limits."""
import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv

from database.db import Database, get_db

load_dotenv()

DEFAULT_CONFIG_PATH = "config/serper_budget_config.json"


class SerperBudgetManager:
    """Strict budget controller ensuring Serper API never exceeds free credit allowance.
    
    Hard constraints:
    - FREE_ONLY mode
    - Max 50 requests absolute ceiling
    - Initial test limit: 10 requests
    - Pagination OFF, Retry OFF, Background searches OFF
    - Query result caching (never call Serper twice for the same query)
    """

    def __init__(self, config_path: str = DEFAULT_CONFIG_PATH, db: Optional[Database] = None):
        self.config_path = config_path
        self.db = db or get_db()
        self.config = self._load_config()
        self.api_key = os.getenv("SERPER_API_KEY")

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration parameters with safe defaults."""
        defaults = {
            "budget_mode": "FREE_ONLY",
            "max_requests": 50,
            "initial_test_requests": 10,
            "pagination_enabled": False,
            "automatic_retry_enabled": False,
            "cache_enabled": True,
            "require_manual_confirmation_after_batch": true if hasattr(bool, 'true') else True
        }
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    defaults.update(loaded)
            except Exception:
                pass
        return defaults

    def get_total_api_calls_made(self) -> int:
        """Count actual network HTTP requests made to Serper recorded in database."""
        rows = self.db.execute_query(
            "SELECT COUNT(*) as count FROM web_search_requests WHERE status IN ('SUCCESS', 'FAILURE');"
        )
        return rows[0]["count"] if rows else 0

    def can_make_request(self, batch_request_count: int = 0, is_initial_test: bool = True) -> Tuple[bool, str]:
        """Pre-flight check before making a Serper API call."""
        if not self.api_key:
            return False, "SERPER_API_KEY is missing from environment variables."

        total_made = self.get_total_api_calls_made()
        max_allowed = self.config.get("max_requests", 50)
        test_limit = self.config.get("initial_test_requests", 10)

        # Hard limit check
        if total_made >= max_allowed:
            return False, f"Hard ceiling reached: {total_made}/{max_allowed} API requests made. Aborting to protect free credits."

        # Initial test limit check
        if is_initial_test and batch_request_count >= test_limit:
            return False, f"Initial test batch limit reached: {batch_request_count}/{test_limit} requests executed. Stopping test."

        return True, "Budget check passed."

    def get_cached_results(self, query: str) -> Optional[List[Dict[str, Any]]]:
        """Check if query results are already cached in SQLite."""
        if not self.config.get("cache_enabled", True):
            return None

        clean_query = query.strip()
        rows = self.db.execute_query(
            "SELECT * FROM web_search_results WHERE query = :query ORDER BY rank ASC;",
            {"query": clean_query}
        )
        return rows if rows else None

    def record_request(
        self,
        query: str,
        category: str,
        request_number: int,
        status: str,
        result_count: int = 0,
        error: Optional[str] = None,
        estimated_usage: float = 0.0
    ) -> None:
        """Log API request attempt to SQLite for auditability."""
        now = datetime.now(timezone.utc).isoformat()
        sql = """
        INSERT INTO web_search_requests (
            timestamp, query, category, request_number, status, result_count, error, estimated_usage
        ) VALUES (
            :timestamp, :query, :category, :request_number, :status, :result_count, :error, :estimated_usage
        );
        """
        self.db.execute_write(
            sql,
            {
                "timestamp": now,
                "query": query,
                "category": category,
                "request_number": request_number,
                "status": status,
                "result_count": result_count,
                "error": error,
                "estimated_usage": estimated_usage
            }
        )

    def get_budget_summary(self) -> Dict[str, Any]:
        """Return full budget and request summary statistics."""
        total_calls = self.get_total_api_calls_made()
        max_allowed = self.config.get("max_requests", 50)
        test_limit = self.config.get("initial_test_requests", 10)

        success_rows = self.db.execute_query(
            "SELECT COUNT(*) as count FROM web_search_requests WHERE status = 'SUCCESS';"
        )
        cached_rows = self.db.execute_query(
            "SELECT COUNT(*) as count FROM web_search_requests WHERE status = 'CACHED';"
        )
        fail_rows = self.db.execute_query(
            "SELECT COUNT(*) as count FROM web_search_requests WHERE status = 'FAILURE';"
        )
        unique_urls_rows = self.db.execute_query(
            "SELECT COUNT(DISTINCT url) as count FROM web_search_results WHERE url IS NOT NULL;"
        )
        total_results_rows = self.db.execute_query(
            "SELECT COUNT(*) as count FROM web_search_results;"
        )

        return {
            "budget_mode": self.config.get("budget_mode", "FREE_ONLY"),
            "max_requests_ceiling": max_allowed,
            "initial_test_limit": test_limit,
            "total_network_requests_made": total_calls,
            "successful_requests": success_rows[0]["count"] if success_rows else 0,
            "cached_requests_served": cached_rows[0]["count"] if cached_rows else 0,
            "failed_requests": fail_rows[0]["count"] if fail_rows else 0,
            "remaining_request_allowance": max(0, max_allowed - total_calls),
            "total_search_results_stored": total_results_rows[0]["count"] if total_results_rows else 0,
            "unique_urls_collected": unique_urls_rows[0]["count"] if unique_urls_rows else 0,
            "pagination_enabled": self.config.get("pagination_enabled", False),
            "automatic_retry_enabled": self.config.get("automatic_retry_enabled", False)
        }
