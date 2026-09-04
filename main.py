import argparse
import json
import os
import sys
from dotenv import load_dotenv

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from database.db import get_db
from database.schema import init_db
from collectors.youtube_collector import YouTubeCollector
from collectors.youtube_quota_manager import YouTubeQuotaManager
from collectors.web_collector import WebCollector
from collectors.serper_budget_manager import SerperBudgetManager
from collectors.hf_dataset_loader import HFDatasetLoader

load_dotenv()


def show_status():
    """Print current system status, database record counts, and API budget summaries."""
    db = get_db()
    counts = db.get_summary_counts()
    yt_manager = YouTubeQuotaManager(db=db)
    yt_status = yt_manager.get_quota_summary()
    serper_manager = SerperBudgetManager(db=db)
    serper_status = serper_manager.get_budget_summary()

    print("\n" + "=" * 60)
    print("AI WISHLIST DISCOVERY ENGINE — SYSTEM STATUS")
    print("=" * 60)
    print("DATABASE COUNTS:")
    print(f"  * Raw Feedback (Staging)   : {counts['raw_feedback']}")
    print(f"  * Processed Feedback       : {counts['processed_feedback']}")
    print(f"  * Relevant Feedback        : {counts['relevant_feedback']}")
    print(f"  * Shopper Sessions         : {counts['shopper_sessions']}")

    print("\nYOUTUBE QUOTA STATUS:")
    print(f"  * Quota Spent / Daily Limit: {yt_status['estimated_quota_used']} / {yt_status['daily_quota_limit']} units")
    print(f"  * Remaining Quota          : {yt_status['remaining_quota']} units")
    print(f"  * Discovered Videos        : {yt_status['total_videos_collected']}")
    print(f"  * Extracted Comments       : {yt_status['total_comments_collected']}")

    print("\nSERPER FREE-CREDIT BUDGET STATUS:")
    print(f"  * Budget Mode              : {serper_status['budget_mode']}")
    print(f"  * Requests Made / Ceiling  : {serper_status['total_network_requests_made']} / {serper_status['max_requests_ceiling']}")
    print(f"  * Remaining Allowance      : {serper_status['remaining_request_allowance']} requests")
    print(f"  * Search Results Stored    : {serper_status['total_search_results_stored']}")
    print(f"  * Unique URLs Discovered   : {serper_status['unique_urls_collected']}")
    print("=" * 60 + "\n")


def run_youtube_test(limit: int = 10):
    """Execute strictly the 10-query YouTube discovery test."""
    print("\n" + "=" * 60)
    print(f"STARTING CONTROLLED YOUTUBE DISCOVERY TEST (Limit: {limit} queries)")
    print("=" * 60)
    collector = YouTubeCollector()
    summary = collector.run_initial_test(limit=limit)

    print("\nYOUTUBE TEST EXECUTION REPORT:")
    print(f"  * Estimated Quota Used     : {summary['estimated_quota_used']} units")
    print(f"  * Remaining Quota          : {summary['remaining_quota']} units")
    print(f"  * Videos Collected         : {summary['total_videos_collected']}")
    print(f"  * Comments Collected       : {summary['total_comments_collected']}")

    print("\nQUERIES EXECUTED:")
    for item in summary.get("test_executed_queries", []):
        print(f"  [OK] Category: {item['category']:<28} | Query: {item['query']:<35} | Comments: {item['comments_extracted']}")
        if item.get("sample_comment") and item["sample_comment"] != "No comments":
            clean_sample = item['sample_comment'].replace('\n', ' ')
            print(f"       Sample: \"{clean_sample}...\"")

    if summary.get("test_errors"):
        print("\nERRORS ENCOUNTERED:")
        for err in summary["test_errors"]:
            print(f"  [ERR] Query: {err['query']} | Error: {err['error']}")

    print("\n[STOPPED] YouTube test run completed. Further calls halted.")
    print("=" * 60 + "\n")


def run_serper_test(limit: int = 10):
    """Execute strictly the 10-query Serper web search test."""
    print("\n" + "=" * 60)
    print(f"STARTING CONTROLLED SERPER WEB SEARCH TEST (Strict Limit: {limit} requests)")
    print("=" * 60)
    collector = WebCollector()
    summary = collector.run_initial_test(limit=limit)

    print("\nSERPER TEST EXECUTION REPORT:")
    print(f"  * Budget Mode              : {summary['budget_mode']}")
    print(f"  * Requests Made / Ceiling  : {summary['total_network_requests_made']} / {summary['max_requests_ceiling']}")
    print(f"  * Remaining Request Cap    : {summary['remaining_request_allowance']}")
    print(f"  * Total Results Stored     : {summary['total_search_results_stored']}")
    print(f"  * Unique URLs Collected    : {summary['unique_urls_collected']}")

    print("\nQUERIES EXECUTED:")
    for item in summary.get("test_executed_queries", []):
        print(f"  [OK] Category: {item['category']:<25} | Query: {item['query'][:40]:<40} | Results: {item['results_count']}")
        if item.get("sample_title"):
            print(f"       Top Domain: {item['sample_domain']:<20} | Title: {item['sample_title'][:60]}")

    if summary.get("test_errors"):
        print("\nERRORS ENCOUNTERED:")
        for err in summary["test_errors"]:
            print(f"  [ERR] Query: {err['query']} | Error: {err['error']}")

    print("\n[STOPPED] Serper test run completed. Further calls halted.")
    print("=" * 60 + "\n")


def run_feedback_processing(limit: int = 200):
    """Execute Phase 3 cleaning, deduplication, and relevance grading on raw_feedback."""
    from processing.relevance import RelevanceClassifier
    print("\n" + "=" * 60)
    print(f"STARTING PHASE 3: CLEANING, DEDUPLICATION & RELEVANCE GRADING (Batch: {limit})")
    print("=" * 60)

    db = get_db()
    classifier = RelevanceClassifier(db=db)
    processed_count = classifier.process_raw_feedback_batch(limit=limit)

    # Fetch relevance score distribution
    distribution = db.execute_query("""
        SELECT relevance_score, COUNT(*) as count 
        FROM processed_feedback 
        GROUP BY relevance_score 
        ORDER BY relevance_score DESC;
    """)

    print(f"\nPROCESSED {processed_count} RAW FEEDBACK RECORDS.")
    print("\nRELEVANCE SCORE DISTRIBUTION (0-3 Scale):")
    score_labels = {
        3: "Highly Relevant (Wishlist / Hesitation / Comparison / Intent)",
        2: "Relevant (Sizing / Quality / Friction / Returns / Price)",
        1: "Peripheral (General fashion aesthetics / looks)",
        0: "Irrelevant (Spam / Bot notice / Non-shopping)"
    }
    for row in distribution:
        s = row["relevance_score"]
        cnt = row["count"]
        lbl = score_labels.get(s, f"Score {s}")
        print(f"  * [{s}] {lbl:<60} : {cnt} records")

    print("\n" + "=" * 60 + "\n")


def run_insights_extraction(limit: int = 100):
    """Execute Phase 4 structured Groq LLM extraction on relevant feedback records."""
    from ai.extraction import ExtractionPipeline
    print("\n" + "=" * 60)
    print(f"STARTING PHASE 4: STRUCTURED LLM INFORMATION EXTRACTION (Batch: {limit})")
    print("=" * 60)

    db = get_db()
    pipeline = ExtractionPipeline(db=db)
    extracted_count = pipeline.process_relevant_feedback_batch(limit=limit, min_relevance=2)

    # Fetch breakdown of extracted purchase barriers
    barriers = db.execute_query("""
        SELECT purchase_barrier, COUNT(*) as count 
        FROM processed_feedback 
        WHERE purchase_barrier IS NOT NULL AND purchase_barrier != 'none'
        GROUP BY purchase_barrier 
        ORDER BY count DESC;
    """)

    sample_insights = db.execute_query("""
        SELECT feedback_id, purchase_barrier, uncertainty_type, evidence_span, inferred_user_need 
        FROM processed_feedback 
        WHERE purchase_barrier IS NOT NULL AND purchase_barrier != 'none'
        LIMIT 5;
    """)

    print(f"\nEXTRACTED STRUCTURED INSIGHTS FOR {extracted_count} RELEVANT RECORDS.")
    print("\nPURCHASE BARRIERS DISCOVERED:")
    for b in barriers:
        print(f"  * {b['purchase_barrier']:<30} : {b['count']} occurrences")

    if sample_insights:
        print("\nSAMPLE STRUCTURED INSIGHTS & INFERRED NEEDS:")
        for idx, row in enumerate(sample_insights, 1):
            print(f"  [{idx}] ID: {row['feedback_id']} | Barrier: {row['purchase_barrier']} | Uncertainty: {row['uncertainty_type']}")
            if row.get("evidence_span"):
                print(f"      Evidence Span : \"{row['evidence_span'][:100]}\"")
            if row.get("inferred_user_need"):
                print(f"      Inferred Need : {row['inferred_user_need']}")

    print("\n" + "=" * 60 + "\n")


def run_phase5_clustering():
    """Execute Phase 5 embeddings and unsupervised semantic clustering."""
    from ai.embeddings import EmbeddingPipeline
    from ai.clustering import ClusteringEngine
    
    print("\n" + "=" * 60)
    print("STARTING PHASE 5: EMBEDDINGS & SEMANTIC CLUSTERING")
    print("=" * 60)
    
    db = get_db()
    
    # 1. Generate Embeddings
    print("\n[Step 1] Generating BGE Embeddings...")
    embedder = EmbeddingPipeline(db=db)
    embedded_count = embedder.process_unembedded_feedback(batch_size=100)
    print(f"-> Generated and stored {embedded_count} composite vector chunks in ChromaDB.")
    
    # 2. Run Clustering
    print("\n[Step 2] Running HDBSCAN Clustering & Taxonomy Generation...")
    clusterer = ClusteringEngine(db=db)
    result = clusterer.run_clustering()
    
    if result["status"] == "success":
        print(f"\nDiscovered {len(result['clusters'])} problem clusters.")
        for c in result["clusters"]:
            lbl = str(c['label']) if c.get('label') else "Unknown"
            print(f"  * [{c['cluster_id'][:8]}] {lbl:<40} (Size: {c['size']})")
    else:
        print(f"\nClustering Status: {result['status']} ({result.get('message')})")

    print("\n" + "=" * 60 + "\n")


def run_phase6_quantification():
    """Execute Phase 6 deterministic quantification, segmentation & opportunity ranking."""
    from analysis.opportunity import OpportunityEngine
    from analysis.segmentation import SegmentationEngine

    print("\n" + "=" * 60)
    print("STARTING PHASE 6: DETERMINISTIC METRICS & OPPORTUNITY ENGINE")
    print("=" * 60)

    db = get_db()
    opp_engine = OpportunityEngine(db=db)
    seg_engine = SegmentationEngine(db=db)

    print("\n[Step 1] Computing Deterministic Metrics & Opportunity Scores...")
    opps = opp_engine.prioritize_and_store_opportunities()

    print(f"\nPrioritized {len(opps)} Opportunity Areas:")
    for op in opps:
        print(f"\n  #{op['priority_rank']} [{op['cluster_label']}]")
        print(f"     Opportunity Score : {op['opportunity_score']:.1f} / 100")
        print(f"     Prevalence        : {op['prevalence_pct']:.1f}% ({op['frequency']} observations)")
        print(f"     Purchase Linkage  : {op['purchase_linkage_score']:.1f}%")
        print(f"     Source Breadth    : {op['source_breadth']} channels")
        print(f"     Rationale         : {op['rationale']}")

    print("\n[Step 2] Category Segmentation Breakdown:")
    cats = seg_engine.get_category_breakdown()
    for c in cats:
        print(f"  * {c['category']:<20}: {c['feedback_count']} items (Fit/Size concerns: {c['fit_size_concerns']}, Quality concerns: {c['quality_concerns']})")

    print("\n" + "=" * 60 + "\n")


def run_phase7_research(query: str):
    """Execute Phase 7 Hybrid RAG PM research assistant."""
    from rag.research_engine import ResearchEngine

    print("\n" + "=" * 60)
    print("STARTING PHASE 7: HYBRID RAG PM RESEARCH ASSISTANT")
    print(f"Query: \"{query}\"")
    print("=" * 60 + "\n")

    engine = ResearchEngine()
    result = engine.answer_query(query)

    print(result["response"])
    print("\n" + "=" * 60 + "\n")


def run_phase8_dashboard(host: str = "127.0.0.1", port: int = 8000):
    """Launch Phase 8 Stitch Frontend & FastAPI Dashboard Server."""
    import uvicorn
    print("\n" + "=" * 60)
    print("STARTING PHASE 8: WISHLIST PURCHASE DISCOVERY DASHBOARD")
    print(f"URL: http://{host}:{port}")
    print("=" * 60 + "\n")
    uvicorn.run("dashboard.api:app", host=host, port=port, reload=False)


def main():
    parser = argparse.ArgumentParser(description="AI Wishlist Discovery Engine CLI")
    parser.add_argument("--init-db", action="store_true", help="Initialize SQLite database schema")
    parser.add_argument("--status", action="store_true", help="Show system status and quota summaries")
    parser.add_argument("--test-youtube", action="store_true", help="Run 10-query YouTube discovery test")
    parser.add_argument("--test-serper", action="store_true", help="Run 10-search Serper web discovery test")
    parser.add_argument("--process-feedback", action="store_true", help="Run Phase 3 cleaning and relevance grading")
    parser.add_argument("--extract-insights", action="store_true", help="Run Phase 4 structured Groq LLM extraction")
    parser.add_argument("--cluster-problems", action="store_true", help="Run Phase 5 Embeddings & HDBSCAN Clustering")
    parser.add_argument("--quantify", action="store_true", help="Run Phase 6 Metrics & Opportunity Prioritization")
    parser.add_argument("--research", type=str, help="Ask the Phase 7 Hybrid RAG engine a research question")
    parser.add_argument("--dashboard", action="store_true", help="Launch Phase 8 Stitch Frontend Dashboard server")
    args = parser.parse_args()

    if args.init_db:
        init_db()
        print("Database initialized successfully.")
    elif args.test_youtube:
        run_youtube_test(limit=10)
    elif args.test_serper:
        run_serper_test(limit=10)
    elif args.process_feedback:
        run_feedback_processing(limit=500)
    elif args.extract_insights:
        run_insights_extraction(limit=500)
    elif args.cluster_problems:
        run_phase5_clustering()
    elif args.quantify:
        run_phase6_quantification()
    elif args.research:
        run_phase7_research(args.research)
    elif args.dashboard:
        run_phase8_dashboard()
    elif args.status:
        show_status()
    else:
        show_status()



if __name__ == "__main__":
    main()

