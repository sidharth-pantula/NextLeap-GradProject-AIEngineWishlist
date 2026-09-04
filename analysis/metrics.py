"""Deterministic mathematical quantification engine for problem clusters."""
import json
import logging
from typing import Any, Dict, List, Optional
from database.db import get_db, Database

logger = logging.getLogger(__name__)


class MetricsEngine:
    """Computes pure SQL and Python mathematical metrics for problem clusters."""

    def __init__(self, db: Optional[Database] = None):
        self.db = db or get_db()

    def get_total_relevant_count(self) -> int:
        """Returns the total number of feedback records with relevance_score >= 2."""
        query = "SELECT COUNT(*) as count FROM processed_feedback WHERE relevance_score >= 2"
        res = self.db.execute_query(query)
        return res[0]["count"] if res else 0

    def compute_cluster_metrics(self, cluster_id: int) -> Dict[str, Any]:
        """Compute frequency, prevalence, source breadth, explicit/inferred rates, and purchase linkage."""
        total_relevant = self.get_total_relevant_count()

        # Query all processed feedback records for this cluster joined with raw_feedback
        query = """
            SELECT 
                p.feedback_id,
                p.evidence_type,
                p.purchase_barrier,
                p.purchase_hesitation,
                p.purchase_postponement_reason,
                p.purchase_outcome,
                p.uncertainty_type,
                p.product_category,
                p.price_sensitivity,
                p.decision_stage,
                r.source
            FROM processed_feedback p
            LEFT JOIN raw_feedback r ON p.feedback_id = r.feedback_id
            WHERE p.cluster_id = ?
        """
        records = self.db.execute_query(query, (cluster_id,))
        frequency = len(records)

        if frequency == 0:
            return {
                "cluster_id": cluster_id,
                "frequency": 0,
                "prevalence_pct": 0.0,
                "source_breadth": 0,
                "explicit_evidence_rate": 0.0,
                "inferred_evidence_rate": 0.0,
                "purchase_linkage_score": 0.0,
                "segment_breakdown_json": json.dumps({})
            }

        # 1. Prevalence %
        prevalence_pct = round((frequency / total_relevant * 100.0), 2) if total_relevant > 0 else 0.0

        # 2. Source Breadth
        sources = {r["source"] for r in records if r.get("source")}
        source_breadth = len(sources)

        # 3. Explicit vs Inferred Evidence Rate
        explicit_count = sum(
            1 for r in records 
            if r.get("evidence_type") and str(r.get("evidence_type")).lower() == "explicit"
        )
        explicit_rate = round((explicit_count / frequency * 100.0), 2)
        inferred_rate = round(100.0 - explicit_rate, 2)

        # 4. Purchase Linkage Score
        # Proportion of records indicating clear hesitation, friction, postponement, abandonment, or barriers
        def is_purchase_linked(r: Dict[str, Any]) -> bool:
            outcome = str(r.get("purchase_outcome") or "").lower()
            if outcome in ["postponed", "abandoned", "hesitated", "drop", "dropped", "uncertain"]:
                return True
            if r.get("purchase_barrier") or r.get("purchase_hesitation") or r.get("purchase_postponement_reason"):
                return True
            if r.get("uncertainty_type"):
                return True
            return False

        linked_count = sum(1 for r in records if is_purchase_linked(r))
        purchase_linkage_score = round((linked_count / frequency * 100.0), 2)

        # 5. Segment Breakdown
        category_counts: Dict[str, int] = {}
        price_counts: Dict[str, int] = {}
        stage_counts: Dict[str, int] = {}

        for r in records:
            cat = r.get("product_category") or "Unknown"
            category_counts[cat] = category_counts.get(cat, 0) + 1

            price = r.get("price_sensitivity") or "Unknown"
            price_counts[price] = price_counts.get(price, 0) + 1

            stage = r.get("decision_stage") or "Unknown"
            stage_counts[stage] = stage_counts.get(stage, 0) + 1

        segment_breakdown = {
            "by_category": category_counts,
            "by_price_sensitivity": price_counts,
            "by_decision_stage": stage_counts,
            "sources": list(sources)
        }

        return {
            "cluster_id": cluster_id,
            "frequency": frequency,
            "prevalence_pct": prevalence_pct,
            "source_breadth": source_breadth,
            "explicit_evidence_rate": explicit_rate,
            "inferred_evidence_rate": inferred_rate,
            "purchase_linkage_score": purchase_linkage_score,
            "segment_breakdown_json": json.dumps(segment_breakdown)
        }

    def compute_and_store_all_metrics(self) -> List[Dict[str, Any]]:
        """Calculate metrics for all existing problem clusters and save to database."""
        clusters = self.db.execute_query("SELECT cluster_id, cluster_label FROM problem_clusters")
        results = []

        for cl in clusters:
            cid = cl["cluster_id"]
            metrics = self.compute_cluster_metrics(cid)

            # Insert or replace in cluster_metrics
            self.db.execute_write("""
                DELETE FROM cluster_metrics WHERE cluster_id = ?
            """, (cid,))

            self.db.execute_write("""
                INSERT INTO cluster_metrics (
                    cluster_id, frequency, prevalence_pct, source_breadth,
                    explicit_evidence_rate, inferred_evidence_rate,
                    purchase_linkage_score, segment_breakdown_json, calculation_timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                cid,
                metrics["frequency"],
                metrics["prevalence_pct"],
                metrics["source_breadth"],
                metrics["explicit_evidence_rate"],
                metrics["inferred_evidence_rate"],
                metrics["purchase_linkage_score"],
                metrics["segment_breakdown_json"]
            ))

            # Also update cluster_size in problem_clusters
            self.db.execute_write("""
                UPDATE problem_clusters 
                SET cluster_size = ? 
                WHERE cluster_id = ?
            """, (metrics["frequency"], cid))

            metrics["cluster_label"] = cl.get("cluster_label")
            results.append(metrics)

        logger.info(f"Successfully computed metrics for {len(results)} problem clusters.")
        return results
