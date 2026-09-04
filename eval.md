# Evaluation Framework & Phase-wise Benchmark Metrics (`eval.md`)

This document defines the formal quantitative and qualitative evaluation criteria, benchmark datasets, validation scripts, and acceptance thresholds across all 9 phases of the **AI-Powered VoC Discovery & Wishlist Conversion Engine**.

---

## 1. Phase-wise Evaluation Matrix

| Phase | Phase Name | Primary Evaluation Metrics | Target Threshold | Evaluation Method / Test Script |
| :--- | :--- | :--- | :--- | :--- |
| **Phase 1** | Storage & Vector Infrastructure | SQLite Schema Integrity, ChromaDB Query Latency | Zero data corruption, Query < 50ms | `tests/test_phase1_storage.py` |
| **Phase 2** | Data Ingestion & API Safeties | Quota Adherence, Budget Limit Enforcement, Duplicate Ratio | 100% hard limit cutoff, 0 credit overrun | `tests/test_phase2_collectors.py`, `tests/test_serper_budget.py` |
| **Phase 3** | Cleaning & Relevance Grading | Precision, Recall, Spam Rejection Rate, False Positive Rate | F1 $\ge 0.88$, Spam Filter > 95% | `tests/test_phase3_processing.py` |
| **Phase 4** | Structured Extraction & Grounding | Zero-Hallucination Rate, Pydantic Schema Pass Rate | Evidence Grounding = 100%, Valid JSON = 100% | `tests/test_phase4_extraction.py` |
| **Phase 5** | Embeddings & Semantic Clustering | Silhouette Score, Topic Coherence, Cluster Stability | Silhouette $\ge 0.35$, Outlier Ratio < 25% | `tests/test_phase5_clustering.py` |
| **Phase 6** | Behavioral Analytics & Opportunity Scoring | Mathematical Consistency, Ranking Stability | Opportunity Score $\in [0, 100]$, Consistency = 100% | `tests/test_phase6_analysis.py` |
| **Phase 7** | Hybrid RAG & PM Research Engine | Faithfulness, Answer Relevance, Quote Traceability | Grounded Verbatim Citations, Zero Math Hallucination | `tests/test_phase7_rag.py` |
| **Phase 8** | Streamlit Presentation Dashboard (4 Views) | Multi-View Interaction, Filter Responsiveness | Load < 2s, 0 Uncaught Exceptions | `tests/test_phase8_dashboard.py` |
| **Phase 9** | End-to-End Orchestration & Verification | Full Pipeline Test Coverage, Zero Regressions | 100% Pytest Pass Rate | `tests/` |

---

## 2. Detailed Evaluation Specifications

### Phase 1: Storage & Database Integrity
- **Metric 1: Foreign Key & Constraint Integrity**: `PRAGMA foreign_key_check` and `PRAGMA integrity_check` must return 0 errors.
- **Metric 2: Concurrent Write Thread Safety**: Zero SQLite `database locked` operational errors across concurrent worker threads.
- **Metric 3: ChromaDB Vector Upsert & Fetch**: Insertion of 1,000 vectors with metadata filter execution under 100ms.

### Phase 2: Data Ingestion & Budget Safeties
- **Metric 1: Serper Hard Limit Ceiling**: Pre-flight limit check halts execution precisely at the configured maximum requests ($N \le 50$) with zero network overshoot.
- **Metric 2: YouTube Quota Tracking**: Quota unit accounting tracks `search.list` (100 units) and `commentThreads.list` (1 unit) with $\pm 0$ unit drift.
- **Metric 3: Schema Normalization Consistency**: 100% of collected records from YouTube, Web Search, Reddit, and Hugging Face match the standardized `raw_feedback` schema.

### Phase 3: Cleaning & 0–3 Relevance Grading
- **Metric 1: Spam & Bot Rejection**: Auto-moderator, affiliate links (`amzn.to`, `bit.ly`), and promotional spam detected and tagged with score 0 with $>98\%$ recall.
- **Metric 2: Relevance Classification Precision**:
  - Score 3 (Wishlist/Hesitation/Drop intent): $\ge 90\%$ Precision against manual golden test set.
  - Score 2 (Sizing/Quality/Returns friction): $\ge 85\%$ Precision.
  - Score 0 (Irrelevant): $\ge 95\%$ Precision.
- **Metric 3: Deduplication Efficiency**: Exact SHA-256 and Jaccard near-duplicate filter ($\ge 0.80$) collapses duplicate customer posts into single canonical records.

### Phase 4: Structured LLM Information Extraction
- **Metric 1: Zero-Hallucination Evidence Grounding**: 100% of `evidence_span` outputs must be verified as verbatim substrings of original text before storage.
- **Metric 2: Schema Conformance**: 100% valid Pydantic type validation across all 30+ categorical, boolean, and textual fields.
- **Metric 3: Job-to-be-Done Inference Validity**: Inferred user needs must articulate non-obvious root blockers (e.g., sizing conversion, fabric translucency proof) rather than repeating the barrier title.

### Phase 5: Semantic Clustering & Dynamic Taxonomy
- **Metric 1: Vector Space Density**: Average silhouette coefficient $\ge 0.35$ on BGE embeddings.
- **Metric 2: Cluster Label Distinctiveness**: Dynamic 2-Level taxonomy labels (Level 1 Category + Level 2 Sub-Problem) evaluated for semantic orthogonality.
- **Metric 3: Outlier Containment**: Noise points in HDBSCAN isolated without distorting core problem cluster centroids.

### Phase 6: Behavioral Analytics & Opportunity Scoring
- **Metric 1: Deterministic Composite Formula**: Opportunity Score rigorously calculated as:
  $$\text{Opportunity Score} = 0.25 \times \text{Prevalence} + 0.25 \times \text{Linkage} + 0.20 \times \text{SourceBreadth} + 0.15 \times \text{ExplicitRate} + 0.15 \times \text{Confidence}$$
- **Metric 2: Non-Monetary Product Focus**: Rationales strictly emphasize product interventions (fit guides, transparency, user proof) rather than discounts.
- **Metric 3: Multi-Dimensional Slicing**: 100% of relevant records partitioned into category, price tier, and decision stage breakdowns.

### Phase 7: Hybrid RAG & PM Research Engine
- **Metric 1: Zero Math Hallucination**: Quantitative figures in LLM responses strictly match SQL summary ground truth.
- **Metric 2: Verbatim Evidence Attribution**: 100% of quote spans in responses match ChromaDB retrieved feedback and include source metadata.
- **Metric 3: Epistemic Honesty & Sparsity Handling**: When sample size is small or evidence is missing, the response explicitly declares confidence level and missing data gaps.
- **Metric 4: Structured Format Compliance**: Output strictly follows the 9-part standard (Finding, Quantification, Segments, Behaviour, Evidence, Confidence, Interpretation, Contradictory Evidence, Hypotheses).

### Phase 8: VoC Research RAG Engine
- **Metric 1: Ragas Faithfulness Score**: $\ge 0.88$ (All claims in synthesized answers directly grounded in retrieved feedback chunks).
- **Metric 2: Answer Relevance Score**: $\ge 0.85$ (Directly answers the strategic research question).
- **Metric 3: Multi-Source Citation Coverage**: Citations accurately map to `feedback_id` and original source URLs.

### Phase 9: Streamlit Dashboard UI
- **Metric 1: Visual Presentation Excellence**: Glassmorphism cards, interactive Plotly charts, dynamic cluster exploration, and responsive layouts.
- **Metric 2: Query Execution Speed**: End-to-end dashboard load and interactive filter response $< 1.5\text{s}$.
