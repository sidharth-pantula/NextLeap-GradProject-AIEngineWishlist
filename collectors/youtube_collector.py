"""YouTube Data Collector for Video Discovery and Comment Ingestion."""
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from database.db import Database, get_db
from .base_collector import BaseCollector
from .youtube_quota_manager import YouTubeQuotaManager

load_dotenv()

DEFAULT_QUERIES_PATH = "config/youtube_search_queries.json"


class YouTubeCollector(BaseCollector):
    """Discovers fashion shopping videos and extracts comment discussions via YouTube Data API v3."""

    def __init__(
        self,
        quota_manager: Optional[YouTubeQuotaManager] = None,
        db: Optional[Database] = None,
        queries_path: str = DEFAULT_QUERIES_PATH
    ):
        super().__init__(db=db)
        self.quota_manager = quota_manager or YouTubeQuotaManager(db=self.db)
        self.queries_path = queries_path
        self.api_key = os.getenv("YOUTUBE_API_KEY")
        self._youtube_client = None

    def _get_client(self):
        """Initialize Google API client."""
        if not self.api_key:
            raise ValueError("YOUTUBE_API_KEY is not configured in environment.")
        if self._youtube_client is None:
            self._youtube_client = build("youtube", "v3", developerKey=self.api_key)
        return self._youtube_client

    def score_video_metadata_relevance(self, title: str, description: str, category: str) -> int:
        """Lightweight 0-4 relevance score based on video metadata before comment retrieval."""
        import re
        text = f"{title} {description}".lower()
        
        # High relevance keywords (4 = directly relevant to wishlist/hesitation/conversion)
        high_intent_patterns = [
            r"\bwishlist\b", r"\bhesitate\b", r"\bhesitation\b", r"\bpostpone\b",
            r"\bwhy i (didn't|did not|don't) buy\b", r"\bcart\b", r"\bregret buying\b"
        ]
        
        # Relevant keywords (3 = relevant purchase-decision discussion)
        relevant_patterns = [
            r"\bsizing\b", r"\bfit\b", r"\bquality\b", r"\breview\b", r"\bhaul\b",
            r"\beors\b", r"\bsale\b", r"\bprice drop\b", r"\bmyntra\b", r"\bajio\b",
            r"\bcompar(e|ing|ison)\b"
        ]

        # Peripheral keywords (2 = general fashion/clothes discussion)
        peripheral_patterns = [
            r"\bfashion\b", r"\bclothes\b", r"\bshopping\b", r"\boutfit\b"
        ]

        if any(re.search(pat, text) for pat in high_intent_patterns):
            return 4
        elif any(re.search(pat, text) for pat in relevant_patterns):
            return 3
        elif any(re.search(pat, text) for pat in peripheral_patterns):
            return 2
        return 1

    def search_videos(
        self,
        query: str,
        category: str = "general",
        max_results: int = 5,
        is_initial_test: bool = True
    ) -> List[Dict[str, Any]]:
        """Search YouTube for relevant videos matching query."""
        now = datetime.now(timezone.utc).isoformat()
        
        # Pre-flight quota check
        allowed, msg = self.quota_manager.can_make_request("search.list", is_initial_test=is_initial_test)
        if not allowed:
            self.quota_manager.record_request("search.list", query, "BLOCKED", 0, msg)
            raise RuntimeError(f"YouTube search blocked: {msg}")

        client = self._get_client()
        try:
            request = client.search().list(
                part="snippet",
                q=query,
                type="video",
                maxResults=max_results,
                relevanceLanguage="en"
            )
            response = request.execute()
            items = response.get("items", [])
        except HttpError as e:
            err_msg = str(e)
            self.quota_manager.record_request("search.list", query, "FAILURE", 0, err_msg)
            raise RuntimeError(f"YouTube search API error: {err_msg}")

        self.quota_manager.record_request("search.list", query, "SUCCESS", len(items))

        videos = []
        for item in items:
            vid_id = item["id"].get("videoId")
            if not vid_id:
                continue
            snippet = item.get("snippet", {})
            title = snippet.get("title", "")
            desc = snippet.get("description", "")
            channel_id = snippet.get("channelId", "")
            channel_name = snippet.get("channelTitle", "")
            published_at = snippet.get("publishedAt", "")
            url = f"https://www.youtube.com/watch?v={vid_id}"

            rel_score = self.score_video_metadata_relevance(title, desc, category)

            video_record = {
                "video_id": vid_id,
                "title": title,
                "description": desc,
                "channel_id": channel_id,
                "channel_name": channel_name,
                "published_at": published_at,
                "url": url,
                "search_query": query,
                "research_category": category,
                "relevance_score": rel_score,
                "discovery_count": 1,
                "collection_timestamp": now
            }
            videos.append(video_record)

        # Save to youtube_videos table
        if videos:
            sql = """
            INSERT INTO youtube_videos (
                video_id, title, description, channel_id, channel_name,
                published_at, url, search_query, research_category,
                relevance_score, discovery_count, collection_timestamp
            ) VALUES (
                :video_id, :title, :description, :channel_id, :channel_name,
                :published_at, :url, :search_query, :research_category,
                :relevance_score, :discovery_count, :collection_timestamp
            ) ON CONFLICT(video_id) DO UPDATE SET
                discovery_count = youtube_videos.discovery_count + 1;
            """
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.executemany(sql, videos)

        return videos

    def fetch_video_comments(
        self,
        video_id: str,
        category: str = "general",
        search_query: str = "",
        max_comments: int = 20,
        is_initial_test: bool = True
    ) -> List[Dict[str, Any]]:
        """Retrieve comment threads for a given video."""
        now = datetime.now(timezone.utc).isoformat()

        # Pre-flight quota check
        allowed, msg = self.quota_manager.can_make_request("commentThreads.list", is_initial_test=is_initial_test)
        if not allowed:
            self.quota_manager.record_request("commentThreads.list", video_id, "BLOCKED", 0, msg)
            return []

        client = self._get_client()
        try:
            request = client.commentThreads().list(
                part="snippet",
                videoId=video_id,
                maxResults=min(max_comments, 100),
                textFormat="plainText",
                order="relevance"
            )
            response = request.execute()
            items = response.get("items", [])
        except HttpError as e:
            # Some videos have disabled comments or require special access
            self.quota_manager.record_request("commentThreads.list", video_id, "FAILURE", 0, str(e))
            return []

        self.quota_manager.record_request("commentThreads.list", video_id, "SUCCESS", len(items))

        comments = []
        for item in items:
            top_level = item.get("snippet", {}).get("topLevelComment", {}).get("snippet", {})
            comment_id = item.get("id")
            text = top_level.get("textDisplay", "")
            author = top_level.get("authorDisplayName", "")
            pub_at = top_level.get("publishedAt", "")
            upd_at = top_level.get("updatedAt", "")
            likes = top_level.get("likeCount", 0)
            replies = item.get("snippet", {}).get("totalReplyCount", 0)
            url = f"https://www.youtube.com/watch?v={video_id}&lc={comment_id}"

            if not text.strip():
                continue

            comment_rec = {
                "comment_id": comment_id,
                "video_id": video_id,
                "parent_comment_id": None,
                "text": text,
                "published_at": pub_at,
                "updated_at": upd_at,
                "like_count": likes,
                "reply_count": replies,
                "author_name": author,
                "url": url,
                "search_query": search_query,
                "research_category": category,
                "collection_timestamp": now
            }
            comments.append(comment_rec)

        # Save to youtube_comments table
        if comments:
            sql = """
            INSERT OR IGNORE INTO youtube_comments (
                comment_id, video_id, parent_comment_id, text, published_at,
                updated_at, like_count, reply_count, author_name, url,
                search_query, research_category, collection_timestamp
            ) VALUES (
                :comment_id, :video_id, :parent_comment_id, :text, :published_at,
                :updated_at, :like_count, :reply_count, :author_name, :url,
                :search_query, :research_category, :collection_timestamp
            );
            """
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.executemany(sql, comments)

            # Also convert and store into normalized raw_feedback
            normalized = [self.normalize_record(c) for c in comments]
            self.save_normalized(normalized)

        return comments

    def normalize_record(self, raw_item: Dict[str, Any]) -> Dict[str, Any]:
        """Map YouTube comment into the standardized raw_feedback schema."""
        return {
            "feedback_id": f"yt_{raw_item['comment_id']}",
            "source": "youtube",
            "source_type": "comment",
            "source_id": raw_item["comment_id"],
            "date": raw_item.get("published_at"),
            "text": raw_item["text"],
            "title": f"YouTube Video {raw_item.get('video_id')}",
            "url": raw_item.get("url"),
            "product": None,
            "category": raw_item.get("research_category"),
            "rating": None,
            "engagement": raw_item.get("like_count", 0),
            "metadata_json": {
                "video_id": raw_item.get("video_id"),
                "author": raw_item.get("author_name"),
                "replies": raw_item.get("reply_count", 0),
                "query": raw_item.get("search_query")
            },
            "collection_timestamp": raw_item["collection_timestamp"]
        }

    def collect(self, query: str, category: str = "general", max_videos: int = 3, max_comments: int = 15) -> List[Dict[str, Any]]:
        """Run end-to-end video discovery and comment extraction for a query."""
        videos = self.search_videos(query=query, category=category, max_results=max_videos)
        all_comments = []
        for vid in videos:
            # Only fetch comments for videos with relevance >= 2
            if vid.get("relevance_score", 0) >= 2:
                comms = self.fetch_video_comments(
                    video_id=vid["video_id"],
                    category=category,
                    search_query=query,
                    max_comments=max_comments
                )
                all_comments.extend(comms)
        return all_comments

    def run_initial_test(self, limit: int = 10, max_videos_per_query: int = 2, max_comments_per_video: int = 5) -> Dict[str, Any]:
        """Execute strictly the 10 initial test queries and return summary report."""
        if not os.path.exists(self.queries_path):
            raise FileNotFoundError(f"Query config not found: {self.queries_path}")

        with open(self.queries_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        test_queries = data.get("initial_test_queries", [])[:limit]
        executed_queries = []
        errors = []
        total_comments_collected = 0

        for q_item in test_queries:
            query_str = q_item["query"]
            cat_str = q_item["category"]

            try:
                comments = self.collect(
                    query=query_str,
                    category=cat_str,
                    max_videos=max_videos_per_query,
                    max_comments=max_comments_per_video
                )
                total_comments_collected += len(comments)
                executed_queries.append({
                    "query": query_str,
                    "category": cat_str,
                    "comments_extracted": len(comments),
                    "sample_comment": comments[0]["text"][:100] if comments else "No comments"
                })
            except Exception as e:
                errors.append({
                    "query": query_str,
                    "error": str(e)
                })

        summary = self.quota_manager.get_quota_summary()
        summary["test_executed_queries"] = executed_queries
        summary["test_errors"] = errors
        summary["test_comments_collected"] = total_comments_collected
        return summary
