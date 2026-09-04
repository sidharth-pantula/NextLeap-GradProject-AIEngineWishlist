"""Local embedding generator using BAAI/bge-small-en-v1.5 and ChromaDB integration."""
import os
import logging
from typing import List, Dict, Any, Tuple, Optional
import sqlite3

try:
    from sentence_transformers import SentenceTransformer
    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    HAS_SENTENCE_TRANSFORMERS = False

from vector.chroma_store import get_vector_store
from database.db import get_db, Database

logger = logging.getLogger(__name__)


class EmbeddingPipeline:
    """Manages the generation of text embeddings and storing them in ChromaDB."""

    def __init__(self, db: Optional[Database] = None, model_name: str = "BAAI/bge-small-en-v1.5"):
        self.db = db or get_db()
        self.chroma = get_vector_store()
        self.model_name = model_name
        self._model = None

    @property
    def model(self):
        """Lazy load the sentence transformer model."""
        if self._model is None:
            if not HAS_SENTENCE_TRANSFORMERS:
                raise ImportError("sentence-transformers is required. Install with: pip install sentence-transformers")
            print(f"Loading embedding model: {self.model_name} ...")
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def generate_embeddings(self, texts: List[str], is_query: bool = False) -> List[List[float]]:
        """
        Generate dense embeddings for a list of texts.
        
        Args:
            texts: List of strings to embed.
            is_query: If True, prepends the BGE query instruction.
        """
        if not texts:
            return []
            
        if is_query:
            # BGE specific query instruction
            texts = [f"Represent this sentence for searching relevant passages: {t}" for t in texts]
            
        embeddings = self.model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
        return embeddings.tolist()

    def format_composite_chunk(self, evidence_span: str, inferred_user_need: str) -> str:
        """Format the primary embedding unit capturing symptom and latent need."""
        evidence = evidence_span.strip() if evidence_span else "Unknown symptom"
        need = inferred_user_need.strip() if inferred_user_need else "Unknown need"
        return f"[Symptom]: {evidence} | [Underlying Need]: {need}"

    def process_unembedded_feedback(self, batch_size: int = 100) -> int:
        """
        Find processed_feedback records that haven't been embedded yet,
        generate composite embeddings, and store them in ChromaDB.
        """
        # We need a way to track what has been embedded. 
        # We can either check ChromaDB or add an 'is_embedded' flag. 
        # For now, we will fetch all relevant records and upsert (Chroma handles overwrites).
        
        query = """
            SELECT 
                p.feedback_id, p.evidence_span, p.inferred_user_need, 
                p.purchase_barrier, p.uncertainty_type, p.decision_stage, 
                p.relevance_score, r.source
            FROM processed_feedback p
            LEFT JOIN raw_feedback r ON p.feedback_id = r.feedback_id
            WHERE p.relevance_score >= 2 
              AND (p.evidence_span IS NOT NULL OR p.inferred_user_need IS NOT NULL)
        """
        records = self.db.execute_query(query)
        if not records:
            return 0
            
        # Optional: Check which IDs already exist in ChromaDB to avoid redundant embedding,
        # but upserting is fine for small batches.
        
        total_embedded = 0
        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]
            
            ids = []
            documents = []
            metadatas = []
            
            for row in batch:
                ids.append(row["feedback_id"])
                doc = self.format_composite_chunk(
                    row.get("evidence_span") or "",
                    row.get("inferred_user_need") or ""
                )
                documents.append(doc)
                
                # Clean metadata
                meta = {
                    "purchase_barrier": row.get("purchase_barrier") or "none",
                    "uncertainty_type": row.get("uncertainty_type") or "none",
                    "decision_stage": row.get("decision_stage") or "unknown",
                    "source": row.get("source") or "unknown",
                    "relevance_score": row.get("relevance_score") or 0
                }
                metadatas.append(meta)
                
            embeddings = self.generate_embeddings(documents, is_query=False)
            
            # Upsert into ChromaDB
            self.chroma.add_feedback_embeddings(
                feedback_ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas
            )
            total_embedded += len(ids)
            print(f"Embedded and stored {total_embedded}/{len(records)} records...")
            
        return total_embedded
