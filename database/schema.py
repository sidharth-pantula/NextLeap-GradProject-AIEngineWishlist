"""SQLite schema definitions and database initialization for the VoC Discovery Engine."""
import os
import sqlite3
from typing import Optional


CREATE_RAW_FEEDBACK_TABLE = """
CREATE TABLE IF NOT EXISTS raw_feedback (
    feedback_id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    source_type TEXT NOT NULL,
    source_id TEXT,
    date TEXT,
    text TEXT NOT NULL,
    title TEXT,
    url TEXT,
    product TEXT,
    category TEXT,
    rating REAL,
    engagement INTEGER DEFAULT 0,
    metadata_json TEXT,
    collection_timestamp TEXT NOT NULL
);
"""

CREATE_PROCESSED_FEEDBACK_TABLE = """
CREATE TABLE IF NOT EXISTS processed_feedback (
    feedback_id TEXT PRIMARY KEY,
    cleaned_text TEXT,
    relevance_score INTEGER NOT NULL,
    relevance_reason TEXT,
    relevance_confidence REAL,
    intent_tier TEXT,
    save_reason_category TEXT,
    wishlist_state TEXT,
    trigger_condition TEXT,
    trigger_type TEXT,
    trigger_category TEXT,
    information_needed_category TEXT,
    current_workaround TEXT,
    option_preservation_signal INTEGER DEFAULT 0,
    scarcity_reaction TEXT,
    reactivation_trigger TEXT,
    user_intent TEXT,
    wishlist_reason TEXT,
    purchase_intent TEXT,
    purchase_barrier TEXT,
    purchase_hesitation TEXT,
    purchase_postponement_reason TEXT,
    uncertainty_type TEXT,
    information_needed TEXT,
    decision_stage TEXT,
    behaviour_after_interest TEXT,
    comparison_behaviour TEXT,
    external_search_behaviour TEXT,
    competitor_behaviour TEXT,
    purchase_outcome TEXT,
    product_category TEXT,
    product_type TEXT,
    price_sensitivity TEXT,
    fit_concern INTEGER DEFAULT 0,
    size_concern INTEGER DEFAULT 0,
    quality_concern INTEGER DEFAULT 0,
    material_concern INTEGER DEFAULT 0,
    styling_concern INTEGER DEFAULT 0,
    occasion_concern INTEGER DEFAULT 0,
    review_concern INTEGER DEFAULT 0,
    social_validation_need INTEGER DEFAULT 0,
    trust_concern INTEGER DEFAULT 0,
    availability_concern INTEGER DEFAULT 0,
    return_exchange_concern INTEGER DEFAULT 0,
    user_segment_signals TEXT,
    evidence_strength TEXT,
    evidence_span TEXT,
    evidence_type TEXT,
    inferred_user_need TEXT,
    inference_confidence REAL,
    cluster_id INTEGER,
    processing_timestamp TEXT NOT NULL,
    FOREIGN KEY(feedback_id) REFERENCES raw_feedback(feedback_id),
    FOREIGN KEY(cluster_id) REFERENCES problem_clusters(cluster_id)
);
"""

CREATE_PROBLEM_CLUSTERS_TABLE = """
CREATE TABLE IF NOT EXISTS problem_clusters (
    cluster_id INTEGER PRIMARY KEY AUTOINCREMENT,
    level_1_category TEXT NOT NULL,
    level_2_category TEXT NOT NULL,
    cluster_label TEXT NOT NULL,
    cluster_description TEXT,
    cluster_size INTEGER DEFAULT 0,
    representative_quote TEXT,
    sub_themes_json TEXT,
    confidence_score REAL,
    created_at TEXT NOT NULL
);
"""

CREATE_CLUSTER_METRICS_TABLE = """
CREATE TABLE IF NOT EXISTS cluster_metrics (
    cluster_id INTEGER PRIMARY KEY,
    frequency_count INTEGER NOT NULL,
    prevalence_pct REAL NOT NULL,
    source_breadth INTEGER NOT NULL,
    explicit_rate REAL NOT NULL,
    inferred_rate REAL NOT NULL,
    purchase_linkage_score REAL NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(cluster_id) REFERENCES problem_clusters(cluster_id)
);
"""

CREATE_OPPORTUNITY_SCORES_TABLE = """
CREATE TABLE IF NOT EXISTS opportunity_scores (
    cluster_id INTEGER PRIMARY KEY,
    opportunity_score REAL NOT NULL,
    priority_rank INTEGER NOT NULL,
    sizing_revenue_opportunity REAL NOT NULL,
    fit_revenue_opportunity REAL NOT NULL,
    decision_acceleration_potential REAL NOT NULL,
    strategic_rationale TEXT NOT NULL,
    non_monetary_recommendation TEXT NOT NULL,
    confidence_score REAL NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(cluster_id) REFERENCES problem_clusters(cluster_id)
);
"""

CREATE_SHOPPER_SESSIONS_TABLE = """
CREATE TABLE IF NOT EXISTS shopper_sessions (
    session_id INTEGER PRIMARY KEY AUTOINCREMENT,
    administrative_pages INTEGER DEFAULT 0,
    administrative_duration REAL DEFAULT 0.0,
    informational_pages INTEGER DEFAULT 0,
    informational_duration REAL DEFAULT 0.0,
    product_related_pages INTEGER DEFAULT 0,
    product_related_duration REAL DEFAULT 0.0,
    bounce_rate REAL DEFAULT 0.0,
    exit_rate REAL DEFAULT 0.0,
    page_value REAL DEFAULT 0.0,
    special_day REAL DEFAULT 0.0,
    month TEXT,
    operating_systems INTEGER,
    browser INTEGER,
    region INTEGER,
    traffic_type INTEGER,
    visitor_type TEXT,
    weekend INTEGER DEFAULT 0,
    revenue_converted INTEGER DEFAULT 0
);
"""

CREATE_WEB_SEARCH_RESULTS_TABLE = """
CREATE TABLE IF NOT EXISTS web_search_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query TEXT NOT NULL,
    research_category TEXT NOT NULL,
    search_timestamp TEXT NOT NULL,
    rank INTEGER,
    title TEXT,
    url TEXT,
    snippet TEXT,
    domain TEXT,
    CONSTRAINT unique_url_query UNIQUE(url, query)
);
"""

CREATE_WEB_SEARCH_REQUESTS_TABLE = """
CREATE TABLE IF NOT EXISTS web_search_requests (
    request_id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    query TEXT NOT NULL,
    category TEXT,
    request_number INTEGER,
    status TEXT NOT NULL,
    result_count INTEGER DEFAULT 0,
    error TEXT,
    estimated_usage REAL DEFAULT 0.0
);
"""

CREATE_YOUTUBE_VIDEOS_TABLE = """
CREATE TABLE IF NOT EXISTS youtube_videos (
    video_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    channel_id TEXT,
    channel_name TEXT,
    published_at TEXT,
    url TEXT,
    search_query TEXT,
    research_category TEXT,
    relevance_score INTEGER DEFAULT 0,
    discovery_count INTEGER DEFAULT 1,
    collection_timestamp TEXT NOT NULL
);
"""

CREATE_YOUTUBE_COMMENTS_TABLE = """
CREATE TABLE IF NOT EXISTS youtube_comments (
    comment_id TEXT PRIMARY KEY,
    video_id TEXT NOT NULL,
    parent_comment_id TEXT,
    text TEXT NOT NULL,
    published_at TEXT,
    updated_at TEXT,
    like_count INTEGER DEFAULT 0,
    reply_count INTEGER DEFAULT 0,
    author_name TEXT,
    url TEXT,
    search_query TEXT,
    research_category TEXT,
    collection_timestamp TEXT NOT NULL,
    FOREIGN KEY(video_id) REFERENCES youtube_videos(video_id)
);
"""

CREATE_YOUTUBE_API_REQUESTS_TABLE = """
CREATE TABLE IF NOT EXISTS youtube_api_requests (
    request_id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    query_or_video_id TEXT NOT NULL,
    status TEXT NOT NULL,
    estimated_quota_units INTEGER DEFAULT 1,
    result_count INTEGER DEFAULT 0,
    error TEXT
);
"""

CREATE_WISHLIST_RECORDS_TABLE = """
CREATE TABLE IF NOT EXISTS wishlist_records (
    wishlist_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL,
    product_id TEXT NOT NULL,
    added_date TEXT NOT NULL,
    product_category TEXT,
    price_at_addition REAL,
    current_price REAL,
    price_alert_set INTEGER DEFAULT 0,
    purchased INTEGER DEFAULT 0,
    purchase_date TEXT,
    days_in_wishlist INTEGER DEFAULT 0,
    price_drop_pct REAL DEFAULT 0.0,
    converted_within_30_days INTEGER DEFAULT 0,
    is_synthetic INTEGER DEFAULT 1,
    source_dataset TEXT DEFAULT 'electricsheepafrica/africa-synth-retail-and-ecommerce-wishlist-and-favorites-data-nigeria'
);
"""

CREATE_ECOMMERCE_EVENTS_TABLE = """
CREATE TABLE IF NOT EXISTS ecommerce_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    event_time TEXT NOT NULL,
    product_id TEXT,
    user_id TEXT,
    user_session TEXT,
    price REAL,
    category TEXT,
    brand TEXT,
    source_dataset TEXT DEFAULT 'REES46/eCommerce-Behavior-Data'
);
"""

CREATE_RESEARCH_QUERIES_TABLE = """
CREATE TABLE IF NOT EXISTS research_queries (
    query_id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_text TEXT NOT NULL,
    response_json TEXT NOT NULL,
    query_timestamp TEXT NOT NULL
);
"""

CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_raw_source ON raw_feedback(source);",
    "CREATE INDEX IF NOT EXISTS idx_raw_category ON raw_feedback(category);",
    "CREATE INDEX IF NOT EXISTS idx_proc_relevance ON processed_feedback(relevance_score);",
    "CREATE INDEX IF NOT EXISTS idx_proc_barrier ON processed_feedback(purchase_barrier);",
    "CREATE INDEX IF NOT EXISTS idx_proc_category ON processed_feedback(product_category);",
    "CREATE INDEX IF NOT EXISTS idx_proc_cluster ON processed_feedback(cluster_id);",
    "CREATE INDEX IF NOT EXISTS idx_proc_intent_tier ON processed_feedback(intent_tier);",
    "CREATE INDEX IF NOT EXISTS idx_proc_save_reason ON processed_feedback(save_reason_category);",
    "CREATE INDEX IF NOT EXISTS idx_proc_state ON processed_feedback(wishlist_state);",
    "CREATE INDEX IF NOT EXISTS idx_proc_trigger_cat ON processed_feedback(trigger_category);",
    "CREATE INDEX IF NOT EXISTS idx_proc_info_cat ON processed_feedback(information_needed_category);",
    "CREATE INDEX IF NOT EXISTS idx_cluster_l1 ON problem_clusters(level_1_category);",
    "CREATE INDEX IF NOT EXISTS idx_cluster_l2 ON problem_clusters(level_2_category);",
    "CREATE INDEX IF NOT EXISTS idx_sessions_visitor ON shopper_sessions(visitor_type);",
    "CREATE INDEX IF NOT EXISTS idx_sessions_revenue ON shopper_sessions(revenue_converted);",
    "CREATE INDEX IF NOT EXISTS idx_wishlist_cat ON wishlist_records(product_category);",
    "CREATE INDEX IF NOT EXISTS idx_wishlist_purchased ON wishlist_records(purchased);",
    "CREATE INDEX IF NOT EXISTS idx_wishlist_30d ON wishlist_records(converted_within_30_days);",
    "CREATE INDEX IF NOT EXISTS idx_wishlist_alert ON wishlist_records(price_alert_set);",
    "CREATE INDEX IF NOT EXISTS idx_ecom_type ON ecommerce_events(event_type);",
    "CREATE INDEX IF NOT EXISTS idx_ecom_session ON ecommerce_events(user_session);",
    "CREATE INDEX IF NOT EXISTS idx_web_query ON web_search_results(query);",
    "CREATE INDEX IF NOT EXISTS idx_web_domain ON web_search_results(domain);",
    "CREATE INDEX IF NOT EXISTS idx_web_url ON web_search_results(url);",
    "CREATE INDEX IF NOT EXISTS idx_yt_video_cat ON youtube_videos(research_category);",
    "CREATE INDEX IF NOT EXISTS idx_yt_comment_video ON youtube_comments(video_id);"
]


def init_db(conn: Optional[sqlite3.Connection] = None, db_path: str = "data/discovery_engine.db") -> None:
    """Initialize all SQLite tables, indexes, and handle schema migrations."""
    should_close = False
    if conn is None:
        db_dir = os.path.dirname(db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        conn = sqlite3.connect(db_path)
        should_close = True

    try:
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")
        cursor.execute(CREATE_RAW_FEEDBACK_TABLE)
        cursor.execute(CREATE_PROCESSED_FEEDBACK_TABLE)
        cursor.execute(CREATE_PROBLEM_CLUSTERS_TABLE)
        cursor.execute(CREATE_CLUSTER_METRICS_TABLE)
        cursor.execute(CREATE_OPPORTUNITY_SCORES_TABLE)
        cursor.execute(CREATE_SHOPPER_SESSIONS_TABLE)
        cursor.execute(CREATE_WISHLIST_RECORDS_TABLE)
        cursor.execute(CREATE_ECOMMERCE_EVENTS_TABLE)
        cursor.execute(CREATE_WEB_SEARCH_RESULTS_TABLE)
        cursor.execute(CREATE_WEB_SEARCH_REQUESTS_TABLE)
        cursor.execute(CREATE_YOUTUBE_VIDEOS_TABLE)
        cursor.execute(CREATE_YOUTUBE_COMMENTS_TABLE)
        cursor.execute(CREATE_YOUTUBE_API_REQUESTS_TABLE)
        cursor.execute(CREATE_RESEARCH_QUERIES_TABLE)
        
        # Schema migration check for new wishlist journey columns
        cursor.execute("PRAGMA table_info(processed_feedback);")
        existing_cols = {col[1] for col in cursor.fetchall()}
        
        new_columns = {
            "cleaned_text": "TEXT",
            "intent_tier": "TEXT",
            "save_reason_category": "TEXT",
            "wishlist_state": "TEXT",
            "trigger_condition": "TEXT",
            "trigger_type": "TEXT",
            "trigger_category": "TEXT",
            "information_needed_category": "TEXT",
            "current_workaround": "TEXT",
            "option_preservation_signal": "INTEGER DEFAULT 0",
            "scarcity_reaction": "TEXT",
            "reactivation_trigger": "TEXT"
        }
        for col_name, col_type in new_columns.items():
            if col_name not in existing_cols:
                cursor.execute(f"ALTER TABLE processed_feedback ADD COLUMN {col_name} {col_type};")

        # Schema migration for web_search_requests
        cursor.execute("PRAGMA table_info(web_search_requests);")
        req_cols = {col[1] for col in cursor.fetchall()}
        new_req_cols = {
            "request_number": "INTEGER",
            "error": "TEXT",
            "estimated_usage": "REAL DEFAULT 0.0"
        }
        for col_name, col_type in new_req_cols.items():
            if col_name not in req_cols:
                cursor.execute(f"ALTER TABLE web_search_requests ADD COLUMN {col_name} {col_type};")

        for idx_sql in CREATE_INDEXES:
            cursor.execute(idx_sql)

        conn.commit()
    finally:
        if should_close:
            conn.close()
