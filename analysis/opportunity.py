"""Deterministic Opportunity Prioritization Engine with Wishlist Decision Journey Framework."""
import logging
from typing import Any, Dict, List, Optional
from database.db import get_db, Database
from analysis.metrics import MetricsEngine

logger = logging.getLogger(__name__)


class OpportunityEngine:
    """Computes multi-dimensional opportunity prioritization scores (0-100) per the PM Framework."""

    def __init__(
        self,
        db: Optional[Database] = None,
        w_prevalence: float = 0.25,
        w_linkage: float = 0.25,
        w_breadth: float = 0.20,
        w_explicit: float = 0.15,
        w_confidence: float = 0.15
    ):
        self.db = db or get_db()
        self.metrics_engine = MetricsEngine(db=self.db)
        self.w_prevalence = w_prevalence
        self.w_linkage = w_linkage
        self.w_breadth = w_breadth
        self.w_explicit = w_explicit
        self.w_confidence = w_confidence

        total_w = w_prevalence + w_linkage + w_breadth + w_explicit + w_confidence
        if total_w > 0:
            self.w_prevalence /= total_w
            self.w_linkage /= total_w
            self.w_breadth /= total_w
            self.w_explicit /= total_w
            self.w_confidence /= total_w

    def calculate_opportunity_score(
        self,
        prevalence_pct: float,
        linkage_score: float,
        source_breadth: int,
        explicit_rate: float,
        confidence_score: float = 85.0
    ) -> float:
        """Calculate composite 0-100 opportunity score."""
        norm_breadth = min(source_breadth / 4.0, 1.0) * 100.0
        score = (
            self.w_prevalence * prevalence_pct +
            self.w_linkage * linkage_score +
            self.w_breadth * norm_breadth +
            self.w_explicit * explicit_rate +
            self.w_confidence * confidence_score
        )
        return round(min(max(score, 0.0), 100.0), 2)

    def generate_structured_opportunity(
        self,
        cluster_id: int,
        cluster_label: str,
        frequency: int,
        prevalence_pct: float,
        linkage_score: float,
        source_breadth: int
    ) -> Dict[str, Any]:
        """Build the standardized 8-part opportunity structure."""
        # Find dominant workarounds and triggers associated with this cluster
        workaround_row = self.db.execute_query("""
            SELECT current_workaround, COUNT(*) as c 
            FROM processed_feedback 
            WHERE cluster_id = ? AND current_workaround IS NOT NULL
            GROUP BY current_workaround ORDER BY c DESC LIMIT 1
        """, (cluster_id,))
        top_workaround = workaround_row[0]["current_workaround"].replace("_", " ").title() if workaround_row else "Reading Customer Reviews & Reddit"

        trigger_row = self.db.execute_query("""
            SELECT trigger_condition, COUNT(*) as c 
            FROM processed_feedback 
            WHERE cluster_id = ? AND trigger_condition IS NOT NULL
            GROUP BY trigger_condition ORDER BY c DESC LIMIT 1
        """, (cluster_id,))
        top_trigger = trigger_row[0]["trigger_condition"] if trigger_row else "Garment measurement transparency & fit try-on proof"

        relevance_str = "High" if linkage_score >= 80.0 else "Moderate" if linkage_score >= 50.0 else "Low"

        # Behaviour & Impact description
        label_lower = cluster_label.lower()
        if "fit" in label_lower or "size" in label_lower or "sizing" in label_lower:
            observed_behaviour = "Users save products to wishlist but delay checkout because they cannot verify sizing or waist-to-hip measurements."
            potential_opportunity = "Reduce fit uncertainty before checkout via structured garment dimensions, user try-on photos, and size guidance."
            why_it_matters = "Fit uncertainty accounts for the majority of postponed wishlist items. Eliminating size ambiguity moves active consideration directly into checkout without requiring discounts."
        elif "quality" in label_lower or "value" in label_lower:
            observed_behaviour = "Users hesitate due to skepticism over fabric durability, sheer materials, and true color representation."
            potential_opportunity = "Provide verified fabric composition, daylight unedited customer photos, and wash-shrinkage guidance."
            why_it_matters = "Quality reassurance converts saved items that users genuinely like but fear regretting after unboxing."
        else:
            observed_behaviour = "Users bookmark items during exploration and compare against alternative brands across marketplaces."
            potential_opportunity = "Enhance product decision support, transparent attribute comparison, and price trajectory visibility to retain shoppers."
            why_it_matters = "Brings external research into the native experience, accelerating conversion before purchase urgency fades."

        rationale = f"Prevalence: {prevalence_pct}% ({frequency} items) | Purchase Linkage: {linkage_score}% | Sources: {source_breadth} channels. Non-monetary intervention: {potential_opportunity}"

        return {
            "cluster_id": cluster_id,
            "problem": cluster_label,
            "observed_behaviour": observed_behaviour,
            "evidence_frequency": f"{frequency} observations ({prevalence_pct}%)",
            "purchase_relevance": relevance_str,
            "potential_trigger": top_trigger,
            "current_workaround": top_workaround,
            "potential_opportunity": potential_opportunity,
            "why_this_matters": why_it_matters,
            "strategic_rationale": rationale,
            "rationale": rationale
        }

    def prioritize_and_store_opportunities(self) -> List[Dict[str, Any]]:
        """Compute opportunity scores, rank them, and persist to SQLite."""
        cluster_metrics_list = self.metrics_engine.compute_and_store_all_metrics()

        scored_clusters = []
        for m in cluster_metrics_list:
            cid = m["cluster_id"]
            if m["frequency"] == 0:
                continue

            cl_meta = self.db.execute_query(
                "SELECT cluster_label, confidence_score FROM problem_clusters WHERE cluster_id = ?",
                (cid,)
            )
            label = cl_meta[0]["cluster_label"] if cl_meta else f"Cluster {cid}"
            confidence = (cl_meta[0]["confidence_score"] or 0.85) * 100.0 if cl_meta else 85.0

            score = self.calculate_opportunity_score(
                prevalence_pct=m["prevalence_pct"],
                linkage_score=m["purchase_linkage_score"],
                source_breadth=m["source_breadth"],
                explicit_rate=m["explicit_evidence_rate"],
                confidence_score=confidence
            )

            struct_opp = self.generate_structured_opportunity(
                cluster_id=cid,
                cluster_label=label,
                frequency=m["frequency"],
                prevalence_pct=m["prevalence_pct"],
                linkage_score=m["purchase_linkage_score"],
                source_breadth=m["source_breadth"]
            )

            scored_clusters.append({
                "cluster_id": cid,
                "cluster_label": label,
                "opportunity_score": score,
                "frequency": m["frequency"],
                "prevalence_pct": m["prevalence_pct"],
                "purchase_linkage_score": m["purchase_linkage_score"],
                "source_breadth": m["source_breadth"],
                "confidence_score": confidence,
                **struct_opp
            })

        scored_clusters.sort(key=lambda x: x["opportunity_score"], reverse=True)

        self.db.execute_write("DELETE FROM opportunity_scores")

        for rank, item in enumerate(scored_clusters, start=1):
            item["priority_rank"] = rank
            item["rank"] = rank
            item["title"] = item.get("cluster_label") or item.get("problem") or f"Opportunity #{rank}"
            item["rank_label"] = f"#{rank} PRIORITY" if rank == 1 else f"#{rank} OPPORTUNITY"
            item["description"] = item.get("potential_opportunity") or item.get("strategic_rationale")
            item["epistemic_classification"] = "QUALIFIED ROADMAP"
            item["prevalence_pct"] = round(item.get("prevalence_pct", 0.0), 1)
            item["purchase_linkage"] = round(item.get("purchase_linkage_score", 0.0), 1)

            self.db.execute_write("""
                INSERT INTO opportunity_scores (
                    cluster_id, opportunity_score, priority_rank, rationale, calculated_at
                ) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (item["cluster_id"], item["opportunity_score"], rank, item["strategic_rationale"]))

        logger.info(f"Generated priority rankings for {len(scored_clusters)} opportunity areas.")
        return scored_clusters
