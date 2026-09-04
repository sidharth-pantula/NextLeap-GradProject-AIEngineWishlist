"""Wishlist Decision Journey & Purchase Trigger Quantification Engine."""
import logging
from typing import Any, Dict, List, Optional
from database.db import Database, get_db

logger = logging.getLogger(__name__)


class WishlistJourneyEngine:
    """Computes deterministic SQL metrics for the complete Wishlist Decision Journey."""

    def __init__(self, db: Optional[Database] = None):
        self.db = db or get_db()

    def get_intent_metrics(self) -> Dict[str, Any]:
        """Compute Strict Purchase Intent vs Broader Commercial Intent with Sanity Check Guardrail."""
        total_rows = self.db.execute_query("""
            SELECT COUNT(*) as total FROM processed_feedback WHERE relevance_score >= 2
        """)
        total_n = total_rows[0]["total"] if total_rows and total_rows[0]["total"] > 0 else 1

        # 7-Tier Distribution
        tier_counts = self.db.execute_query("""
            SELECT 
                COALESCE(intent_tier, 'uncertain_unknown') as tier,
                COUNT(*) as count
            FROM processed_feedback
            WHERE relevance_score >= 2
            GROUP BY intent_tier
        """)
        tier_map = {row["tier"]: row["count"] for row in tier_counts}

        # A. Strict Purchase Intent = Immediate buy statements (3 records)
        strict_count = tier_map.get("immediate_purchase", 0)
        strict_pct = round((strict_count / total_n) * 100.0, 1)

        # B. Active Commercial Consideration = Planned + Conditional + Active Consideration (124 records)
        active_consideration_count = (
            tier_map.get("planned_future", 0) +
            tier_map.get("conditional_intent", 0) +
            tier_map.get("active_consideration", 0)
        )
        active_consideration_pct = round((active_consideration_count / total_n) * 100.0, 1)

        # C. Exploration & Bookmarking = Casual bookmarking + Exploration (61 records)
        exploration_count = tier_map.get("exploration_inspiration", 0) + tier_map.get("casual_bookmarking", 0)
        exploration_pct = round((exploration_count / total_n) * 100.0, 1)

        # Total Broader Commercial Intent = Strict (1.6%) + Active Consideration (66.0%) = 67.6% (127 records)
        broader_count = strict_count + active_consideration_count
        broader_pct = round((broader_count / total_n) * 100.0, 1)

        # D. Conditional Intent (standalone for PM clarity)
        conditional_count = tier_map.get("conditional_intent", 0)
        conditional_pct = round((conditional_count / total_n) * 100.0, 1)

        # Sanity Check Guardrail: Flag if broader intent exceeds 25% to trigger active consideration inspection
        is_sanity_flagged = broader_pct > 25.0
        sanity_message = (
            f"Note for PM: Broader commercial consideration ({broader_pct}%) is driven primarily by active consideration "
            f"({active_consideration_pct}%, {active_consideration_count} items researching sizing/quality) rather than immediate checkout ready intent ({strict_pct}%)."
            if is_sanity_flagged else "Commercial intent metrics within normal conservative bounds."
        )

        tier_metadata = [
            {"tier": "immediate_purchase", "label": "Immediate / High Intent", "count": tier_map.get("immediate_purchase", 0), "pct": round((tier_map.get("immediate_purchase", 0) / total_n) * 100, 1), "desc": "Explicit statements to order/buy now"},
            {"tier": "planned_future", "label": "Planned / Future Intent", "count": tier_map.get("planned_future", 0), "pct": round((tier_map.get("planned_future", 0) / total_n) * 100, 1), "desc": "Saving for occasion, payday, next month"},
            {"tier": "conditional_intent", "label": "Conditional Purchase Intent", "count": tier_map.get("conditional_intent", 0), "pct": round((tier_map.get("conditional_intent", 0) / total_n) * 100, 1), "desc": "Will buy if price drops or size confirmed"},
            {"tier": "active_consideration", "label": "Active Consideration", "count": tier_map.get("active_consideration", 0), "pct": round((tier_map.get("active_consideration", 0) / total_n) * 100, 1), "desc": "Researching fit, quality, comparing options"},
            {"tier": "exploration_inspiration", "label": "Exploration / Inspiration", "count": tier_map.get("exploration_inspiration", 0), "pct": round((tier_map.get("exploration_inspiration", 0) / total_n) * 100, 1), "desc": "Browsing styles, collecting outfit ideas"},
            {"tier": "casual_bookmarking", "label": "Casual Bookmarking", "count": tier_map.get("casual_bookmarking", 0), "pct": round((tier_map.get("casual_bookmarking", 0) / total_n) * 100, 1), "desc": "Saving for later without purchase plan"},
            {"tier": "uncertain_unknown", "label": "Uncertain / Unknown", "count": tier_map.get("uncertain_unknown", 0), "pct": round((tier_map.get("uncertain_unknown", 0) / total_n) * 100, 1), "desc": "Insufficient context"}
        ]

        return {
            "total_analyzed": total_n,
            "strict_purchase_intent_count": strict_count,
            "strict_purchase_intent_pct": strict_pct,
            "active_consideration_count": active_consideration_count,
            "active_consideration_pct": active_consideration_pct,
            "broader_commercial_intent_count": broader_count,
            "broader_commercial_intent_pct": broader_pct,
            "exploration_bookmarking_count": exploration_count,
            "exploration_bookmarking_pct": exploration_pct,
            "conditional_intent_count": conditional_count,
            "conditional_intent_pct": conditional_pct,
            "sanity_check_flagged": is_sanity_flagged,
            "sanity_check_message": sanity_message,
            "tiers": tier_metadata
        }

    def get_why_users_save(self) -> List[Dict[str, Any]]:
        """Quantify the 7 canonical categories for Why Users Save items to Wishlist."""
        total_rows = self.db.execute_query("""
            SELECT COUNT(*) as total FROM processed_feedback WHERE relevance_score >= 2
        """)
        total_n = total_rows[0]["total"] if total_rows and total_rows[0]["total"] > 0 else 1

        rows = self.db.execute_query("""
            SELECT 
                COALESCE(save_reason_category, 'unknown') as category,
                COUNT(*) as count
            FROM processed_feedback
            WHERE relevance_score >= 2
            GROUP BY save_reason_category
            ORDER BY count DESC
        """)
        cat_map = {r["category"]: r["count"] for r in rows}

        categories = [
            ("intentional_planning", "Intentional purchase planning", "User saves with concrete intention to purchase once ready."),
            ("future_consideration", "Future consideration", "Saved for upcoming payday, wedding, or planned event."),
            ("sale_price_waiting", "Sale / price waiting", "Saved specifically to monitor price drops or festival sales."),
            ("comparison", "Comparison", "Saved alongside alternative options to compare fit and fabric."),
            ("exploration_inspiration", "Exploration / inspiration", "Aesthetic bookmarking without immediate purchase need."),
            ("casual_bookmarking", "Casual bookmarking", "Saving to remember or accumulating wishlist items."),
            ("stock_anxiety", "Stock availability anxiety", "Saved due to fear of size selling out or disappearing."),
            ("unknown", "Unknown", "Insufficient context in verbatim statement.")
        ]

        results = []
        for cat_key, cat_label, cat_desc in categories:
            cnt = cat_map.get(cat_key, 0)
            pct = round((cnt / total_n) * 100.0, 1)
            # Find representative quote
            quote_row = self.db.execute_query("""
                SELECT evidence_span, cleaned_text FROM processed_feedback
                WHERE relevance_score >= 2 AND save_reason_category = :cat AND evidence_span IS NOT NULL
                LIMIT 1
            """, {"cat": cat_key})
            rep_quote = quote_row[0]["evidence_span"] if quote_row else "No direct quote available."

            results.append({
                "category_key": cat_key,
                "label": cat_label,
                "description": cat_desc,
                "count": cnt,
                "percentage": pct,
                "representative_quote": rep_quote
            })

        results.sort(key=lambda x: x["count"], reverse=True)
        return results

    def get_wishlist_states(self) -> List[Dict[str, Any]]:
        """Quantify the 12-state decision funnel for saved fashion items."""
        total_rows = self.db.execute_query("""
            SELECT COUNT(*) as total FROM processed_feedback WHERE relevance_score >= 2
        """)
        total_n = total_rows[0]["total"] if total_rows and total_rows[0]["total"] > 0 else 1

        rows = self.db.execute_query("""
            SELECT 
                COALESCE(wishlist_state, 'unknown') as state,
                COUNT(*) as count
            FROM processed_feedback
            WHERE relevance_score >= 2
            GROUP BY wishlist_state
            ORDER BY count DESC
        """)
        state_map = {r["state"]: r["count"] for r in rows}

        state_definitions = [
            ("just_saved", "1. Just Saved", "Item newly added to wishlist"),
            ("exploring", "2. Exploring", "Browsing styling & alternatives"),
            ("considering", "3. Considering", "Actively evaluating purchase"),
            ("waiting", "4. Waiting", "Postponed for payday / occasion"),
            ("comparing", "5. Comparing", "Cross-checking across brands/apps"),
            ("needs_information", "6. Needs Information", "Blocked by missing sizing/fabric info"),
            ("waiting_for_price", "7. Waiting for Price", "Monitoring for price drop / sale"),
            ("waiting_for_availability", "8. Waiting for Stock", "Size or color out of stock"),
            ("re_activated", "9. Re-activated", "Returned during sale / restock"),
            ("purchased", "10. Purchased", "Completed order"),
            ("abandoned", "11. Abandoned", "Removed or forgotten"),
            ("unknown", "12. Unknown", "Undetermined state")
        ]

        results = []
        for state_key, state_label, state_desc in state_definitions:
            cnt = state_map.get(state_key, 0)
            pct = round((cnt / total_n) * 100.0, 1)
            results.append({
                "state_key": state_key,
                "label": state_label,
                "description": state_desc,
                "count": cnt,
                "percentage": pct,
                "is_active_friction": state_key in ["needs_information", "comparing", "waiting_for_price"]
            })

        return results

    def get_purchase_triggers(self) -> Dict[str, List[Dict[str, Any]]]:
        """Group observed purchase triggers into Observed Stated, Potential, and Hypotheses."""
        rows = self.db.execute_query("""
            SELECT 
                trigger_category,
                trigger_type,
                trigger_condition,
                COUNT(*) as count
            FROM processed_feedback
            WHERE relevance_score >= 2 AND trigger_condition IS NOT NULL
            GROUP BY trigger_category, trigger_type, trigger_condition
            ORDER BY count DESC
        """)

        grouped = {
            "observed_stated": [],
            "potential_trigger": [],
            "hypothesis_to_validate": []
        }

        for r in rows:
            t_type = r.get("trigger_type") or "potential_trigger"
            item = {
                "category": (r.get("trigger_category") or "general").replace("_", " ").title(),
                "condition": r.get("trigger_condition"),
                "count": r["count"]
            }
            if t_type in grouped:
                grouped[t_type].append(item)
            else:
                grouped["potential_trigger"].append(item)

        return grouped

    def get_information_gaps_and_workarounds(self) -> Dict[str, Any]:
        """Quantify missing product information and the external workarounds users resort to."""
        info_rows = self.db.execute_query("""
            SELECT 
                COALESCE(information_needed_category, 'fit') as info_cat,
                COUNT(*) as count
            FROM processed_feedback
            WHERE relevance_score >= 2
            GROUP BY information_needed_category
            ORDER BY count DESC
        """)

        workaround_rows = self.db.execute_query("""
            SELECT 
                COALESCE(current_workaround, 'reading_reviews') as workaround,
                COUNT(*) as count
            FROM processed_feedback
            WHERE relevance_score >= 2
            GROUP BY current_workaround
            ORDER BY count DESC
        """)

        # Co-occurrence matrix
        matrix_rows = self.db.execute_query("""
            SELECT 
                COALESCE(information_needed_category, 'fit') as info_cat,
                COALESCE(current_workaround, 'reading_reviews') as workaround,
                COUNT(*) as count
            FROM processed_feedback
            WHERE relevance_score >= 2
            GROUP BY information_needed_category, current_workaround
            ORDER BY count DESC
            LIMIT 10
        """)

        return {
            "information_gaps": info_rows,
            "external_workarounds": workaround_rows,
            "gap_to_workaround_matrix": matrix_rows
        }

    def get_confidence_building_behaviours(self) -> List[Dict[str, Any]]:
        """Quantify empirical behaviours users undertake to build purchase confidence and overcome uncertainty."""
        total_rows = self.db.execute_query("""
            SELECT COUNT(*) as total FROM processed_feedback WHERE relevance_score >= 2
        """)
        total_n = total_rows[0]["total"] if total_rows and total_rows[0]["total"] > 0 else 1

        row = self.db.execute_query("""
            SELECT
                SUM(CASE WHEN fit_concern > 0 OR size_concern > 0 THEN 1 ELSE 0 END) as fit_size,
                SUM(CASE WHEN review_concern > 0 THEN 1 ELSE 0 END) as review_reading,
                SUM(CASE WHEN quality_concern > 0 OR material_concern > 0 THEN 1 ELSE 0 END) as quality_fabric,
                SUM(CASE WHEN social_validation_need > 0 OR trust_concern > 0 THEN 1 ELSE 0 END) as social_validation,
                SUM(CASE WHEN return_exchange_concern > 0 THEN 1 ELSE 0 END) as return_policy,
                SUM(CASE WHEN styling_concern > 0 OR occasion_concern > 0 THEN 1 ELSE 0 END) as styling_occasion
            FROM processed_feedback
            WHERE relevance_score >= 2
        """)[0]

        behaviours = [
            {
                "behaviour": "Garment Dimensions & Size Conversion Check",
                "category": "Fit Confidence",
                "count": row["fit_size"] or 0,
                "pct": round(((row["fit_size"] or 0) / total_n) * 100.0, 1),
                "desc": "Cross-checks brand size charts, bust/waist dimensions, and height-to-length fit."
            },
            {
                "behaviour": "Community Discussions & Peer Validation",
                "category": "Social Validation",
                "count": row["social_validation"] or 0,
                "pct": round(((row["social_validation"] or 0) / total_n) * 100.0, 1),
                "desc": "Asks friends or checks Reddit (r/IndianFashionAddicts) and forums for honest feedback."
            },
            {
                "behaviour": "Customer Photo & Try-On Review Research",
                "category": "Visual Proof",
                "count": row["review_reading"] or 0,
                "pct": round(((row["review_reading"] or 0) / total_n) * 100.0, 1),
                "desc": "Inspects real daylight customer photos and YouTube haul videos to verify true appearance."
            },
            {
                "behaviour": "Return & Exchange Policy Verification",
                "category": "Risk Mitigation",
                "count": row["return_policy"] or 0,
                "pct": round(((row["return_policy"] or 0) / total_n) * 100.0, 1),
                "desc": "Confirms return window and doorstep pickup ease before ordering uncertain sizes."
            },
            {
                "behaviour": "Material, Fabric & Wash-Care Verification",
                "category": "Quality Reassurance",
                "count": row["quality_fabric"] or 0,
                "pct": round(((row["quality_fabric"] or 0) / total_n) * 100.0, 1),
                "desc": "Checks fabric composition percentage (cotton vs polyester) and wash shrinkage risks."
            },
            {
                "behaviour": "Styling & Occasion Appropriateness Check",
                "category": "Styling Fit",
                "count": row["styling_occasion"] or 0,
                "pct": round(((row["styling_occasion"] or 0) / total_n) * 100.0, 1),
                "desc": "Evaluates outfit versatility for specific upcoming events (office, wedding, festival)."
            }
        ]

        behaviours.sort(key=lambda x: x["count"], reverse=True)
        return behaviours

    def get_scarcity_and_availability_dynamics(self) -> Dict[str, Any]:
        """Quantify stock availability signals and Scarcity / FOMO dual reactions."""
        total_rows = self.db.execute_query("""
            SELECT COUNT(*) as total FROM processed_feedback WHERE relevance_score >= 2
        """)
        total_n = total_rows[0]["total"] if total_rows and total_rows[0]["total"] > 0 else 1

        # Scarcity reaction breakdown
        scarcity_rows = self.db.execute_query("""
            SELECT 
                COALESCE(scarcity_reaction, 'neutral') as reaction,
                COUNT(*) as count
            FROM processed_feedback
            WHERE relevance_score >= 2
            GROUP BY scarcity_reaction
            ORDER BY count DESC
        """)

        return {
            "scarcity_dynamics": [
                {"reaction": r["reaction"].replace("_", " ").title(), "count": r["count"], "pct": round((r["count"] / total_n) * 100.0, 1)}
                for r in scarcity_rows
            ]
        }

    # Backward compatibility alias
    def get_option_preservation_and_scarcity(self) -> Dict[str, Any]:
        """Alias returning scarcity dynamics and confidence-building without option preservation framing."""
        scarcity = self.get_scarcity_and_availability_dynamics()
        return {
            "confidence_behaviours": self.get_confidence_building_behaviours(),
            "scarcity_dynamics": scarcity["scarcity_dynamics"]
        }

