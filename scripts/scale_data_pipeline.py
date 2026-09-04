"""End-to-End Multi-Source Scaling Pipeline Script."""
import os
import sys
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db import get_db
from collectors.multi_source_ingestion import ingest_web_and_reddit_results, ingest_huggingface_fashion_feedback
from processing.relevance import RelevanceClassifier
from ai.extraction import ExtractionPipeline
from ai.embeddings import EmbeddingPipeline
from ai.clustering import ClusteringEngine
from analysis.opportunity import OpportunityEngine
from analysis.segmentation import SegmentationEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def scale_all_sources():
    db = get_db()
    print("=" * 60)
    print("SCALING ALL DATA SOURCES: YOUTUBE, REDDIT, WEB, HUGGING FACE")
    print("=" * 60)

    # 1. Ingest Web & Reddit from Discovered Search Results
    print("\n[Step 1] Ingesting Web & Reddit Search Results into raw_feedback...")
    ingest_web_and_reddit_results(db)

    # 2. Ingest Hugging Face Reviews & Shopper Sessions
    print("\n[Step 2] Ingesting Hugging Face E-Commerce & Shopper Datasets...")
    ingest_huggingface_fashion_feedback(db)

    # 3. Run Phase 3 Cleaning & Relevance Scoring on All Raw Records
    print("\n[Step 3] Running Phase 3 Cleaning & Relevance Scoring across All Sources...")
    classifier = RelevanceClassifier(db=db)
    # Process in batches
    total_graded = 0
    while True:
        graded = classifier.process_raw_feedback_batch(limit=100)
        if graded == 0:
            break
        total_graded += graded
    print(f"-> Classified and graded {total_graded} raw feedback records into processed_feedback.")

    # 4. Run Phase 4 Structured Extraction & Need Inference
    print("\n[Step 4] Running Phase 4 Structured Information Extraction...")
    extractor = ExtractionPipeline(db=db)
    extracted_count = extractor.process_relevant_feedback_batch(limit=500, min_relevance=2, use_llm=False)
    print(f"-> Extracted structured signals & quote spans for {extracted_count} records.")

    # 5. Run Phase 5 Local BGE Embeddings & HDBSCAN Semantic Clustering
    print("\n[Step 5] Running Phase 5 Local BGE Embeddings & Clustering...")
    embedder = EmbeddingPipeline(db=db)
    emb_count = embedder.process_unembedded_feedback(batch_size=100)
    print(f"-> Generated {emb_count} composite vector embeddings in ChromaDB.")

    clusterer = ClusteringEngine(db=db)
    clust_res = clusterer.run_clustering()
    if clust_res["status"] == "success":
        print(f"-> Discovered {len(clust_res['clusters'])} multi-source problem clusters:")
        for c in clust_res["clusters"]:
            lbl = str(c.get('label') or 'Unlabeled')
            print(f"   * {lbl:<40} (Size: {c['size']})")
    else:
        print(f"-> Clustering status: {clust_res['status']} ({clust_res.get('message')})")

    # 6. Run Phase 6 Deterministic Quantification & Opportunity Scoring
    print("\n[Step 6] Running Phase 6 Metrics & Opportunity Prioritization...")
    opp_engine = OpportunityEngine(db=db)
    opps = opp_engine.prioritize_and_store_opportunities()
    print(f"-> Generated {len(opps)} prioritized opportunity areas across all sources:")
    for op in opps:
        print(f"   #{op['priority_rank']} [{op['cluster_label']}] - Opp Score: {op['opportunity_score']} | Prevalence: {op['prevalence_pct']}% | Sources: {op['source_breadth']}")

    # 7. Summary Report
    print("\n" + "=" * 60)
    print("MULTI-SOURCE DATA SCALING COMPLETED SUCCESSFULLY!")
    print("=" * 60)
    source_dist = db.execute_query("SELECT source, COUNT(*) as c FROM raw_feedback GROUP BY source ORDER BY c DESC")
    print("\nTotal Ingested by Source:")
    for s in source_dist:
        print(f"  * {s['source'].title():<15}: {s['c']} items")

    rel_dist = db.execute_query("SELECT COUNT(*) as c FROM processed_feedback WHERE relevance_score >= 2")
    print(f"\nTotal Verified Relevant VoC Feedback Items: {rel_dist[0]['c'] if rel_dist else 0}")
    
    session_count = db.execute_query("SELECT COUNT(*) as c FROM shopper_sessions")
    print(f"Total Quantitative Shopper Sessions: {session_count[0]['c'] if session_count else 0}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    scale_all_sources()
