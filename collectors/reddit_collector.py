"""Reddit Collector for Fashion Community Post & Discussion Ingestion."""
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from database.db import Database, get_db
from .base_collector import BaseCollector


class RedditCollector(BaseCollector):
    """Ingests public Reddit submissions and comments from local JSON/CSV files or public datasets."""

    def __init__(self, db: Optional[Database] = None):
        super().__init__(db=db)

    def load_from_json_file(self, file_path: str, subreddit: str = "IndianFashionAddicts") -> int:
        """Load Reddit posts/comments from a JSON file into raw_feedback."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Reddit file not found: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        records = data if isinstance(data, list) else data.get("posts", data.get("comments", []))
        normalized = []
        for r in records:
            r["subreddit"] = subreddit
            normalized.append(self.normalize_record(r))

        return self.save_normalized(normalized)

    def normalize_record(self, raw_item: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Reddit post/comment into standardized raw_feedback schema."""
        now = datetime.now(timezone.utc).isoformat()
        r_id = str(raw_item.get("id", raw_item.get("post_id", hash(raw_item.get("text", "")))))
        return {
            "feedback_id": f"rd_{r_id}",
            "source": "reddit",
            "source_type": raw_item.get("source_type", "post"),
            "source_id": r_id,
            "date": raw_item.get("created_utc", raw_item.get("date", now)),
            "text": raw_item.get("text", raw_item.get("selftext", raw_item.get("body", ""))),
            "title": raw_item.get("title"),
            "url": raw_item.get("permalink", raw_item.get("url")),
            "product": raw_item.get("product_name"),
            "category": raw_item.get("category", "fashion"),
            "rating": None,
            "engagement": raw_item.get("score", raw_item.get("upvotes", 0)),
            "metadata_json": {
                "subreddit": raw_item.get("subreddit", "fashion"),
                "num_comments": raw_item.get("num_comments", 0),
                "author": raw_item.get("author")
            },
            "collection_timestamp": now
        }

    def collect(self, file_path: Optional[str] = None) -> List[Dict[str, Any]]:
        """Collect Reddit records if a file is provided."""
        if file_path and os.path.exists(file_path):
            count = self.load_from_json_file(file_path)
            return [{"records_loaded": count}]
        return []
