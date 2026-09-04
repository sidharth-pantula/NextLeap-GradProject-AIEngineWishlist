import sqlite3
import json
import os

db_path = 'data/discovery_engine.db'
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("=========================================")
print("1. DATA SOURCES & RAW COUNTS")
print("=========================================")
sources_raw = cursor.execute("""
    SELECT source, source_type, COUNT(*) as cnt 
    FROM raw_feedback 
    GROUP BY source, source_type 
    ORDER BY cnt DESC
""").fetchall()
for r in sources_raw:
    print(f"Source: {r['source']} (type: {r['source_type']}) -> {r['cnt']} records")

print("\n--- Additional Specific Source Tables ---")
t_yt_vid = cursor.execute("SELECT COUNT(*) FROM youtube_videos").fetchone()[0]
t_yt_comm = cursor.execute("SELECT COUNT(*) FROM youtube_comments").fetchone()[0]
t_yt_req = cursor.execute("SELECT COUNT(*) FROM youtube_api_requests").fetchone()[0]
t_web_res = cursor.execute("SELECT COUNT(*) FROM web_search_results").fetchone()[0]
t_web_req = cursor.execute("SELECT COUNT(*) FROM web_search_requests").fetchone()[0]
t_wishlist = cursor.execute("SELECT COUNT(*) FROM wishlist_records").fetchone()[0]
t_shopper = cursor.execute("SELECT COUNT(*) FROM shopper_sessions").fetchone()[0]
t_ecom = cursor.execute("SELECT COUNT(*) FROM ecommerce_events").fetchone()[0]

print(f"youtube_videos: {t_yt_vid}")
print(f"youtube_comments: {t_yt_comm}")
print(f"youtube_api_requests: {t_yt_req}")
print(f"web_search_results: {t_web_res}")
print(f"web_search_requests: {t_web_req}")
print(f"wishlist_records (HF electricsheepafrica): {t_wishlist}")
print(f"shopper_sessions (HF online_shoppers_intention): {t_shopper}")
print(f"ecommerce_events (HF REES46): {t_ecom}")

print("\n=========================================")
print("2. PROCESSED FEEDBACK BREAKDOWN")
print("=========================================")
sources_proc = cursor.execute("""
    SELECT r.source, 
           COUNT(p.feedback_id) as total_proc,
           SUM(CASE WHEN p.relevance_score >= 2 THEN 1 ELSE 0 END) as rel_gte_2,
           SUM(CASE WHEN p.relevance_score = 3 THEN 1 ELSE 0 END) as rel_3_high,
           SUM(CASE WHEN p.relevance_score = 2 THEN 1 ELSE 0 END) as rel_2_med,
           SUM(CASE WHEN p.relevance_score = 1 THEN 1 ELSE 0 END) as rel_1_low,
           SUM(CASE WHEN p.relevance_score = 0 THEN 1 ELSE 0 END) as rel_0_irr,
           AVG(p.relevance_score) as avg_rel
    FROM processed_feedback p
    JOIN raw_feedback r ON p.feedback_id = r.feedback_id
    GROUP BY r.source 
    ORDER BY total_proc DESC
""").fetchall()
for r in sources_proc:
    print(f"Source: {r['source']} -> Total Processed: {r['total_proc']} | Rel>=2 (Retained): {r['rel_gte_2']} | Rel=3: {r['rel_3_high']} | Rel=2: {r['rel_2_med']} | Rel=1: {r['rel_1_low']} | Rel=0: {r['rel_0_irr']} | Avg Rel: {r['avg_rel']:.2f}")

tot_proc = cursor.execute("SELECT COUNT(*) FROM processed_feedback").fetchone()[0]
tot_rel_gte_2 = cursor.execute("SELECT COUNT(*) FROM processed_feedback WHERE relevance_score >= 2").fetchone()[0]
print(f"\nTotal Processed Feedback: {tot_proc}")
print(f"Total Relevant (Relevance >= 2 used for downstream clusters/RAG): {tot_rel_gte_2}")

print("\n=========================================")
print("3. CHROMA DB VECTOR STORE")
print("=========================================")
try:
    import chromadb
    client = chromadb.PersistentClient(path="chroma_db")
    colls = client.list_collections()
    for c in colls:
        print(f"Collection: {c.name} -> Count: {c.count()} embeddings")
        sample = c.peek(limit=1)
        print(f"   Metadata keys: {list(sample['metadatas'][0].keys()) if sample['metadatas'] else 'None'}")
except Exception as e:
    print(f"Chroma error: {e}")

print("\n=========================================")
print("4. CLUSTERS & THEMES")
print("=========================================")
clusters = cursor.execute("""
    SELECT c.cluster_id, c.cluster_label, c.level_1_category, c.level_2_category, c.cluster_size,
           m.frequency, m.prevalence_pct, m.purchase_linkage_score, m.source_breadth,
           o.priority_rank, o.opportunity_score, o.rationale
    FROM problem_clusters c
    LEFT JOIN cluster_metrics m ON c.cluster_id = m.cluster_id
    LEFT JOIN opportunity_scores o ON c.cluster_id = o.cluster_id
    ORDER BY o.priority_rank ASC
""").fetchall()

print(f"Total Problem Clusters: {len(clusters)}")
for c in clusters:
    print(f"\nCluster #{c['cluster_id']} [Rank {c['priority_rank'] or 'N/A'}]")
    print(f"  Label: {c['cluster_label']}")
    print(f"  L1 Category: {c['level_1_category']} | L2: {c['level_2_category']}")
    print(f"  Size: {c['cluster_size']} | Freq: {c['frequency']} | Prev: {c['prevalence_pct']}% | Linkage: {c['purchase_linkage_score']} | Breadth: {c['source_breadth']}")
    print(f"  Opp Score: {c['opportunity_score']}")
    print(f"  Rationale: {c['rationale']}")

print("\n=========================================")
print("5. OPPORTUNITY SCORES TABLE")
print("=========================================")
opps = cursor.execute("""
    SELECT o.opportunity_id, o.cluster_id, c.cluster_label, o.opportunity_score, o.priority_rank, o.rationale
    FROM opportunity_scores o
    JOIN problem_clusters c ON o.cluster_id = c.cluster_id
    ORDER BY o.priority_rank ASC
""").fetchall()
print(f"Total Ranked Opportunity Areas in DB: {len(opps)}")
for o in opps:
    print(f"Rank {o['priority_rank']}: Cluster {o['cluster_id']} - '{o['cluster_label']}' (Score: {o['opportunity_score']:.2f})")

conn.close()
