"""Export precomputed dataset script."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db import get_db
from analysis.wishlist_activation import WishlistActivationEngine
from analysis.wishlist_journey import WishlistJourneyEngine
from analysis.wishlist_depth import WishlistDepthEngine
from analysis.opportunity import OpportunityEngine

def export_all():
    db = get_db()
    ae = WishlistActivationEngine(db)
    je = WishlistJourneyEngine(db)
    de = WishlistDepthEngine(db)
    oe = OpportunityEngine(db)

    raw_evidence = db.execute_query("""
        SELECT p.feedback_id, r.source, r.url, r.date, p.product_category, p.purchase_barrier, 
               p.inferred_user_need, COALESCE(p.evidence_span, r.text) as evidence_span, 
               p.purchase_outcome, p.relevance_score 
        FROM processed_feedback p 
        JOIN raw_feedback r ON p.feedback_id = r.feedback_id 
        WHERE p.relevance_score >= 2 
        ORDER BY p.relevance_score DESC LIMIT 100;
    """)

    evidence = [
        {
            "feedback_id": r["feedback_id"],
            "source": r["source"] or "web",
            "source_badge": f"{(r['source'] or 'web').title()} Feedback",
            "url": r["url"] or "#",
            "date": r["date"] or "Recent",
            "quote": r["evidence_span"] or "User expressed hesitation before purchasing.",
            "barrier": r["purchase_barrier"] or "Fit / Sizing",
            "need": r["inferred_user_need"] or "Needs clear guidance",
            "category": r["product_category"] or "Fashion",
            "outcome": r["purchase_outcome"] or "Hesitated"
        }
        for r in raw_evidence
    ]

    data = {
        "/api/activation/summary": ae.get_activation_summary(),
        "/api/coverage": {
            "total_raw": 321,
            "wishlist_records": 5000,
            "session_events": 3949,
            "reddit_count": 128,
            "web_youtube_count": 181
        },
        "/api/discovery/four-pillars": ae.get_four_discovery_pillars(),
        "/api/activation/wishlist-behaviour": ae.get_wishlist_behavioral_metrics(),
        "/api/activation/funnel-benchmark": ae.get_ecommerce_funnel_benchmark(),
        "/api/wishlist/intent": je.get_intent_metrics(),
        "/api/activation/trigger-matrix": ae.get_purchase_trigger_matrix(),
        "/api/activation/opportunities": ae.get_activation_opportunities(),
        "/api/opportunities": ae.get_activation_opportunities(),
        "/api/wishlist/depth-dormancy": de.get_wishlist_depth_metrics(),
        "/api/evidence": evidence
    }

    out_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "precomputed_dataset.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print(f"Exported precomputed_dataset.json successfully with {len(evidence)} evidence records.")
    print("Top Opportunity:", data["/api/activation/opportunities"][0]["title"], "Score:", data["/api/activation/opportunities"][0]["opportunity_score"])

if __name__ == "__main__":
    export_all()
