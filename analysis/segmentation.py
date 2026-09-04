"""Multi-dimensional segmentation engine for cross-sectional behavioral analysis."""
import logging
from typing import Any, Dict, List, Optional
from database.db import get_db, Database

logger = logging.getLogger(__name__)


class SegmentationEngine:
    """Provides segment-level behavioral slicing and correlation with shopper session data."""

    def __init__(self, db: Optional[Database] = None):
        self.db = db or get_db()

    def get_category_breakdown(self) -> List[Dict[str, Any]]:
        """Break down relevant feedback and barriers by product category."""
        query = """
            SELECT 
                COALESCE(p.product_category, 'General Apparel') as category,
                COUNT(*) as feedback_count,
                SUM(CASE WHEN p.fit_concern = 1 OR p.size_concern = 1 THEN 1 ELSE 0 END) as fit_size_concerns,
                SUM(CASE WHEN p.quality_concern = 1 OR p.material_concern = 1 THEN 1 ELSE 0 END) as quality_concerns,
                SUM(CASE WHEN p.price_sensitivity IN ('High', 'Budget', 'price_sensitive') THEN 1 ELSE 0 END) as price_sensitive_count,
                SUM(CASE WHEN p.return_exchange_concern = 1 THEN 1 ELSE 0 END) as return_concerns
            FROM processed_feedback p
            WHERE p.relevance_score >= 2
            GROUP BY category
            ORDER BY feedback_count DESC
        """
        return self.db.execute_query(query)

    def get_price_tier_breakdown(self) -> List[Dict[str, Any]]:
        """Break down feedback patterns across price sensitivity segments."""
        query = """
            SELECT 
                COALESCE(p.price_sensitivity, 'Medium / Unspecified') as price_tier,
                COUNT(*) as count,
                AVG(CASE WHEN p.purchase_outcome IN ('postponed', 'abandoned', 'hesitated') THEN 1.0 ELSE 0.0 END) * 100 as hesitation_rate,
                SUM(CASE WHEN p.wishlist_reason LIKE '%sale%' OR p.wishlist_reason LIKE '%price drop%' THEN 1 ELSE 0 END) as waiting_for_sale_count
            FROM processed_feedback p
            WHERE p.relevance_score >= 2
            GROUP BY price_tier
            ORDER BY count DESC
        """
        return self.db.execute_query(query)

    def get_decision_stage_funnel(self) -> List[Dict[str, Any]]:
        """Maps feedback counts across the shopping decision stages."""
        query = """
            SELECT 
                COALESCE(p.decision_stage, 'Consideration') as stage,
                COUNT(*) as count,
                COUNT(DISTINCT p.cluster_id) as active_clusters
            FROM processed_feedback p
            WHERE p.relevance_score >= 2
            GROUP BY stage
            ORDER BY count DESC
        """
        return self.db.execute_query(query)

    def get_shopper_session_insights(self) -> Dict[str, Any]:
        """Aggregate behavioral session metrics from the shopper_sessions dataset."""
        query = """
            SELECT 
                COUNT(*) as total_sessions,
                AVG(informational_duration) as avg_info_duration,
                AVG(product_related_duration) as avg_product_duration,
                AVG(bounce_rate) as avg_bounce_rate,
                AVG(exit_rate) as avg_exit_rate,
                SUM(CASE WHEN revenue_converted = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as conversion_rate,
                AVG(CASE WHEN visitor_type = 'Returning_Visitor' AND revenue_converted = 0 THEN 1.0 ELSE 0.0 END) * 100 as returning_abandonment_rate
            FROM shopper_sessions
        """
        rows = self.db.execute_query(query)
        if rows and rows[0]["total_sessions"] > 0:
            row = rows[0]
            return {
                "total_sessions": row["total_sessions"],
                "conversion_rate_pct": round(row["conversion_rate"] or 0.0, 2),
                "non_conversion_rate_pct": round(100.0 - (row["conversion_rate"] or 0.0), 2),
                "avg_info_duration_sec": round(row["avg_info_duration"] or 0.0, 1),
                "avg_product_duration_sec": round(row["avg_product_duration"] or 0.0, 1),
                "avg_exit_rate": round(row["avg_exit_rate"] or 0.0, 4),
                "returning_abandonment_rate_pct": round(row["returning_abandonment_rate"] or 0.0, 2)
            }
        return {
            "total_sessions": 0,
            "conversion_rate_pct": 0.0,
            "non_conversion_rate_pct": 100.0,
            "avg_info_duration_sec": 0.0,
            "avg_product_duration_sec": 0.0,
            "avg_exit_rate": 0.0,
            "returning_abandonment_rate_pct": 0.0
        }
