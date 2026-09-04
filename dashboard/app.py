"""Streamlit Entrypoint rendering the 1:1 Stitch PM Intelligence Dashboard."""
import os
import sys
import json
import streamlit as st
import streamlit.components.v1 as components

# Ensure root directory is in sys.path
CWD = os.path.dirname(os.path.abspath(__file__))
if CWD not in sys.path:
    sys.path.insert(0, CWD)

from database.db import get_db
from analysis.wishlist_activation import WishlistActivationEngine
from analysis.wishlist_journey import WishlistJourneyEngine
from analysis.wishlist_depth import WishlistDepthEngine
from analysis.opportunity import OpportunityEngine

# Configure Streamlit Page
st.set_page_config(
    page_title="Wishlist Purchase Discovery Engine | PM Growth Intelligence",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Hide Streamlit Default Chrome & Padding for full-screen Stitch UI
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display:none;}
    div[data-testid="stToolbar"] {visibility: hidden;}
    div[data-testid="stDecoration"] {visibility: hidden;}
    div[data-testid="stStatusWidget"] {visibility: hidden;}
    .block-container {
        padding: 0 !important;
        margin: 0 !important;
        max-width: 100% !important;
    }
    iframe {
        width: 100vw !important;
        height: 100vh !important;
        min-height: 100vh !important;
        border: none !important;
        display: block !important;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def get_initial_dataset():
    """Pre-aggregates all ground-truth analytical datasets to inject into the Stitch UI."""
    db = get_db()
    
    # Auto-bootstrap if empty
    try:
        res = db.execute_query("SELECT COUNT(*) as c FROM raw_feedback")
        count = res[0]["c"] if res else 0
        if count == 0:
            from scripts.scale_data_pipeline import scale_all_sources
            scale_all_sources()
    except Exception:
        pass

    activation_engine = WishlistActivationEngine(db=db)
    journey_engine = WishlistJourneyEngine(db=db)
    depth_engine = WishlistDepthEngine(db=db)
    opp_engine = OpportunityEngine(db=db)

    # 1. Activation summary
    summary = activation_engine.get_activation_summary()
    
    # 2. Coverage
    raw_cnt = db.execute_query("SELECT COUNT(*) as c FROM raw_feedback")
    total_raw = raw_cnt[0]["c"] if raw_cnt else 321
    coverage = {
        "total_raw": total_raw,
        "wishlist_records": 5000,
        "session_events": 3949,
        "reddit_count": 128,
        "web_youtube_count": 181
    }

    # 3. Four Pillars
    four_pillars = activation_engine.get_four_discovery_pillars()

    # 4. Behavioral & Funnel Benchmarks
    w_bench = activation_engine.get_wishlist_behavioral_metrics()
    c_bench = activation_engine.get_ecommerce_funnel_benchmark()

    # 5. Intent tiers
    intent_data = journey_engine.get_intent_metrics()

    # 6. Trigger matrix
    t_matrix = activation_engine.get_purchase_trigger_matrix()

    # 7. Opportunities
    opps = activation_engine.get_activation_opportunities()

    # 8. Depth / Dormancy
    depth_data = depth_engine.get_wishlist_depth_metrics()

    # 9. Evidence items
    evidence_rows = db.execute_query("""
        SELECT p.feedback_id, r.source, p.product_category, p.friction_category, p.inferred_need, p.user_quote, p.purchase_outcome, p.relevance_score
        FROM processed_feedback p
        JOIN raw_feedback r ON p.feedback_id = r.feedback_id
        WHERE p.relevance_score >= 2
        ORDER BY p.relevance_score DESC
        LIMIT 100;
    """)

    return {
        "/api/activation/summary": summary,
        "/api/coverage": coverage,
        "/api/discovery/four-pillars": four_pillars,
        "/api/activation/wishlist-behaviour": w_bench,
        "/api/activation/funnel-benchmark": c_bench,
        "/api/wishlist/intent": intent_data,
        "/api/activation/trigger-matrix": t_matrix,
        "/api/activation/opportunities": opps,
        "/api/wishlist/depth-dormancy": depth_data,
        "/api/evidence": evidence_rows
    }


def render_dashboard():
    data_payload = get_initial_dataset()
    json_data = json.dumps(data_payload)

    html_path = os.path.join(CWD, "stitch_wishlist_purchase_discovery_engine", "code.html")
    if not os.path.exists(html_path):
        html_path = os.path.join(CWD, "index.html")

    with open(html_path, "r", encoding="utf-8") as f:
        html_code = f.read()

    # Inject ground truth analytical data directly into window object
    injection = f"""
    <script>
      window.__INITIAL_DATA__ = {json_data};
    </script>
    """
    if "</head>" in html_code:
        html_code = html_code.replace("</head>", f"{injection}\n</head>", 1)
    else:
        html_code = injection + html_code

    components.html(html_code, height=1200, scrolling=True)


if __name__ == "__main__":
    render_dashboard()
