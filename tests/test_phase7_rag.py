"""Unit tests for Phase 7: Hybrid RAG & PM Research Engine."""
import pytest
from database.db import get_db
from vector.chroma_store import get_vector_store
from rag.retrieval import HybridRetriever
from rag.research_engine import ResearchEngine


@pytest.fixture(scope="module")
def setup_phase7_context():
    """Setup test data in SQLite and ChromaDB for Phase 7 tests."""
    db = get_db()
    chroma = get_vector_store()

    # Ensure test problem cluster and opportunity score
    db.execute_write("""
        INSERT OR IGNORE INTO problem_clusters (cluster_id, level_1_category, level_2_category, cluster_label, cluster_description, created_at)
        VALUES (888, 'Quality & Material', 'Fabric Transparency', 'Translucent Material Hesitation', 'Users complain fabric is sheer', CURRENT_TIMESTAMP)
    """)
    db.execute_write("""
        INSERT OR IGNORE INTO cluster_metrics (cluster_id, frequency, prevalence_pct, source_breadth, explicit_evidence_rate, inferred_evidence_rate, purchase_linkage_score, calculation_timestamp)
        VALUES (888, 4, 40.0, 2, 75.0, 25.0, 100.0, CURRENT_TIMESTAMP)
    """)
    db.execute_write("""
        INSERT OR IGNORE INTO opportunity_scores (cluster_id, opportunity_score, priority_rank, rationale, calculated_at)
        VALUES (888, 82.5, 1, 'Top quality barrier', CURRENT_TIMESTAMP)
    """)

    # Raw and processed feedback
    db.execute_write("""
        INSERT OR IGNORE INTO raw_feedback (feedback_id, source, source_type, text, collection_timestamp)
        VALUES ('test_p7_1', 'youtube', 'comment', 'The white shirt is completely see-through in daylight', CURRENT_TIMESTAMP)
    """)
    db.execute_write("""
        INSERT OR IGNORE INTO processed_feedback (
            feedback_id, relevance_score, evidence_span, inferred_user_need, 
            purchase_barrier, uncertainty_type, decision_stage, purchase_outcome, 
            product_category, cluster_id, processing_timestamp
        ) VALUES (
            'test_p7_1', 3, 'white shirt is completely see-through', 'Needs opaque fabric or lining',
            'Material transparency', 'quality_uncertainty', 'Consideration', 'abandoned',
            'Apparel', 888, CURRENT_TIMESTAMP
        )
    """)

    yield db, chroma

    # Cleanup
    db.execute_write("DELETE FROM processed_feedback WHERE feedback_id = 'test_p7_1'")
    db.execute_write("DELETE FROM raw_feedback WHERE feedback_id = 'test_p7_1'")
    db.execute_write("DELETE FROM opportunity_scores WHERE cluster_id = 888")
    db.execute_write("DELETE FROM cluster_metrics WHERE cluster_id = 888")
    db.execute_write("DELETE FROM problem_clusters WHERE cluster_id = 888")


def test_hybrid_retriever(setup_phase7_context):
    db, chroma = setup_phase7_context
    retriever = HybridRetriever(db=db, chroma=chroma)

    sql_data = retriever.retrieve_sql_analytics("What are top barriers?")
    assert "summary_text" in sql_data
    assert "total_raw" in sql_data
    assert "total_relevant" in sql_data
    assert len(sql_data["top_opportunities"]) > 0

    context = retriever.retrieve("Why are users hesitating to buy white shirts?")
    assert "sql_summary" in context
    assert "evidence_quotes" in context
    assert "query" in context


def test_research_engine_synthesis(setup_phase7_context):
    db, chroma = setup_phase7_context
    engine = ResearchEngine(db=db)

    result = engine.answer_query("Why do users hesitate to buy sheer clothes?", top_k=3)
    assert "query" in result
    assert "response" in result
    assert "context" in result
    assert len(result["response"]) > 0
    # Verify mandatory structured format sections exist in response
    assert "Finding" in result["response"]
    assert "Quantification" in result["response"]
