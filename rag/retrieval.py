"""Hybrid Dual Retriever combining deterministic SQL summaries with dense vector evidence."""
import logging
from typing import Any, Dict, List, Optional
from database.db import get_db, Database
from vector.chroma_store import get_vector_store, ChromaStore
from ai.embeddings import EmbeddingPipeline

logger = logging.getLogger(__name__)


class HybridRetriever:
    """Retrieves both deterministic SQL aggregate metrics and semantic verbatim quotes."""

    def __init__(
        self,
        db: Optional[Database] = None,
        chroma: Optional[ChromaStore] = None,
        embedder: Optional[EmbeddingPipeline] = None
    ):
        self.db = db or get_db()
        self.chroma = chroma or get_vector_store()
        self.embedder = embedder or EmbeddingPipeline(db=self.db)

    def retrieve_sql_analytics(self, query: str = "", filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Runs deterministic SQL aggregations to build quantitative ground truth."""
        # 1. Total and relevant counts
        total_raw = self.db.execute_query("SELECT COUNT(*) as count FROM raw_feedback")
        total_raw_count = total_raw[0]["count"] if total_raw else 0

        total_rel = self.db.execute_query("SELECT COUNT(*) as count FROM processed_feedback WHERE relevance_score >= 2")
        total_rel_count = total_rel[0]["count"] if total_rel else 0

        # 2. Top Opportunity Rankings & Clusters
        opp_query = """
            SELECT 
                o.priority_rank,
                o.opportunity_score,
                c.cluster_label,
                c.level_1_category,
                m.frequency,
                m.prevalence_pct,
                m.purchase_linkage_score,
                m.source_breadth
            FROM opportunity_scores o
            JOIN problem_clusters c ON o.cluster_id = c.cluster_id
            JOIN cluster_metrics m ON o.cluster_id = m.cluster_id
            ORDER BY o.priority_rank ASC
            LIMIT 5
        """
        top_opportunities = self.db.execute_query(opp_query)

        # 3. Category Breakdown
        cat_query = """
            SELECT 
                COALESCE(product_category, 'General Apparel') as category,
                COUNT(*) as count,
                SUM(CASE WHEN fit_concern = 1 OR size_concern = 1 THEN 1 ELSE 0 END) as fit_size_concerns,
                SUM(CASE WHEN quality_concern = 1 OR material_concern = 1 THEN 1 ELSE 0 END) as quality_concerns
            FROM processed_feedback
            WHERE relevance_score >= 2
            GROUP BY category
            ORDER BY count DESC
        """
        category_breakdown = self.db.execute_query(cat_query)

        # 4. Purchase Outcome Distribution
        outcome_query = """
            SELECT 
                COALESCE(purchase_outcome, 'Unspecified / Hesitated') as outcome,
                COUNT(*) as count
            FROM processed_feedback
            WHERE relevance_score >= 2
            GROUP BY outcome
            ORDER BY count DESC
        """
        outcomes = self.db.execute_query(outcome_query)

        # 5. Wishlist Decision Journey Analytics
        from analysis.wishlist_journey import WishlistJourneyEngine
        journey_eng = WishlistJourneyEngine(db=self.db)
        intent_data = journey_eng.get_intent_metrics()
        save_reasons = journey_eng.get_why_users_save()
        gaps_data = journey_eng.get_information_gaps_and_workarounds()
        preservation_data = journey_eng.get_option_preservation_and_scarcity()

        # 6. Format into clean text block for LLM prompt
        lines = [
            f"- Total Ingested Conversations/Records: {total_raw_count}",
            f"- Total Verified Relevant VoC Records (Score >= 2): {total_rel_count}",
            f"- Strict Purchase Intent: {intent_data['strict_purchase_intent_pct']}% ({intent_data['strict_purchase_intent_count']} items)",
            f"- Broader Commercial Intent: {intent_data['broader_commercial_intent_pct']}% ({intent_data['broader_commercial_intent_count']} items - {intent_data['sanity_check_message']})",
            f"- Exploration & Bookmarking: {intent_data['exploration_bookmarking_pct']}% ({intent_data['exploration_bookmarking_count']} items)",
            f"- Conditional Intent: {intent_data['conditional_intent_pct']}% ({intent_data['conditional_intent_count']} items)",
            "",
            "Why Users Save to Wishlist (Decomposition):"
        ]

        for sr in save_reasons[:5]:
            lines.append(f"  * {sr['label']}: {sr['percentage']}% ({sr['count']} items)")

        lines.append("\nTop Information Gaps & External Workarounds:")
        for gap in gaps_data["information_gaps"][:4]:
            lines.append(f"  * Missing Info [{gap['info_cat']}]: {gap['count']} mentions")
        for wa in gaps_data["external_workarounds"][:3]:
            lines.append(f"  * Workaround [{wa['workaround'].replace('_', ' ').title()}]: {wa['count']} users")

        lines.append("\nTop Discovered Problem Clusters (Prioritized):")
        if top_opportunities:
            for opp in top_opportunities:
                lines.append(
                    f"  * #{opp['priority_rank']} [{opp['cluster_label']}] (Category: {opp['level_1_category']}) | "
                    f"Opp Score: {opp['opportunity_score']:.1f}/100 | Prevalence: {opp['prevalence_pct']:.1f}% ({opp['frequency']} items) | "
                    f"Purchase Linkage: {opp['purchase_linkage_score']:.1f}% | Source Breadth: {opp['source_breadth']} channels"
                )
        else:
            lines.append("  (No problem clusters quantified yet)")

        lines.append("\nCategory Distribution:")
        for cat in category_breakdown:
            lines.append(f"  * {cat['category']}: {cat['count']} items (Fit/Size concerns: {cat['fit_size_concerns']}, Quality concerns: {cat['quality_concerns']})")

        lines.append("\nPurchase Outcomes:")
        for out in outcomes:
            lines.append(f"  * {out['outcome']}: {out['count']} items")

        summary_text = "\n".join(lines)

        return {
            "summary_text": summary_text,
            "total_raw": total_raw_count,
            "total_relevant": total_rel_count,
            "intent_data": intent_data,
            "save_reasons": save_reasons,
            "top_opportunities": top_opportunities,
            "category_breakdown": category_breakdown,
            "outcomes": outcomes
        }

    def retrieve_verbatim_evidence(
        self,
        query: str,
        top_k: int = 5,
        where_filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Dense vector search across ChromaDB + SQLite metadata lookup for verbatim quotes."""
        # 1. Embed query with BGE search prefix
        query_vectors = self.embedder.generate_embeddings([query], is_query=True)
        if not query_vectors:
            return []

        # 2. Chroma search
        chroma_hits = self.chroma.query_feedback(
            query_embedding=query_vectors[0],
            top_k=top_k,
            where_filter=where_filter
        )

        evidence_items = []
        for hit in chroma_hits:
            f_id = hit["id"]
            
            # Fetch complete row from database
            rows = self.db.execute_query("""
                SELECT 
                    p.feedback_id,
                    p.evidence_span,
                    p.inferred_user_need,
                    p.purchase_barrier,
                    p.uncertainty_type,
                    p.product_category,
                    p.price_sensitivity,
                    r.source,
                    r.url,
                    r.date,
                    r.title
                FROM processed_feedback p
                LEFT JOIN raw_feedback r ON p.feedback_id = r.feedback_id
                WHERE p.feedback_id = ?
            """, (f_id,))

            if rows:
                row = rows[0]
                evidence_items.append({
                    "feedback_id": f_id,
                    "evidence_span": row.get("evidence_span") or hit.get("document", ""),
                    "inferred_user_need": row.get("inferred_user_need") or "",
                    "purchase_barrier": row.get("purchase_barrier") or "",
                    "uncertainty_type": row.get("uncertainty_type") or "",
                    "product_category": row.get("product_category") or "Fashion",
                    "source": row.get("source") or "Unknown",
                    "url": row.get("url") or "",
                    "date": row.get("date") or "",
                    "distance": hit.get("distance", 0.0)
                })

        return evidence_items

    def retrieve(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        """Combines SQL aggregate metrics and semantic quote search into a unified context bundle."""
        sql_data = self.retrieve_sql_analytics(query)
        evidence_list = self.retrieve_verbatim_evidence(query, top_k=top_k)

        # Format evidence quotes into text
        quote_lines = []
        if evidence_list:
            for idx, ev in enumerate(evidence_list, start=1):
                quote_lines.append(
                    f"{idx}. \"{ev['evidence_span']}\"\n"
                    f"   [Source: {ev['source']} | Category: {ev['product_category']} | Barrier: {ev['purchase_barrier']} | Need: {ev['inferred_user_need']}]"
                )
        else:
            quote_lines.append("(No direct verbatim evidence retrieved for this specific query)")

        evidence_text = "\n\n".join(quote_lines)

        return {
            "query": query,
            "sql_summary": sql_data["summary_text"],
            "evidence_quotes": evidence_text,
            "raw_sql_data": sql_data,
            "raw_evidence_list": evidence_list
        }
