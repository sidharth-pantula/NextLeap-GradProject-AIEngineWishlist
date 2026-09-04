"""Thread-safe SQLite database manager and query helper class."""
import json
import os
import sqlite3
from contextlib import contextmanager
from typing import Any, Dict, Generator, List, Optional, Tuple

from .schema import init_db


class Database:
    """SQLite Database wrapper providing connection management and high-level CRUD methods."""

    def __init__(self, db_path: str = "data/discovery_engine.db"):
        self.db_path = db_path
        db_dir = os.path.dirname(db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        init_db(db_path=self.db_path)

    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager for acquiring SQLite connection with foreign keys enabled."""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def execute_query(self, query: str, params: Tuple = ()) -> List[Dict[str, Any]]:
        """Execute a SELECT query and return list of dict rows."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def execute_write(self, query: str, params: Tuple = ()) -> int:
        """Execute INSERT/UPDATE/DELETE query and return affected row count."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.rowcount

    def insert_raw_feedback(self, record: Dict[str, Any]) -> bool:
        """Insert a single normalized raw feedback record."""
        return self.batch_insert_raw_feedback([record]) == 1

    def batch_insert_raw_feedback(self, records: List[Dict[str, Any]]) -> int:
        """Batch insert raw feedback records, ignoring exact duplicate primary keys."""
        if not records:
            return 0
        sql = """
        INSERT OR IGNORE INTO raw_feedback (
            feedback_id, source, source_type, source_id, date,
            text, title, url, product, category,
            rating, engagement, metadata_json, collection_timestamp
        ) VALUES (
            :feedback_id, :source, :source_type, :source_id, :date,
            :text, :title, :url, :product, :category,
            :rating, :engagement, :metadata_json, :collection_timestamp
        );
        """
        formatted = []
        for r in records:
            meta = r.get("metadata_json") or r.get("metadata")
            if isinstance(meta, (dict, list)):
                meta_str = json.dumps(meta)
            else:
                meta_str = str(meta) if meta is not None else None

            formatted.append({
                "feedback_id": r["feedback_id"],
                "source": r["source"],
                "source_type": r.get("source_type", "comment"),
                "source_id": r.get("source_id"),
                "date": r.get("date"),
                "text": r["text"],
                "title": r.get("title"),
                "url": r.get("url"),
                "product": r.get("product"),
                "category": r.get("category"),
                "rating": r.get("rating"),
                "engagement": r.get("engagement", 0),
                "metadata_json": meta_str,
                "collection_timestamp": r["collection_timestamp"]
            })

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany(sql, formatted)
            return cursor.rowcount

    def batch_insert_processed_feedback(self, records: List[Dict[str, Any]]) -> int:
        """Insert or replace processed structured feedback records."""
        if not records:
            return 0
        sql = """
        INSERT OR REPLACE INTO processed_feedback (
            feedback_id, relevance_score, relevance_reason, relevance_confidence,
            user_intent, wishlist_reason, purchase_intent, purchase_barrier,
            purchase_hesitation, purchase_postponement_reason, uncertainty_type,
            information_needed, decision_stage, behaviour_after_interest,
            comparison_behaviour, external_search_behaviour, competitor_behaviour,
            purchase_outcome, product_category, product_type, price_sensitivity,
            fit_concern, size_concern, quality_concern, material_concern,
            styling_concern, occasion_concern, review_concern, social_validation_need,
            trust_concern, availability_concern, return_exchange_concern,
            user_segment_signals, evidence_strength, evidence_span, evidence_type,
            inferred_user_need, inference_confidence, cluster_id, processing_timestamp
        ) VALUES (
            :feedback_id, :relevance_score, :relevance_reason, :relevance_confidence,
            :user_intent, :wishlist_reason, :purchase_intent, :purchase_barrier,
            :purchase_hesitation, :purchase_postponement_reason, :uncertainty_type,
            :information_needed, :decision_stage, :behaviour_after_interest,
            :comparison_behaviour, :external_search_behaviour, :competitor_behaviour,
            :purchase_outcome, :product_category, :product_type, :price_sensitivity,
            :fit_concern, :size_concern, :quality_concern, :material_concern,
            :styling_concern, :occasion_concern, :review_concern, :social_validation_need,
            :trust_concern, :availability_concern, :return_exchange_concern,
            :user_segment_signals, :evidence_strength, :evidence_span, :evidence_type,
            :inferred_user_need, :inference_confidence, :cluster_id, :processing_timestamp
        );
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany(sql, records)
            return cursor.rowcount

    def batch_insert_shopper_sessions(self, sessions: List[Dict[str, Any]]) -> int:
        """Batch insert e-commerce session logs (e.g. from jlh/uci-shopper)."""
        if not sessions:
            return 0
        sql = """
        INSERT INTO shopper_sessions (
            administrative_pages, administrative_duration, informational_pages,
            informational_duration, product_related_pages, product_related_duration,
            bounce_rate, exit_rate, page_value, special_day, month,
            operating_systems, browser, region, traffic_type, visitor_type,
            weekend, revenue_converted
        ) VALUES (
            :administrative_pages, :administrative_duration, :informational_pages,
            :informational_duration, :product_related_pages, :product_related_duration,
            :bounce_rate, :exit_rate, :page_value, :special_day, :month,
            :operating_systems, :browser, :region, :traffic_type, :visitor_type,
            :weekend, :revenue_converted
        );
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany(sql, sessions)
            return cursor.rowcount

    def batch_insert_wishlist_records(self, records: List[Dict[str, Any]]) -> int:
        """Batch insert or replace synthetic wishlist records."""
        if not records:
            return 0
        sql = """
        INSERT OR REPLACE INTO wishlist_records (
            wishlist_id, customer_id, product_id, added_date, product_category,
            price_at_addition, current_price, price_alert_set, purchased,
            purchase_date, days_in_wishlist, price_drop_pct, converted_within_30_days,
            is_synthetic, source_dataset
        ) VALUES (
            :wishlist_id, :customer_id, :product_id, :added_date, :product_category,
            :price_at_addition, :current_price, :price_alert_set, :purchased,
            :purchase_date, :days_in_wishlist, :price_drop_pct, :converted_within_30_days,
            :is_synthetic, :source_dataset
        );
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany(sql, records)
            return cursor.rowcount

    def batch_insert_ecommerce_events(self, events: List[Dict[str, Any]]) -> int:
        """Batch insert e-commerce progression events (view, cart, purchase)."""
        if not events:
            return 0
        sql = """
        INSERT INTO ecommerce_events (
            event_type, event_time, product_id, user_id, user_session,
            price, category, brand, source_dataset
        ) VALUES (
            :event_type, :event_time, :product_id, :user_id, :user_session,
            :price, :category, :brand, :source_dataset
        );
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany(sql, events)
            return cursor.rowcount

    def get_summary_counts(self) -> Dict[str, int]:
        """Return row counts for key tables."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM raw_feedback;")
            raw_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM processed_feedback;")
            proc_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM processed_feedback WHERE relevance_score >= 2;")
            relevant_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM shopper_sessions;")
            session_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM wishlist_records;")
            wishlist_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM ecommerce_events;")
            ecom_count = cursor.fetchone()[0]
            return {
                "raw_feedback": raw_count,
                "processed_feedback": proc_count,
                "relevant_feedback": relevant_count,
                "shopper_sessions": session_count,
                "wishlist_records": wishlist_count,
                "ecommerce_events": ecom_count
            }


_db_instance: Optional[Database] = None


def get_db(db_path: str = "data/discovery_engine.db") -> Database:
    """Get or create singleton Database instance."""
    global _db_instance
    if _db_instance is None or _db_instance.db_path != db_path:
        _db_instance = Database(db_path=db_path)
    return _db_instance
