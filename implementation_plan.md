# Phase-Wise Implementation Plan
## AI-Powered Voice-of-Customer (VoC) Wishlist-to-Purchase Discovery Engine

Based on [`context.md`](./context.md) and [`architecture.md`](./architecture.md), this document establishes the detailed, phase-wise roadmap for building the discovery engine. Each phase specifies its scope, components, input/output data flow, validation checkpoints, acceptance criteria, and links to:
- [`eval.md`](./eval.md) — Comprehensive quantitative evaluation metrics and benchmarks across all phases.
- [`edgecase.md`](./edgecase.md) — Edge cases, defensive boundary conditions, and failure mode recovery strategies.

---

## Roadmap Overview

```
Phase 1: Infrastructure & Storage Foundation
   │
   ▼
Phase 2: Data Ingestion Subsystem (YouTube, HF Datasets, Serper Web, Reddit)
   │
   ▼
Phase 3: Data Cleaning, Deduplication & Relevance Classification (Groq 0-3)
   │
   ▼
Phase 4: Structured LLM Information Extraction & Evidence Provenance
   │
   ▼
Phase 5: Local BGE Vector Pipeline & Unsupervised Semantic Clustering
   │
   ▼
Phase 6: Deterministic Quantification, Segmentation & Opportunity Engine
   │
   ▼
Phase 7: Hybrid RAG & Natural Language PM Research Engine
   │
   ▼
Phase 8: Interactive Streamlit Presentation Dashboard (4 Views)
   │
   ▼
Phase 9: Pipeline Orchestration & End-to-End Test Suite
```

---

## Phase 1: Infrastructure, Environment & Storage Foundation

### 1.1 Objective
Establish the project skeleton, dependency environment, credential management, SQLite relational database schemas, and local ChromaDB client setup.

### 1.2 Files to Create
- `requirements.txt` — Core project dependencies (`groq`, `sentence-transformers`, `chromadb`, `pandas`, `numpy`, `scikit-learn`, `hdbscan`, `datasets`, `google-api-python-client`, `streamlit`, `python-dotenv`, `pytest`).
- `.env.example` & `.gitignore` — Template for `GROQ_API_KEY`, `YOUTUBE_API_KEY`, `SERPER_API_KEY`, `REDDIT_*`, `HF_TOKEN`, and ignore rules for databases, cache, and secrets.
- `database/schema.py` — SQLite DDL definitions for all tables (`raw_feedback`, `processed_feedback`, `problem_clusters`, `cluster_metrics`, `opportunity_scores`, `shopper_sessions`, `research_queries`) with indexing.
- `database/db.py` — Thread-safe context-managed SQLite connection handler, transaction management, and query helpers.
- `vector/chroma_store.py` — Local ChromaDB persistent client manager handling collections (`feedback_embeddings`, `evidence_embeddings`, `user_needs_embeddings`).

### 1.3 Key Schemas Initialized
- `raw_feedback`: Ingestion staging table preserving original verbatim text and metadata.
- `processed_feedback`: Structured signals, purchase barriers, uncertainties, decision stages, quote spans, and cluster foreign keys.
- `shopper_sessions`: Quantitative session metrics from `jlh/uci-shopper` (`Administrative`, `Informational`, `ProductRelated`, `BounceRates`, `ExitRates`, `Revenue`).
- `problem_clusters`, `cluster_metrics`, `opportunity_scores`: Derived analytical tables.

### 1.4 Acceptance Criteria & Verification
- [ ] Running schema initialization creates all 7 tables and 10 indexes in `data/discovery_engine.db`.
- [ ] ChromaDB initializes persistent local storage in `chroma_db/` without network errors.
- [ ] Environment variables load correctly via `python-dotenv`.

---

## Phase 2: Modular Data Ingestion Subsystem & YouTube Discovery Layer

### 2.1 Objective
Build source-specific collectors that retrieve fashion shopping conversations and session datasets, transforming them into the standardized `raw_feedback` schema and `shopper_sessions` table.

The primary discovery milestone is the **YouTube Discovery + Data Collection Layer**, targeting behavioral evidence around **Wishlist $\rightarrow$ Purchase conversion barriers** in online fashion rather than generic brand sentiment.

---

### 2.2 YouTube Discovery Architecture & Specifications

#### Part 1: Search Query Library (`config/youtube_search_queries.json`)
Organized across 15 behavioral research categories:
- **A. Wishlist / Save / Bookmark Behaviour**:
  - Global: *"fashion wishlist"*, *"clothing wishlist"*, *"clothes saved for later"*, *"fashion items saved for later"*, *"clothes I want to buy later"*, *"fashion products I am saving"*, *"online shopping wishlist"*, *"clothing wishlist shopping"*, *"saving clothes to buy later"*, *"bookmarking clothes online"*, *"fashion items I want to buy"*, *"clothes I keep saving"*, *"wishlist shopping experience"*.
  - India: *"Myntra wishlist"*, *"Myntra saved items"*, *"Myntra wishlist shopping"*, *"AJIO wishlist"*, *"AJIO saved items"*, *"Flipkart fashion wishlist"*, *"Amazon fashion wishlist India"*, *"Indian online fashion wishlist"*.
- **B. Purchase Hesitation**:
  - *"why I don't buy clothes online"*, *"why I hesitate buying clothes online"*, *"online fashion purchase hesitation"*, *"why I postpone buying clothes"*, *"why I don't purchase clothes I like"*, *"online clothing purchase decision"*, *"deciding whether to buy clothes online"*, *"fashion shopping hesitation"*, *"clothes shopping decision making"*.
- **C. Price / Price Drop**:
  - *"waiting for price drop clothes"*, *"waiting for price drop fashion"*, *"waiting for clothes to become cheaper"*, *"fashion price drop shopping"*, *"clothes price tracking"*, *"should I wait for price drop clothes"*, *"online fashion price comparison"*, *"fashion shopping price comparison India"*.
- **D. Sales / Discounts**:
  - Global: *"waiting for sale clothes"*, *"waiting for fashion sale"*, *"should I wait for sale clothes"*, *"buying clothes during sale"*, *"online fashion sale shopping"*, *"fashion sale buying behaviour"*, *"clothes sale shopping tips"*, *"fashion discount shopping"*, *"best time to buy clothes online"*.
  - India: *"Myntra sale shopping"*, *"Myntra sale buying"*, *"Myntra End of Reason Sale"*, *"Myntra EORS shopping"*, *"AJIO sale shopping"*, *"Flipkart fashion sale"*, *"Amazon fashion sale India"*, *"Indian online fashion sale"*.
- **E. Festival Sales (India)**:
  - *"Diwali online shopping clothes"*, *"Diwali fashion shopping"*, *"Diwali fashion sale"*, *"online shopping during Diwali"*, *"Myntra Diwali sale"*, *"Myntra festive sale"*, *"AJIO Diwali sale"*, *"Flipkart Big Billion Days fashion"*, *"Amazon Great Indian Festival fashion"*, *"Indian festive shopping clothes"*, *"Navratri fashion shopping online"*, *"wedding season fashion shopping India"*.
- **F. Offers / Coupons / Promotions**:
  - *"fashion coupon shopping"*, *"clothing coupon online"*, *"fashion promo code shopping"*, *"fashion cashback shopping"*, *"online fashion offers"*, *"fashion bank offer shopping"*, *"Myntra coupon shopping"*, *"AJIO coupon shopping"*, *"Myntra bank offer"*, *"fashion sale coupon worth it"*, *"online fashion discount decision"*.
- **G. Fit / Size**:
  - *"online clothes sizing problem"*, *"online clothing fit problem"*, *"clothes don't fit online shopping"*, *"fashion size uncertainty"*, *"Myntra sizing problem"*, *"AJIO sizing problem"*, *"online dress size problem"*, *"choosing clothes size online"*, *"how to know clothes will fit online"*.
- **H. Quality / Material**:
  - *"online clothes quality problem"*, *"online clothing quality before buying"*, *"fashion quality reviews"*, *"clothes material before buying"*, *"Myntra quality problem"*, *"AJIO quality problem"*, *"online fashion quality disappointment"*, *"clothes look different from photos"*.
- **I. Reviews / Social Proof**:
  - *"fashion reviews before buying"*, *"clothing reviews before purchase"*, *"do reviews affect fashion purchase"*, *"fashion product reviews shopping"*, *"online clothing reviews"*, *"checking reviews before buying clothes"*, *"fashion influencer recommendation purchase"*, *"YouTube fashion review before buying"*.
- **J. Comparison**:
  - *"comparing clothes before buying"*, *"compare fashion products online"*, *"clothing comparison before purchase"*, *"choosing between two dresses"*, *"choosing between clothing brands"*, *"fashion product alternatives"*, *"which clothes should I buy"*, *"comparing Myntra and AJIO"*, *"Myntra vs AJIO fashion shopping"*, *"Amazon vs Myntra fashion"*.
- **K. Return / Exchange**:
  - *"online clothes return concerns"*, *"clothes return before buying"*, *"fashion return policy purchase decision"*, *"online clothing exchange problem"*, *"Myntra return problem"*, *"AJIO return problem"*, *"clothes don't fit return online"*.
- **L. Availability / Stock**:
  - *"clothes out of stock shopping"*, *"fashion size out of stock"*, *"wishlist item out of stock"*, *"waiting for size to come back"*, *"fashion product stock availability"*, *"Myntra size unavailable"*, *"AJIO size unavailable"*, *"clothes wishlist unavailable"*.
- **M. Styling / Occasion**:
  - *"should I buy this dress"*, *"does this outfit suit me"*, *"fashion purchase advice"*, *"clothes for occasion online shopping"*, *"wedding outfit shopping online"*, *"office clothes online shopping"*, *"party outfit buying decision"*, *"styling before buying clothes"*.
- **N. External Information Seeking**:
  - *"what to check before buying clothes online"*, *"fashion shopping advice"*, *"online clothing buying tips"*, *"how to decide what clothes to buy"*, *"fashion product research before buying"*, *"clothes buying advice YouTube"*, *"fashion shopping mistakes"*.
- **O. Brand / Platform Experience (Behavior-centric)**:
  - *"Myntra shopping experience"*, *"Myntra buying experience"*, *"Myntra fashion shopping review"*, *"AJIO shopping experience"*, *"AJIO buying experience"*, *"Flipkart fashion shopping review"*, *"Amazon fashion shopping India"*.

#### Part 2: Search Strategy & Deduplication (`search.list`)
- Set `type=video`, retrieve configurable max results per query.
- Extract: `video_id`, `title`, `description`, `channel_id`, `channel_name`, `published_at`, `url`, `search_query`, `research_category`, `rank`.
- Deduplicate across queries and track multi-query discovery counts.

#### Part 3: Video Relevance Filter (Metadata Stage)
Classifies discovered videos prior to comment extraction:
- `0`: Irrelevant
- `1`: Peripheral fashion content
- `2`: Relevant online shopping discussion
- `3`: Highly relevant purchase-decision discussion
- `4`: Directly relevant to wishlist / purchase hesitation / conversion

#### Part 4: Comment Collection (`commentThreads.list`)
For relevant videos, fetch public comment threads:
- Arguments: `videoId`, `maxResults`, `textFormat='plainText'`, `order='relevance'`.
- Fields: `comment_id`, `video_id`, `parent_comment_id`, `text`, `published_at`, `updated_at`, `like_count`, `reply_count`, `url`, `search_query`, `research_category`.
- Pagination support via `pageToken`.

#### Part 5: In-Video Comment Search Keywords
Candidate generation keywords for deep search:
`wishlist`, `saved`, `save`, `buy later`, `waiting`, `sale`, `discount`, `price`, `price drop`, `expensive`, `compare`, `size`, `sizing`, `fit`, `quality`, `review`, `return`, `exchange`, `out of stock`, `sold out`, `recommend`, `worth it`, `coupon`, `offer`, `Diwali`, `EORS`, `Big Billion Days`, `Great Indian Festival`.

#### Part 6: Raw Storage Schemas
- `youtube_videos`: video-level discovery metadata and relevance score.
- `youtube_comments`: raw comment threads and replies.
- `raw_feedback`: normalized common schema (`source="youtube"`, `source_type="comment"`).

#### Part 7: Quota Management (`collectors/youtube_quota_manager.py`)
- Explicit tracking of YouTube API quota units (search.list ~100 units vs commentThreads.list ~1 unit).
- Request logging (endpoint, timestamp, success/failure, estimated quota cost).
- Search query result caching to avoid redundant API calls.
- Hard safety cutoffs on total quota and pagination depth.

#### Part 8: 10-Query Initial Test Protocol
Run a controlled initial test with strictly 10 representative queries across key research dimensions:
1. Wishlist: *"Myntra wishlist"*
2. Purchase hesitation: *"why I hesitate buying clothes online"*
3. Price drop: *"waiting for price drop clothes"*
4. Sale: *"Myntra sale shopping"*
5. Festival sale: *"Diwali online shopping clothes"*
6. Sizing: *"online clothes sizing problem"*
7. Quality: *"online clothes quality problem"*
8. Comparison: *"comparing clothes before buying"*
9. Social proof: *"checking reviews before buying clothes"*
10. Platform behavior: *"AJIO shopping experience"*

Stop after test and output:
- Queries executed, videos found, unique videos, duplicate videos, comments collected, duplicate comments, API calls, estimated quota used, top relevant videos/comments, and errors.

---

---

### 2.3 Public Web Research & Discovery Layer (Serper API)

#### Part 1: Core Research Questions & Dimensions
The web discovery layer discovers online discussions across 16 core behavioral dimensions:
1. **Why Users Save / Wishlist**: Intent behind saving, bookmarking vs. temporary shortlisting, holding items without ready intent.
2. **Purchase Intent Validation**: Distinguishing High Intent vs. Low Intent vs. Pure Bookmarking (revisiting vs. forgetting saved items).
3. **Comprehensive Purchase Barriers**:
   - Price: Perceived poor value, waiting for drops/sales, price shock.
   - Fit & Size: Brand size discrepancies, body-type uncertainty, fear of return hassles.
   - Quality & Material: Durability, sheer/transparent fabric, expectation vs. reality.
   - Information Gaps: Missing measurements, lack of real customer photos/videos.
   - Trust: Seller credibility, counterfeit fears, fake review suspicion.
   - Reviews: Conflicting reviews, difficulty parsing feedback.
   - Returns & Exchanges: Return fees, policy friction, exchange delays.
   - Availability: Out-of-stock sizes/colors, restock waiting.
   - Style & Occasion: Wardrobe mismatch, styling hesitation.
   - Comparison: Choice overload, indecision between multiple items.
4. **Purchase Triggers (Monetary & Non-Monetary)**: Discounts, size confidence, try-on photos, styling guides, restock alerts, deadline urgency.
5. **Discount & Sale Dynamics**: Behavioral patterns around EORS, Big Billion Days, Great Indian Festival, and regret over pre-sale buying.
6. **Price Drop Tracking**: Price alert monitoring, abandonment after price spikes.
7. **Cross-Platform & Alternative Comparison**: Comparing Product A vs B vs C across Myntra, AJIO, Amazon, Reddit recommendations.
8. **External Information Seeking**: Post-discovery searches on Google, Reddit, YouTube try-on hauls, Instagram, and review blogs.
9. **Fit & Sizing Uncertainty**: Body-shape concerns, size chart confusion, buying multiple sizes.
10. **Quality & Material Uncertainty**: Photo-to-reality mismatch, fabric feel, stitching flaws.
11. **Reviews & Social Proof**: Customer photos, Reddit consensus, influencer validation.
12. **Occasion & Deadline Urgency**: Weddings, festivals, workwear deadlines altering hesitation.
13. **Indian Festival Shopping**: Diwali, Navratri, wedding season sales, impulse vs planned buys.
14. **Reservation & Stock Availability**: "Hold my size", "Notify me when available" behavior.
15. **User Segment Differences**: New vs experienced, budget vs premium shoppers.
16. **Negative & Positive Cases**: Tracking both "saved and bought because..." and "saved and never bought because...".

#### Part 2: Programmatic Query Generator (`config/web_search_queries.json`)
Generates high-information query combinations programmatically:
$$\text{Query} = \text{USER ACTION} + \text{PRODUCT} + \text{DECISION STAGE} + \text{BARRIER/TRIGGER} + \text{CONTEXT}$$
Examples:
- `"saved fashion item before buying price drop India"`
- `"wishlisted dress hesitation sizing problem reddit"`
- `"why I didn't buy clothes after saving Myntra review"`

#### Part 3: Domain Discovery
Discovers evidence across multi-domain sources:
`site:reddit.com`, `site:quora.com`, `site:youtube.com`, consumer forums, shopping communities, fashion blogs, public review portals.

#### Part 4: Strict Serper Budget Control (`collectors/serper_budget_manager.py`)
- **Hard Free-Credit Allowance Constraint**: Total free credit ceiling (~$5).
- **Default Hard Ceiling**: 50 total requests max.
- **Initial Test Run**: Strictly **10 API requests**.
- **Enforcements**: Pagination OFF, automatic retry OFF, no background loops, SHA-256 query caching, automatic stop on limit.

#### Part 5: Storage Schemas (`web_search_results` & `web_search_requests`)
- `web_search_results`: (`id`, `query`, `research_category`, `search_timestamp`, `rank`, `title`, `url`, `snippet`, `domain`, `duplicate_count`, `first_discovered_at`, `last_discovered_at`, `retrieval_status`).
- `web_search_requests`: (`request_id`, `timestamp`, `query`, `category`, `status`, `result_count`, `error`, `estimated_usage_if_available`).

#### Part 6: Public Page Retrieval & Content Classification (`collectors/web_pages.py`)
- Retrieves public page content where permitted respecting `robots.txt`, rate limits, and terms.
- Classifies retrieved content into:
  - `USER_GENERATED` (Forum posts, customer reviews, Q&A discussions)
  - `COMMERCIAL/PRODUCT_CONTEXT` (Product pages, retailer banners)
  - `EDITORIAL` (Fashion blogs, articles)
  - `OTHER`
- Ingests `USER_GENERATED` content into normalized `raw_feedback` (`source="web"`).

#### Part 7: 10-Search Initial Test Protocol
Executes strictly 10 representative searches covering key research categories:
1. Wishlist / Save behavior
2. Purchase hesitation
3. Price / sale waiting
4. Price drop behavior
5. Fit / size uncertainty
6. Reviews / social proof
7. Product comparison
8. External research
9. Indian festival shopping
10. Myntra / AJIO shopping behavior

Stops immediately after 10 requests and outputs:
- Requests used, results returned, unique URLs, duplicate URLs, domains discovered, categories covered, remaining request allowance, sample snippets.

---

### 2.4 Other Collectors in Phase 2
- `collectors/hf_dataset_loader.py` — Ingests **`jlh/uci-shopper`** (12,330 e-commerce sessions) into `shopper_sessions` and complementary review datasets.
- `collectors/reddit_collector.py` — Ingests fashion community posts/comments from Reddit dumps or PRAW API.

---

### 2.5 Acceptance Criteria & Verification
- [ ] `youtube_search_queries.json` & `web_search_queries.json` contain complete research category query banks.
- [ ] `YouTubeQuotaManager` & `SerperBudgetManager` enforce strict API call caps and safety stops.
- [ ] Controlled 10-request tests for YouTube and Serper execute cleanly and populate SQLite staging tables.
- [ ] Content classifier separates `USER_GENERATED` evidence from marketing noise.
- [ ] All records cleanly convert to `raw_feedback` schema.

---

## Phase 3: Data Cleaning, Deduplication & Relevance Filtering

### 3.1 Objective
Sanitize incoming raw text, remove duplicates, and use Groq LLM to filter out noise, categorizing records on a strict 0–3 relevance scale.

### 3.2 Files to Create
- `processing/cleaning.py` — Text normalization:
  - Strips HTML tags, fixes Unicode mojibake, cleans excessive whitespace.
  - Filters promotional spam, bot messages, affiliate links, and gibberish.
- `processing/deduplication.py` — Deduplication engine:
  - Exact deduplication using SHA-256 hashes of cleaned text.
  - Near-duplicate detection using MinHash / Jaccard similarity.
- `prompts/relevance_prompt.txt` — Zero-shot / Few-shot prompt template for 0–3 grading with structured reasoning.
- `processing/relevance.py` — Relevance classifier using Groq LLM:
  - `0 (Irrelevant)`: Spam, unrelated chit-chat.
  - `1 (Peripheral)`: General fashion talk without shopping decision info.
  - `2 (Relevant)`: Discusses sizing, fit, quality, returns, or price perceptions.
  - `3 (Highly Relevant)`: Explicitly mentions wishlist behavior, hesitation, postponement, cart abandonment, product comparison, or external research.

### 3.3 Acceptance Criteria & Verification
- [ ] Cleaned records preserve original text in `raw_feedback` while storing sanitization flags.
- [ ] Exact duplicate records are rejected with zero database corruption.
- [ ] Relevance classifier grades a test batch and populates `relevance_score`, `relevance_reason`, and `relevance_confidence`.

---

## Phase 4: Structured LLM Information Extraction & Evidence Provenance

### 4.1 Objective
For all relevant records (`relevance_score >= 2`), extract structured behavioral signals, purchase barriers, uncertainties, decision stages, exact quote spans, and inferred user needs.

### 4.2 Files to Create
- `ai/groq_client.py` — Resilient Groq client with JSON-mode enforcement, token tracking, retry logic, and exponential backoff on HTTP 429.
- `prompts/extraction_prompt.txt` — Structured extraction prompt enforcing the complete JSON extraction schema.
- `ai/extraction.py` — Extraction pipeline orchestrator:
  - Maps LLM JSON output to `processed_feedback` fields.
  - Validates verbatim presence of `evidence_span` in the original text (zero hallucination check).
  - Differentiates `evidence_type` (`explicit` vs `inferred`).
  - Infers underlying Job-to-be-Done (`inferred_user_need`) with confidence score.

### 4.3 Extracted Schema Fields
- `user_intent`, `wishlist_reason`, `purchase_intent`
- `purchase_barrier`, `purchase_hesitation`, `purchase_postponement_reason`, `uncertainty_type`
- `decision_stage`, `behaviour_after_interest`, `comparison_behaviour`, `external_search_behaviour`
- `product_category`, `product_type`, `price_sensitivity`
- Boolean/Integer flags for: `fit_concern`, `size_concern`, `quality_concern`, `material_concern`, `styling_concern`, `occasion_concern`, `trust_concern`, `return_exchange_concern`, `availability_concern`
- `evidence_span`, `evidence_type`, `inferred_user_need`, `inference_confidence`

### 4.4 Acceptance Criteria & Verification
- [ ] Extracted JSON passes Pydantic schema validation.
- [ ] Evidence spans are strictly substrings of the original input text.
- [ ] Extracted records are batch-inserted into SQLite `processed_feedback`.

---

## Phase 5: Local BGE Vector Pipeline & Unsupervised Semantic Clustering

### 5.1 Objective
Embed processed text and inferred needs using a local BGE model, store vectors in ChromaDB, and perform unsupervised semantic clustering to discover emerging problem categories and build the dynamic 2-level problem taxonomy.

### 5.2 Chunking Strategy for BGE Model
The `BAAI/bge-small-en-v1.5` model has a strict context window of **512 tokens**. Based on data analysis, while YouTube comments are short (max ~450 chars), future inputs from Reddit and scraped Web Articles will significantly exceed this limit.
Therefore, a rigorous chunking strategy is necessary before embedding:
1. **Primary Embedding Unit**: Instead of embedding the full raw text (which might be noisy), embed the `evidence_span` + `inferred_user_need` combined. These are precisely extracted high-signal spans by the Groq LLM in Phase 4 and are guaranteed to be concise (typically < 100 words).
2. **Fallback / Long-Text Chunking**: If raw text embedding is needed, use `langchain.text_splitter.RecursiveCharacterTextSplitter` configured for semantic boundaries (split on `\n\n`, then `.` , then ` `).
   - Chunk Size: `350 tokens` (leaves room for system metadata prefixing like `"Represent this sentence for searching relevant passages: "`).
   - Chunk Overlap: `50 tokens` to preserve context across boundaries.

### 5.3 Embedding Strategy & Vector Space Design
Based on the chunking strategy, to maximize semantic retrieval quality (Phase 8 RAG) and clustering cohesion (Phase 5 HDBSCAN), the embeddings will follow this architecture:
1. **Model Selection**: `BAAI/bge-small-en-v1.5` (384-dimensional dense vectors) for rapid local CPU/GPU execution without external API dependencies.
2. **Composite Representation**: The chunks will be templated into a standardized string before embedding to capture both the symptom and the latent job-to-be-done. Format:
   `[Symptom]: {evidence_span} | [Underlying Need]: {inferred_user_need}`
3. **Instruction Prefixing**:
   - **Document Generation (Phase 5)**: Chunks are embedded *without* a prefix (standard BGE methodology for document indexing).
   - **Query Generation (Phase 8 RAG)**: Search queries will strictly prepend the instruction: `"Represent this sentence for searching relevant passages: "` to activate BGE's asymmetric retrieval weights.
4. **Metadata Enrichment for Hybrid Search**: Every vector stored in ChromaDB will include structured metadata (`purchase_barrier`, `uncertainty_type`, `decision_stage`, `source`, `relevance_score`) enabling strict pre-filtering before dense semantic distance calculation.

### 5.4 Files to Create
- `ai/embeddings.py` — Local embedding generator using `sentence-transformers` with `BAAI/bge-small-en-v1.5` (384-dimensional dense vectors).
- `vector/chroma_store.py` — Embedding indexing with metadata filtering (`feedback_id`, `source`, `category`, `barrier`).
- `ai/clustering.py` — Clustering & discovery engine:
  - HDBSCAN clustering on BGE embeddings to discover dense problem clusters and isolate outliers.
  - Fallback support for Agglomerative / K-Means clustering.
  - Centroid exemplar extraction and Groq-powered cluster labeling to generate `cluster_label`, `cluster_description`, and Level 1 / Level 2 taxonomy mappings.
  - Updates `problem_clusters` and links `processed_feedback.cluster_id`.

### 5.3 Acceptance Criteria & Verification
- [ ] Dense vectors are generated locally on CPU/GPU without external embedding API calls.
- [ ] ChromaDB collections (`feedback_embeddings`, `evidence_embeddings`) allow similarity queries with metadata filters.
- [ ] HDBSCAN identifies naturally occurring clusters without forcing uniform cluster sizes.
- [ ] Emerging problem themes are assigned meaningful Level 1/Level 2 taxonomy labels.

---

## Phase 6: Deterministic Quantification, Segmentation & Opportunity Engine

### 6.1 Objective
Compute all numerical metrics deterministically in pure SQL and Python (strictly prohibiting LLMs from doing math), perform multi-dimensional segmentation, and score opportunity areas for PM prioritization.

### 6.2 Files to Create
- `analysis/metrics.py` — Mathematical quantification engine:
  - **Frequency ($N$)**: Total occurrences per problem.
  - **Prevalence ($\%$)**: Proportion of total relevant feedback.
  - **Source Breadth**: Number of distinct sources exhibiting the problem ($1 \dots 4$).
  - **Explicit vs Inferred Rate**: Percentage directly stated vs inferred.
  - **Purchase Linkage Score**: Percentage explicitly tied to hesitation, postponement, or abandonment.
- `analysis/segmentation.py` — Segmentation engine:
  - Slices metrics across product categories (`Apparel`, `Footwear`, `Accessories`), price sensitivity (`Budget`, `Mid`, `Premium`), and decision stages.
  - Cross-analyzes session drop-off rates from `shopper_sessions` (`jlh/uci-shopper`).
- `analysis/opportunity.py` — Multi-dimensional Opportunity Prioritization Score ($0 - 100$):
  $$\text{Score} = w_1 \cdot \text{Prevalence} + w_2 \cdot \text{Linkage} + w_3 \cdot \text{SourceBreadth} + w_4 \cdot \text{ExplicitRate} + w_5 \cdot \text{Confidence}$$
  - Populates `cluster_metrics` and `opportunity_scores` in SQLite.

### 6.3 Acceptance Criteria & Verification
- [ ] All metrics match exact SQL counts and mathematical formulas.
- [ ] Opportunity ranking produces a deterministic ordered leaderboard ($0 - 100$).
- [ ] Segmentation breakdowns accurately partition data without missing records.

---

## Phase 7: Hybrid RAG & Natural Language PM Research Engine

### 7.1 Objective
Build a Hybrid RAG research engine that decomposes PM natural language questions into deterministic SQL analytics queries + ChromaDB semantic quote retrieval, synthesized by Groq into the standardized VoC research response format.

### 7.2 Files to Create
- `rag/retrieval.py` — Hybrid dual retriever:
  - Query Intent Router: Extracts structured filters (category, barrier, price tier) and generates SQL aggregation queries.
  - Semantic Retriever: Queries ChromaDB for verbatim user quotes and representative evidence.
- `prompts/research_prompt.txt` — Synthesis prompt grounding Groq strictly on retrieved SQL tables and quotes.
- `rag/research_engine.py` — Research synthesizer enforcing the mandatory response standard:
  - **Finding** (Concise discovery)
  - **Quantification** (Exact metrics: $N$, %, source breadth, linkage)
  - **Affected Segments** (Category and shopper profiles)
  - **Observed Behaviour** (Specific user actions)
  - **Representative Evidence** (Verbatim quotes with source citations)
  - **Confidence Level** (High / Medium / Low)
  - **Interpretation** (Wishlist-to-purchase implications)
  - **Contradictory Evidence** (Opposing behaviors observed)
  - **Remaining Unknowns & Hypotheses** (Questions needing first-party testing)

### 7.3 Acceptance Criteria & Verification
- [ ] PM queries return exact numerical statistics matching SQLite ground truth.
- [ ] Every response includes traceable verbatim quotes and source IDs.
- [ ] Contradictory evidence is surfaced rather than smoothed over.
- [ ] When evidence is sparse, the system explicitly responds: *"Insufficient evidence to conclude"*.

---

## Phase 8: Interactive Streamlit Presentation Dashboard

### 8.1 Objective
Build an interactive, multi-view Streamlit application providing Product Managers with executive discovery insights, problem deep-dives, decision journey funnel analytics, and an interactive VoC Research Assistant.

### 8.2 Files to Create
- `dashboard/app.py` — Streamlit application entrypoint with sidebar global filters (Source, Category, Date range, Intent depth).
- `dashboard/views/executive_view.py` — Executive Discovery:
  - KPI summary metrics (Total collected, relevant %, top discovered barriers).
  - Source and product category distribution charts.
  - Top Opportunity Prioritization Leaderboard.
- `dashboard/views/problem_explorer.py` — Problem Explorer:
  - Interactive 2-level taxonomy tree browser.
  - Drill-down metrics (prevalence, source breadth, explicit/inferred ratio).
  - Verbatim quote inspector with source badges and tags.
  - Contradictory evidence callouts.
- `dashboard/views/decision_journey.py` — Decision Journey:
  - Observed funnel flow: `Discover → Like → Wishlist → Revisit → Compare → Research → Hesitate → Outcome`.
  - Friction hotspot highlights and external research exit points.
  - Behavioral session analytics from `shopper_sessions` (`jlh/uci-shopper`: Informational duration vs revenue non-conversion).
- `dashboard/views/research_chat.py` — VoC Research Assistant:
  - Chat interface powered by the Hybrid RAG engine with pre-built PM question suggestions.

### 8.3 Acceptance Criteria & Verification
- [ ] Streamlit application launches cleanly via `streamlit run dashboard/app.py`.
- [ ] All 4 views render correctly and respond to global sidebar filters.
- [ ] Interactive charts (Plotly) display metrics accurately without lag.
- [ ] Chat interface generates grounded answers with quote citations.

---

## Phase 9: CLI Pipeline Orchestration & End-to-End Test Suite

### 9.1 Objective
Provide a unified CLI orchestrator to run individual phases or the full end-to-end pipeline, accompanied by an automated test suite.

### 9.2 Files to Create
- `main.py` — CLI entrypoint with argument parsing:
  - `--collect`: Run ingestion collectors.
  - `--clean`: Run cleaning and deduplication.
  - `--classify`: Run relevance classification.
  - `--extract`: Run structured LLM extraction.
  - `--cluster`: Run BGE embedding & HDBSCAN clustering.
  - `--quantify`: Compute metrics and opportunity scores.
  - `--dashboard`: Launch Streamlit dashboard.
  - `--all`: Execute full end-to-end pipeline.
- `tests/test_collectors.py` — Ingestion and schema normalization tests.
- `tests/test_cleaning.py` — Sanitization and exact/near deduplication tests.
- `tests/test_extraction.py` — Schema validation and quote span checks.
- `tests/test_metrics.py` — Deterministic mathematical formula validation.
- `tests/test_rag.py` — Hybrid retrieval and response formatting tests.

### 9.3 Acceptance Criteria & Verification
- [ ] `pytest tests/ -v` passes 100% with no regressions.
- [ ] `python main.py --all` executes the complete pipeline from raw ingestion to dashboard readiness.

---

## Summary Matrix of Project Phases

| Phase | Core Deliverables | Primary Technologies | Input $\rightarrow$ Output |
|---|---|---|---|
| **Phase 1** | Schema DDL, DB Context, Chroma Client | SQLite, ChromaDB, Python | Config $\rightarrow$ Initialized Databases |
| **Phase 2** | YouTube, HF, Serper, Reddit Collectors | YouTube API, Serper API, HF `datasets` | Public APIs/Datasets $\rightarrow$ `raw_feedback` & `shopper_sessions` |
| **Phase 3** | Text Sanitizer, Dedup, Relevance Classifier | Regex, MinHash, Groq LLM | `raw_feedback` $\rightarrow$ Cleaned & Scored Records (0–3) |
| **Phase 4** | Structured Extractor & Need Inference | Groq LLM (LLaMA 3.3 70B), Pydantic | Relevant Records $\rightarrow$ `processed_feedback` |
| **Phase 5** | Local BGE Embeddings, HDBSCAN Clustering | `sentence-transformers`, `hdbscan`, ChromaDB | Extracted Needs $\rightarrow$ `problem_clusters` & Taxonomy |
| **Phase 6** | Quantification & Opportunity Engine | Pandas, NumPy, SQL | `processed_feedback` $\rightarrow$ `cluster_metrics` & `opportunity_scores` |
| **Phase 7** | Hybrid RAG & PM Research Engine | SQL + ChromaDB + Groq LLM | Natural Language Query $\rightarrow$ Grounded VoC Response |
| **Phase 8** | Interactive Streamlit Dashboard (4 Views) | Streamlit, Plotly | SQLite + ChromaDB $\rightarrow$ Multi-View PM Web App |
| **Phase 9** | Pipeline CLI & Test Suite | Python `argparse`, `pytest` | Full System $\rightarrow$ Automated Verification & CLI |
