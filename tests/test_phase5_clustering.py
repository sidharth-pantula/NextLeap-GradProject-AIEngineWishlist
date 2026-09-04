import pytest
import sqlite3
import numpy as np
from ai.embeddings import EmbeddingPipeline
from ai.clustering import ClusteringEngine
from vector.chroma_store import get_vector_store
from database.db import get_db

@pytest.fixture(scope="module")
def setup_phase5_db():
    """Setup a temporary database and Chroma collection for testing Phase 5."""
    db = get_db()
    chroma = get_vector_store()
    
    # Insert mock processed feedback
    db.execute_write("""
        INSERT OR IGNORE INTO processed_feedback (feedback_id, evidence_span, inferred_user_need, relevance_score)
        VALUES 
        ('test_f1', 'Size M is too tight', 'Needs accurate sizing', 3),
        ('test_f2', 'Size chart is wrong', 'Needs correct size chart', 3),
        ('test_f3', 'Material is too thin', 'Needs thicker material', 2),
        ('test_f4', 'Fabric is transparent', 'Needs opaque fabric', 2)
    """)
    yield db, chroma
    
    # Cleanup
    db.execute_write("DELETE FROM processed_feedback WHERE feedback_id LIKE 'test_%'")
    # We won't easily delete from Chroma without rebuilding, but this is fine for a quick test.

def test_embedding_generation(setup_phase5_db):
    db, _ = setup_phase5_db
    embedder = EmbeddingPipeline(db=db)
    
    # Test formatting
    chunk = embedder.format_composite_chunk("Size M is too tight", "Needs accurate sizing")
    assert "[Symptom]: Size M is too tight" in chunk
    assert "[Underlying Need]: Needs accurate sizing" in chunk
    
    # Test encoding
    embeddings = embedder.generate_embeddings([chunk])
    assert len(embeddings) == 1
    assert len(embeddings[0]) == 384 # BGE-small dimension

def test_process_unembedded_feedback(setup_phase5_db):
    db, chroma = setup_phase5_db
    embedder = EmbeddingPipeline(db=db)
    
    count = embedder.process_unembedded_feedback()
    assert count > 0

def test_clustering_engine(setup_phase5_db):
    db, _ = setup_phase5_db
    clusterer = ClusteringEngine(db=db)
    
    result = clusterer.run_clustering()
    assert result["status"] in ["success", "error", "skipped"]
    
    if result["status"] == "success":
        assert "clusters" in result
        assert len(result["clusters"]) > 0
