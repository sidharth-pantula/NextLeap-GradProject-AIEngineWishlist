"""Unsupervised semantic clustering engine using HDBSCAN and Groq."""
import json
import logging
import uuid
import numpy as np
from typing import List, Dict, Any, Optional

try:
    import hdbscan
    from sklearn.cluster import AgglomerativeClustering
    HAS_CLUSTERING = True
except ImportError:
    HAS_CLUSTERING = False

from vector.chroma_store import get_vector_store
from database.db import get_db, Database
from ai.groq_client import GroqClient

logger = logging.getLogger(__name__)

CLUSTER_LABEL_PROMPT = """You are an expert ecommerce product manager analyzing voice-of-customer data.
I will provide you with a sample of user feedback and their inferred needs belonging to a single semantic cluster.
Your task is to generate a structured taxonomy for this problem cluster.

Return a JSON object strictly matching this schema:
{{
    "cluster_label": "Short 3-5 word label for the problem",
    "level_1_category": "Broad category (e.g., Sizing & Fit, Quality, Price & Value, Information Gap, Trust, UX/UI)",
    "level_2_problem": "Specific sub-problem (e.g., Unclear Size Charts, Translucent Material)",
    "cluster_description": "A 1-2 sentence description of the underlying hesitation block."
}}

Cluster Sample:
{samples}
"""

class ClusteringEngine:
    def __init__(self, db: Optional[Database] = None):
        self.db = db or get_db()
        self.chroma = get_vector_store()
        self.groq = GroqClient()
        
    def run_clustering(self) -> Dict[str, Any]:
        """Fetch embeddings from ChromaDB, cluster them, and label the clusters."""
        if not HAS_CLUSTERING:
            raise ImportError("hdbscan and scikit-learn are required.")
            
        coll = self.chroma.get_collection(self.chroma.FEEDBACK_COLLECTION)
        if not coll:
            return {"status": "error", "message": "Feedback collection not found."}
            
        data = coll.get(include=["embeddings", "documents", "metadatas"])
        
        if not data or data.get("embeddings") is None or len(data["embeddings"]) < 3:
            return {"status": "skipped", "message": "Not enough embeddings to cluster (minimum 3 required)."}
            
        ids = data["ids"]
        embeddings = np.array(data["embeddings"])
        documents = data["documents"]
        
        n_samples = len(embeddings)
        print(f"Running clustering on {n_samples} vectors...")
        
        # 1. Clustering
        labels = self._compute_clusters(embeddings, n_samples)
        
        # 2. Extract Clusters
        unique_labels = set(labels)
        clusters = {}
        for i, lbl in enumerate(labels):
            if lbl == -1:
                continue # Noise
            if lbl not in clusters:
                clusters[lbl] = {"ids": [], "docs": [], "embeddings": []}
            clusters[lbl]["ids"].append(ids[i])
            clusters[lbl]["docs"].append(documents[i])
            clusters[lbl]["embeddings"].append(embeddings[i])
            
        if not clusters:
            return {"status": "error", "message": "Clustering resulted entirely in noise points."}
            
        print(f"Found {len(clusters)} valid problem clusters.")
        
        # 3. Label Clusters and Update DB
        results = []
        for lbl, cluster_data in clusters.items():
            
            # Sample up to 5 documents for the LLM
            samples = cluster_data["docs"][:5]
            samples_text = "\n".join([f"- {s}" for s in samples])
            
            # Use Groq to generate taxonomy
            taxonomy = self._generate_cluster_taxonomy(samples_text)
            
            # Calculate Centroid
            centroid = np.mean(cluster_data["embeddings"], axis=0).tolist()
            
            # Insert into SQLite
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO problem_clusters (
                        cluster_label, level_1_category, level_2_category, 
                        cluster_description, representative_quote, cluster_size, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    taxonomy.get("cluster_label", f"Cluster {lbl}"),
                    taxonomy.get("level_1_category", "Unknown"),
                    taxonomy.get("level_2_problem", "Unknown"),
                    taxonomy.get("cluster_description", ""),
                    samples[0] if samples else "",
                    len(cluster_data["ids"])
                ))
                cluster_id = cursor.lastrowid
            
            # Update processed_feedback with this cluster_id
            for f_id in cluster_data["ids"]:
                self.db.execute_write(
                    "UPDATE processed_feedback SET cluster_id = ? WHERE feedback_id = ?",
                    (cluster_id, f_id)
                )
                
            results.append({
                "cluster_id": str(cluster_id),
                "label": taxonomy.get("cluster_label"),
                "size": len(cluster_data["ids"])
            })
            
        return {"status": "success", "clusters": results}
        
    def _compute_clusters(self, embeddings: np.ndarray, n_samples: int) -> np.ndarray:
        """Apply HDBSCAN or fallback to Agglomerative Clustering."""
        if n_samples >= 10:
            try:
                min_cluster_size = max(2, min(5, n_samples // 4))
                clusterer = hdbscan.HDBSCAN(min_cluster_size=min_cluster_size, metric='euclidean')
                labels = clusterer.fit_predict(embeddings)
                
                # Check if everything is noise (-1)
                if len(set(labels)) <= 1 and -1 in set(labels):
                    print("HDBSCAN produced only noise. Falling back to Agglomerative Clustering...")
                    return self._fallback_clustering(embeddings, n_samples)
                return labels
            except Exception as e:
                print(f"HDBSCAN failed: {e}. Falling back...")
                return self._fallback_clustering(embeddings, n_samples)
        else:
            return self._fallback_clustering(embeddings, n_samples)
            
    def _fallback_clustering(self, embeddings: np.ndarray, n_samples: int) -> np.ndarray:
        """Fallback for small datasets or HDBSCAN noise."""
        n_clusters = max(2, n_samples // 3)
        if n_clusters >= n_samples:
            n_clusters = max(1, n_samples - 1)
        clusterer = AgglomerativeClustering(n_clusters=n_clusters)
        return clusterer.fit_predict(embeddings)

    def _generate_cluster_taxonomy(self, samples_text: str) -> Dict[str, str]:
        """Ask Groq to generate taxonomy labels for the cluster."""
        prompt = CLUSTER_LABEL_PROMPT.format(samples=samples_text)
        try:
            response = self.groq.complete_json(prompt)
            return response or {}
        except Exception as e:
            logger.error(f"Failed to generate cluster taxonomy: {e}")
            return {}
