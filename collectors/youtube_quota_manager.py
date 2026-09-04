"""YouTube Data API Quota & Rate Limit Controller."""
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from dotenv import load_dotenv

from database.db import Database, get_db

load_dotenv()

# Quota costs as defined by YouTube Data API v3
QUOTA_COSTS = {
    "search.list": 100,
    "commentThreads.list": 1,
    "videos.list": 1
}


class YouTubeQuotaManager:
    """Tracks YouTube Data API quota expenditure and enforces safety cutoffs."""

    def __init__(
        self,
        daily_quota_limit: int = 10000,
        initial_test_quota_limit: int = 1500,
        db: Optional[Database] = None
    ):
        self.daily_quota_limit = daily_quota_limit
        self.initial_test_quota_limit = initial_test_quota_limit
        self.db = db or get_db()
        self.api_key = os.getenv("YOUTUBE_API_KEY")

    def get_estimated_quota_used(self) -> int:
        """Calculate total estimated quota units spent recorded in database."""
        rows = self.db.execute_query(
            "SELECT SUM(estimated_quota_units) as total_units FROM youtube_api_requests WHERE status = 'SUCCESS';"
        )
        if rows and rows[0]["total_units"]:
            return int(rows[0]["total_units"])
        return 0

    def can_make_request(self, endpoint: str, is_initial_test: bool = True) -> Tuple[bool, str]:
        """Pre-flight check before making a YouTube API call."""
        if not self.api_key:
            return False, "YOUTUBE_API_KEY is missing from environment variables."

        cost = QUOTA_COSTS.get(endpoint, 1)
        used = self.get_estimated_quota_used()
        limit = self.initial_test_quota_limit if is_initial_test else self.daily_quota_limit

        if used + cost > limit:
            return False, f"Quota limit reached: {used}/{limit} units spent. Required {cost} for {endpoint}."

        return True, "Quota check passed."

    def record_request(
        self,
        endpoint: str,
        query_or_video_id: str,
        status: str,
        result_count: int = 0,
        error: Optional[str] = None
    ) -> None:
        """Log YouTube API request and estimated quota cost to SQLite."""
        now = datetime.now(timezone.utc).isoformat()
        cost = QUOTA_COSTS.get(endpoint, 1) if status == "SUCCESS" else 0
        sql = """
        INSERT INTO youtube_api_requests (
            timestamp, endpoint, query_or_video_id, status, estimated_quota_units, result_count, error
        ) VALUES (
            :timestamp, :endpoint, :query_or_video_id, :status, :estimated_quota_units, :result_count, :error
        );
        """
        self.db.execute_write(
            sql,
            {
                "timestamp": now,
                "endpoint": endpoint,
                "query_or_video_id": query_or_video_id,
                "status": status,
                "estimated_quota_units": cost,
                "result_count": result_count,
                "error": error
            }
        )

    def get_quota_summary(self) -> Dict[str, Any]:
        """Return comprehensive quota metrics."""
        used = self.get_estimated_quota_used()
        success_rows = self.db.execute_query(
            "SELECT COUNT(*) as count FROM youtube_api_requests WHERE status = 'SUCCESS';"
        )
        fail_rows = self.db.execute_query(
            "SELECT COUNT(*) as count FROM youtube_api_requests WHERE status = 'FAILURE';"
        )
        video_count_rows = self.db.execute_query(
            "SELECT COUNT(*) as count FROM youtube_videos;"
        )
        comment_count_rows = self.db.execute_query(
            "SELECT COUNT(*) as count FROM youtube_comments;"
        )

        return {
            "estimated_quota_used": used,
            "daily_quota_limit": self.daily_quota_limit,
            "initial_test_quota_limit": self.initial_test_quota_limit,
            "remaining_quota": max(0, self.daily_quota_limit - used),
            "successful_requests": success_rows[0]["count"] if success_rows else 0,
            "failed_requests": fail_rows[0]["count"] if fail_rows else 0,
            "total_videos_collected": video_count_rows[0]["count"] if video_count_rows else 0,
            "total_comments_collected": comment_count_rows[0]["count"] if comment_count_rows else 0
        }
