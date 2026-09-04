# Edge Cases, Failure Modes & Defensive Strategies (`edgecase.md`)

This document catalogs critical edge cases, boundary conditions, failure modes, and recovery safeguards for every phase of the **AI-Powered VoC Discovery & Wishlist Conversion Engine**.

---

## 1. Edge Cases & Resilience Matrix

| Phase | Boundary Condition / Edge Case | Failure Mode / Risk | Defensive Strategy & Recovery Mechanism |
| :--- | :--- | :--- | :--- |
| **Phase 1** | Schema evolution / SQLite migrations | `sqlite3.OperationalError: no such column` | `init_db()` executes non-destructive `PRAGMA table_info` checks and applies automatic `ALTER TABLE ADD COLUMN` migrations safely. |
| **Phase 1** | Concurrent writes to SQLite database | `sqlite3.OperationalError: database is locked` | Thread-safe connection context manager with `busy_timeout=5000ms` and atomic transactions with `BEGIN IMMEDIATE`. |
| **Phase 2** | Serper Free Credit Depletion / Budget Expiry | Incurring unintended paid API costs | Centralized `SerperBudgetManager` with strict pre-flight count verification, hard ceiling of 50 calls, and SHA-256 query caching. |
| **Phase 2** | YouTube Video Comments Disabled / Geo-restricted | HTTP 403 / 404 error crashing collection loop | Catch `googleapiclient.errors.HttpError`, log error in `youtube_api_requests`, and continue gracefully to next video. |
| **Phase 2** | Malformed / Network Timeout during Web Crawling | Unhandled exception hanging the process | Requests timeout set strictly to 10s, `try/except` wraps every URL extraction, and bad HTTP statuses log to database. |
| **Phase 3** | Text with heavy Unicode mojibake / raw HTML | Garbled text polluting embeddings and LLM | `TextCleaner` applies HTML entity unescaping, regex tag stripping, and normalization before any LLM grading. |
| **Phase 3** | Near-duplicate spam posts with minor character variation | Skewing problem frequency metrics | `Deduplicator` applies Jaccard token-set similarity threshold ($\ge 0.80$) in addition to exact SHA-256 digests. |
| **Phase 4** | LLM Hallucinated Evidence Spans | False citations not present in original text | `ExtractionPipeline.validate_and_ground_evidence()` enforces verbatim substring verification against original input text. |
| **Phase 4** | Groq API Rate Limiting (HTTP 429) | Extraction pipeline crash during batch | `GroqClient` implements exponential backoff retry with automatic model fallback (`qwen/qwen3.8-27b` $\rightarrow$ `qwen/qwen3.6-27b`). |
| **Phase 4** | Groq JSON Output Formatting Errors | JSON decode syntax error | Enforce `response_format={"type": "json_object"}` and Pydantic validation with default fallback values. |
| **Phase 5** | Small / Sparse Dataset (< 20 relevant items) | HDBSCAN creates single noise cluster (-1) | Adaptive clustering fallback: If items $< 30$ or HDBSCAN produces only noise, automatically fallback to Agglomerative / K-Means clustering. |
| **Phase 5** | GPU / Torch CUDA Unavailable | Embedding generation crashes on non-GPU host | `sentence-transformers` automatically loads `BAAI/bge-small-en-v1.5` on CPU with thread pooling. |
| **Phase 6** | Zero Feedback in a Specific Product Category | Division by zero during Opportunity Scoring | Opportunity formula uses smoothed denominators and bounds scores within $[0.0, 100.0]$. |
| **Phase 7** | LLM Proposes Discount / Coupon Solutions | Violating monetary incentive constraint | `AntiDiscountFilter` scans solution text for forbidden discount terms (coupon, % off, discount, cashback) and automatically prompts regeneration. |
| **Phase 8** | RAG Query with Zero Relevant Vectors Retrieved | Hallucinating unsupported recommendations | Distance threshold filter: If cosine similarity $< 0.40$, system returns *"Insufficient empirical evidence in database"* rather than fabricating answers. |
| **Phase 9** | Streamlit Session State Disconnection | UI resets during multi-step analysis | State persistence via SQLite caching and Streamlit `st.session_state` synchronization. |

---

## 2. In-Depth Resilience Protocols

### 2.1 API Key & Network Boundary Handlers
- **Serper / Brave Key Auto-Detection**: When the API key starts with `BSA...`, the system automatically routes to Brave Search API; otherwise it routes to Serper, maintaining identical budget tracking and SQLite logging.
- **YouTube Quota Preservation**: If `search.list` quota limit is approached, the collector prioritizes `commentThreads.list` on already-discovered high-relevance videos (saving 99 quota units per call).

### 2.2 Verbatim Grounding Protocol (Phase 4)
```python
def validate_and_ground_evidence(original_text: str, extracted_span: Optional[str]):
    if not extracted_span or not original_text:
        return None, "inferred"
    if extracted_span.lower() in original_text.lower():
        start_idx = original_text.lower().find(extracted_span.lower())
        return original_text[start_idx:start_idx + len(extracted_span)], "explicit"
    return extracted_span, "inferred"
```

### 2.3 Anti-Discount Defense Protocol (Phase 7)
Any proposed intervention is checked against a strict banned vocabulary:
```python
FORBIDDEN_MONETARY_TERMS = [
    r"\bdiscount(s)?\b", r"\bcoupon(s)?\b", r"\bcashback\b", r"\b\d+%\s*off\b",
    r"\bpromo code\b", r"\bprice drop\b", r"\bmarkdown\b", r"\bfree gift voucher\b"
]
```
If triggered, the solution generator is immediately rejected and re-prompted to focus strictly on structural, informational, and visual confidence solutions (size recommendation algorithms, fabric transparency guides, try-on user proof, and delivery transparency).
