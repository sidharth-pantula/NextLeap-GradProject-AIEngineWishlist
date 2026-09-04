"""AI-Powered Wishlist Activation & Discovery Engine - Streamlit Dashboard.
PM Growth Intelligence, Behavioral Analytics, and Hybrid RAG Assistant.
"""
import os
import sys
import json
import logging
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Ensure project root is in sys.path
CWD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if CWD not in sys.path:
    sys.path.insert(0, CWD)

from database.db import get_db, Database
from analysis.metrics import MetricsEngine
from analysis.segmentation import SegmentationEngine
from analysis.opportunity import OpportunityEngine
from analysis.wishlist_journey import WishlistJourneyEngine
from analysis.wishlist_activation import WishlistActivationEngine
from analysis.wishlist_depth import WishlistDepthEngine
from rag.research_engine import ResearchEngine

# Page Configuration
st.set_page_config(
    page_title="Wishlist Purchase Discovery Engine | PM Growth Intelligence",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .main-header {
        font-size: 1.8rem;
        font-weight: 800;
        color: #0D6EFD;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 0.95rem;
        color: #6C757D;
        margin-bottom: 1.5rem;
    }
    .kpi-card {
        background: #FFFFFF;
        padding: 1.2rem;
        border-radius: 10px;
        border: 1px solid #E9ECEF;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        text-align: center;
    }
    .kpi-val {
        font-size: 2rem;
        font-weight: 800;
        color: #212529;
    }
    .kpi-label {
        font-size: 0.8rem;
        font-weight: 600;
        color: #6C757D;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .quote-box {
        background: #F8F9FA;
        border-left: 4px solid #0D6EFD;
        padding: 1rem;
        margin: 0.8rem 0;
        border-radius: 0 8px 8px 0;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def init_backend():
    """Initializes backend database and checks for auto-bootstrap."""
    db = get_db()
    try:
        res = db.execute_query("SELECT COUNT(*) as c FROM raw_feedback")
        count = res[0]["c"] if res else 0
        if count == 0:
            from scripts.scale_data_pipeline import scale_all_sources
            scale_all_sources()
    except Exception as e:
        st.warning(f"Database bootstrap notice: {e}")
    return db


# Initialize DB and Engines
db = init_backend()
activation_engine = WishlistActivationEngine(db=db)
metrics_engine = MetricsEngine(db=db)
opp_engine = OpportunityEngine(db=db)
journey_engine = WishlistJourneyEngine(db=db)
depth_engine = WishlistDepthEngine(db=db)
rag_engine = ResearchEngine(db=db)

# Sidebar
st.sidebar.image("https://img.icons8.com/isometric/96/shopping-bag.png", width=64)
st.sidebar.title("Discovery Engine")
st.sidebar.caption("Voice-of-Customer & Behavioral Intelligence")

category_filter = st.sidebar.selectbox(
    "🏷️ Product Category",
    ["All", "Apparel", "Footwear", "Outerwear", "Dresses", "Ethnic Wear"],
    index=0
)

channel_filter = st.sidebar.selectbox(
    "📡 Evidence Channel",
    ["All", "reddit", "youtube", "web", "huggingface"],
    index=0
)

st.sidebar.markdown("---")
view_mode = st.sidebar.radio(
    "📌 Navigation View",
    [
        "📊 Executive Overview & KPIs",
        "🎯 Four Pillars of Intent",
        "⚡ Reactivation & Trigger Matrix",
        "🧭 Journey & Funnel Benchmarks",
        "💡 Opportunity Prioritization",
        "🤖 AI PM Research Assistant (RAG)",
        "💬 Verbatim Evidence Log"
    ]
)

st.sidebar.markdown("---")
st.sidebar.caption("🚀 **Dataset Scale**: 5,321 Records (321 Qualitative VoC + 5,000 Behavioral Wishlists)")

# ---------------------------------------------------------
# VIEW 1: EXECUTIVE OVERVIEW & KPIS
# ---------------------------------------------------------
if view_mode == "📊 Executive Overview & KPIs":
    st.markdown('<div class="main-header">Wishlist Activation & Purchase Discovery Engine</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Empirical findings on saving, postponement, validation, and reactivation dynamics across 5,321 multi-channel records.</div>', unsafe_allow_html=True)

    summary = activation_engine.get_activation_summary()
    
    # 4 Top KPI Cards
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">30-Day Conversion Rate</div>
            <div class="kpi-val" style="color: #DC3545;">{summary.get('overall_30d_conversion_pct', 18.4)}%</div>
            <p style="font-size: 0.75rem; color: #6C757D; margin-top: 4px;">Baseline across all wishlisted items</p>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Price-Drop Conversion Lift</div>
            <div class="kpi-val" style="color: #198754;">+{summary.get('price_drop_conversion_lift', 28.6)}%</div>
            <p style="font-size: 0.75rem; color: #6C757D; margin-top: 4px;">Lift when discount alert triggered</p>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Strict Purchase Intent</div>
            <div class="kpi-val" style="color: #0D6EFD;">{summary.get('strict_purchase_intent_pct', 24.1)}%</div>
            <p style="font-size: 0.75rem; color: #6C757D; margin-top: 4px;">Ready-to-buy shoppers</p>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Exploration & Bookmarking</div>
            <div class="kpi-val" style="color: #FD7E14;">{summary.get('exploration_bookmarking_pct', 34.0)}%</div>
            <p style="font-size: 0.75rem; color: #6C757D; margin-top: 4px;">Aspirational / moodboard saves</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    
    # Chart row
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Wishlist Intent Breakdown (Four Pillars)")
        four_pillars = activation_engine.get_four_pillar_breakdown()
        labels = [p["pillar_name"] for p in four_pillars]
        values = [p["pct_of_total_wishlists"] for p in four_pillars]
        colors = ['#0D6EFD', '#FD7E14', '#198754', '#6F42C1']
        
        fig = px.pie(
            names=labels, 
            values=values, 
            color_discrete_sequence=colors,
            hole=0.45
        )
        fig.update_traces(textposition='inside', textinfo='percent+label')
        fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=320)
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.subheader("Conversion Comparison: Price Drop vs No Drop")
        w_bench = activation_engine.get_wishlist_behavioral_metrics()
        df_comp = pd.DataFrame([
            {"Cohort": "With Price Drop (>0%)", "Conversion Rate (%)": w_bench.get("price_drop_conversion_pct", 34.2)},
            {"Cohort": "No Price Drop", "Conversion Rate (%)": w_bench.get("no_price_drop_conversion_pct", 5.6)},
            {"Cohort": "Overall Baseline", "Conversion Rate (%)": w_bench.get("overall_30d_conversion_pct", 18.4)}
        ])
        fig_bar = px.bar(
            df_comp, 
            x="Cohort", 
            y="Conversion Rate (%)", 
            color="Cohort",
            color_discrete_sequence=['#198754', '#DC3545', '#0D6EFD'],
            text="Conversion Rate (%)"
        )
        fig_bar.update_traces(texttemplate='%{text}%', textposition='outside')
        fig_bar.update_layout(showlegend=False, yaxis_range=[0, 42], height=320, margin=dict(t=10, b=10, l=10, r=10))
        st.plotly_chart(fig_bar, use_container_width=True)


# ---------------------------------------------------------
# VIEW 2: FOUR PILLARS OF INTENT
# ---------------------------------------------------------
elif view_mode == "🎯 Four Pillars of Intent":
    st.markdown('<div class="main-header">The Four Pillars of Wishlist Intent</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Categorization of shopper intent when adding fashion items to wishlists.</div>', unsafe_allow_html=True)

    four_pillars = activation_engine.get_four_pillar_breakdown()
    for p in four_pillars:
        with st.expander(f"📌 {p['pillar_name']} — {p['pct_of_total_wishlists']}% of All Wishlists (30d Conv: {p['avg_30d_conversion_pct']}%)", expanded=True):
            st.markdown(f"**Behavioral Definition**: {p['behavioral_definition']}")
            st.markdown(f"**Primary Customer Friction**: `{p['primary_friction']}`")
            st.markdown(f"**Optimal Reactivation Mechanism**: :green[{p['reactivation_mechanism']}]")
            st.info(f"💡 **Key Insight**: {p['epistemic_mandate_insight']}")


# ---------------------------------------------------------
# VIEW 3: REACTIVATION & TRIGGER MATRIX
# ---------------------------------------------------------
elif view_mode == "⚡ Reactivation & Trigger Matrix":
    st.markdown('<div class="main-header">Reactivation & Trigger Matrix</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Prevalence and 30-day conversion lift across targeted trigger mechanisms.</div>', unsafe_allow_html=True)

    t_matrix = activation_engine.get_reactivation_trigger_matrix()
    df_matrix = pd.DataFrame(t_matrix)
    
    col_chart, col_table = st.columns([1.2, 1])
    with col_chart:
        fig = px.scatter(
            df_matrix,
            x="prevalence_pct",
            y="conversion_lift_pct",
            size="prevalence_pct",
            color="friction_category",
            hover_name="trigger_name",
            text="trigger_name",
            labels={
                "prevalence_pct": "Customer Prevalence (% of Shoppers)",
                "conversion_lift_pct": "Conversion Lift (%)",
                "friction_category": "Friction Area"
            },
            title="Trigger Effectiveness vs Shopper Reach"
        )
        fig.update_traces(textposition="top center")
        fig.update_layout(height=450)
        st.plotly_chart(fig, use_container_width=True)

    with col_table:
        st.dataframe(
            df_matrix[["trigger_name", "friction_category", "prevalence_pct", "conversion_lift_pct"]].rename(
                columns={
                    "trigger_name": "Trigger",
                    "friction_category": "Category",
                    "prevalence_pct": "Prevalence (%)",
                    "conversion_lift_pct": "Lift (%)"
                }
            ),
            use_container_width=True,
            height=450
        )


# ---------------------------------------------------------
# VIEW 4: JOURNEY & FUNNEL BENCHMARKS
# ---------------------------------------------------------
elif view_mode == "🧭 Journey & Funnel Benchmarks":
    st.markdown('<div class="main-header">Wishlist Progression & Funnel Benchmarks</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Funnel drop-off points from Product View to Completed Purchase.</div>', unsafe_allow_html=True)

    c_bench = activation_engine.get_commercial_funnel_benchmark()
    stages = c_bench.get("stages", [])
    if stages:
        df_stages = pd.DataFrame(stages)
        fig = go.Figure(go.Funnel(
            y=df_stages["stage_name"],
            x=df_stages["shoppers_reached"],
            textinfo="value+percent initial"
        ))
        fig.update_layout(height=400, margin=dict(t=20, b=20, l=20, r=20))
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Dormancy Distribution")
        depth = depth_engine.get_wishlist_depth_metrics()
        dorm = depth.get("dormancy_distribution", {})
        if dorm:
            df_dorm = pd.DataFrame([{"Dormancy Age": k, "Wishlists": v} for k, v in dorm.items()])
            fig_d = px.bar(df_dorm, x="Dormancy Age", y="Wishlists", color="Dormancy Age")
            st.plotly_chart(fig_d, use_container_width=True)


# ---------------------------------------------------------
# VIEW 5: OPPORTUNITY PRIORITIZATION
# ---------------------------------------------------------
elif view_mode == "💡 Opportunity Prioritization":
    st.markdown('<div class="main-header">PM Opportunity Prioritization Matrix</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Algorithmic prioritization ranking based on prevalence, severity, intent, and source breadth.</div>', unsafe_allow_html=True)

    opps = opp_engine.prioritize_and_store_opportunities()
    if opps:
        for op in opps:
            with st.container():
                st.markdown(f"""
                <div style="background: white; border: 1px solid #E9ECEF; border-radius: 8px; padding: 1.2rem; margin-bottom: 1rem;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <h4 style="margin: 0; color: #0D6EFD;">#{op.get('priority_rank')} {op.get('cluster_label')}</h4>
                        <span style="background: #E7F1FF; color: #0D6EFD; font-weight: bold; padding: 4px 10px; border-radius: 6px;">Score: {op.get('opportunity_score')}</span>
                    </div>
                    <p style="margin: 0.5rem 0; color: #495057;"><strong>Friction & Root Cause:</strong> {op.get('friction_summary')}</p>
                    <p style="margin: 0.5rem 0; color: #198754;"><strong>Recommended Intervention:</strong> {op.get('recommended_intervention')}</p>
                    <div style="display: flex; gap: 20px; font-size: 0.85rem; color: #6C757D; margin-top: 0.8rem;">
                        <span>📊 Prevalence: <strong>{op.get('prevalence_pct')}%</strong></span>
                        <span>🔥 Severity: <strong>{op.get('severity_score')}/5.0</strong></span>
                        <span>🎯 Intent: <strong>{op.get('intent_score')}/5.0</strong></span>
                        <span>🌐 Sources: <strong>{op.get('source_breadth')}</strong></span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("No opportunity records computed yet. Please run data scaling.")


# ---------------------------------------------------------
# VIEW 6: AI RESEARCH ASSISTANT (HYBRID RAG)
# ---------------------------------------------------------
elif view_mode == "🤖 AI PM Research Assistant (RAG)":
    st.markdown('<div class="main-header">AI PM Research Assistant</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Hybrid RAG synthesizing SQL Ground Truth and dense ChromaDB vector search via Groq Llama 3.</div>', unsafe_allow_html=True)

    quick_prompts = [
        "Why do footwear shoppers abandon wishlisted items after 14 days?",
        "What are the top 3 sizing uncertainty frictions across Reddit and YouTube?",
        "How effective are price drop notifications on conversion rate?",
        "What prevents high-intent outerwear shoppers from purchasing?"
    ]
    
    st.markdown("**💡 Quick Prompts:**")
    prompt_cols = st.columns(len(quick_prompts))
    selected_prompt = None
    for i, p in enumerate(quick_prompts):
        if prompt_cols[i].button(p, key=f"quick_{i}"):
            selected_prompt = p

    query = st.text_input("Enter your research question:", value=selected_prompt or "", placeholder="e.g. Why do shoppers hesitate to buy wishlisted dresses?")
    
    if st.button("🚀 Synthesize Answer", type="primary"):
        if query.strip():
            with st.spinner("Decomposing query, aggregating SQLite facts & retrieving semantic evidence..."):
                try:
                    result = rag_engine.research(query)
                    st.markdown("### 📋 Executive Research Synthesis")
                    st.markdown(result.get("answer", "No response received."))
                    
                    if result.get("supporting_quotes"):
                        st.markdown("#### 💬 Verbatim Supporting Evidence")
                        for q in result["supporting_quotes"]:
                            st.markdown(f"""
                            <div class="quote-box">
                                <em>"{q.get('quote') or q.get('text')}"</em><br>
                                <span style="font-size: 0.75rem; color: #6C757D;">Channel: {q.get('source', 'VoC')} | Relevance: {q.get('relevance_score', 'N/A')}</span>
                            </div>
                            """, unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"Error during RAG synthesis: {e}")
        else:
            st.warning("Please enter a research question.")


# ---------------------------------------------------------
# VIEW 7: VERBATIM EVIDENCE LOG
# ---------------------------------------------------------
elif view_mode == "💬 Verbatim Evidence Log":
    st.markdown('<div class="main-header">Verbatim Evidence Log</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Explore direct customer quotes and extracted pain points across Reddit, YouTube, Web & Datasets.</div>', unsafe_allow_html=True)

    where_sql = "relevance_score >= 2"
    params = []
    if category_filter != "All":
        where_sql += " AND LOWER(product_category) = LOWER(?)"
        params.append(category_filter)
    if channel_filter != "All":
        where_sql += " AND LOWER(source) = LOWER(?)"
        params.append(channel_filter)

    query = f"""
    SELECT p.feedback_id, r.source, p.product_category, p.friction_category, p.inferred_need, p.user_quote, p.purchase_outcome, p.relevance_score
    FROM processed_feedback p
    JOIN raw_feedback r ON p.feedback_id = r.feedback_id
    WHERE {where_sql}
    ORDER BY p.relevance_score DESC
    LIMIT 50;
    """
    rows = db.execute_query(query, tuple(params))
    
    if rows:
        st.write(f"Showing **{len(rows)}** verified relevant VoC items:")
        for r in rows:
            st.markdown(f"""
            <div class="quote-box">
                <div style="font-size: 0.95rem; font-weight: 500; color: #212529;">"{r.get('user_quote') or 'No quote span'}"</div>
                <div style="margin-top: 6px; font-size: 0.8rem; color: #6C757D;">
                    🏷️ <strong>Category:</strong> {r.get('product_category', 'General')} | 
                    ⚠️ <strong>Friction:</strong> {r.get('friction_category', 'General')} | 
                    💡 <strong>Inferred Need:</strong> {r.get('inferred_need', 'N/A')} | 
                    📡 <strong>Source:</strong> {r.get('source', 'VoC').title()}
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No records matching selected filters.")
