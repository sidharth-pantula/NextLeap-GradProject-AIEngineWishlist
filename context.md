# Context & Master Blueprint: AI-Powered Wishlist-to-Purchase Discovery Engine

## 0. Role and Objective
- **Role**: AI Product Engineer, Data Engineer, ML Engineer, and Product Analytics Engineer collaborating with a Product Manager on the Growth Team.
- **Environment**: Google Antigravity using Python.
- **Deliverable**: Technically credible, modular, working prototype (not a conceptual mockup).
- **Core Directive**: **Do NOT immediately propose product solutions.** The system is built to discover and understand the underlying user problems, barriers, and needs first.

---

## 1. Business Problem & Strategic Context
- **Observation**: Millions of users browse fashion products, save items they like, and build wishlists. A wishlist is a critical behavioral signal: the user has expressed explicit purchase interest but stopped short of checking out.
- **Problem**: Users accumulate dozens or hundreds of wishlisted items, but only a small fraction translate into completed purchases.
- **Strategic Goal**: Increase the percentage of users who purchase at least one item from their wishlist within 30 days of adding it.
- **Business Impact**:
  - Increase purchase frequency
  - Improve monetization from existing users
  - Extract value from existing high-intent demand
  - Reduce lost purchase intent
- **Constraints**:
  - The underlying user problem is currently unknown.
  - The eventual product solution cannot rely on monetary incentives (discounts, coupons, price cuts, loyalty rewards).
  - The system must discover what prevents users from converting wishlist interest into a purchase.

---

## 2. System Purpose
Transform unstructured publicly available user conversations into structured, evidence-backed discovery artifacts:
$$\text{Unstructured User Conversations} \longrightarrow \text{Structured Signals} \longrightarrow \text{Recurring Problems} \longrightarrow \text{User Needs} \longrightarrow \text{Purchase Barriers} \longrightarrow \text{Quantified Evidence} \longrightarrow \text{Segment Differences} \longrightarrow \text{Opportunity Areas} \longrightarrow \text{Testable Hypotheses}$$

### What the Engine IS:
- A Voice-of-Customer (VoC) Discovery and Research Engine.
- A tool for PMs to uncover root causes, uncertainties, comparison behaviors, and external information seeking.

### What the Engine IS NOT:
- NOT a product recommendation engine.
- NOT a discount/promotional engine.
- NOT a feature idea generator that jumps to conclusions.

---

## 3. Core Research Questions (PM Questions)

### Wishlist Behaviour
1. Why do users add fashion products to their wishlist?
2. What does a wishlist addition actually represent?
3. When is wishlist behaviour genuine purchase intent?
4. When is it merely bookmarking?
5. When is it shortlisting / comparison?
6. When is it price-waiting?
7. When is it future / occasion-based intent?

### Purchase Conversion & Barriers
8. What prevents wishlisted products from eventually being purchased?
9. What causes users to postpone purchases?
10. What causes users to abandon products?
11. What happens between wishlist creation and purchase/non-purchase?
12. What uncertainties remain after users identify a product they like?

### Decision-Making & Comparison
13. How do users compare multiple shortlisted products?
14. What makes users unable to decide between products?
15. What information do users need before committing?
16. What triggers confidence to purchase?

### External Information Seeking
17. What information do users seek outside the fashion platform?
18. Do they use Google, Reddit, YouTube, influencers, brand websites, competitors, or communities?
19. What information gaps cause users to leave the platform?

### Specific Problem Areas
20. What role do fit, size, quality, styling, price, reviews, occasion, trust, availability, and social validation play?
21. Which of these are actual purchase barriers versus merely common complaints?
22. What new problems emerge that were not anticipated in the initial taxonomy?

### Segmentation
23. How do these behaviours differ by product category (Apparel, Footwear, Accessories, etc.)?
24. How do they differ by user behaviour (high vs. low wishlist volume, high vs. low intent)?
25. How do frequent wishlist users differ from occasional wishlist users?
26. How do price-sensitive users differ from premium shoppers?

### Opportunity & Prioritization
27. What unmet needs emerge consistently?
28. Which problems have the strongest evidence?
29. Which problems have the strongest connection to purchase hesitation?
30. Which opportunity areas should the Product Manager investigate first?

---

## 4. Product-Analytics Epistemology Principle

The engine strictly enforces clear distinctions between:
1. **Observation**: What users explicitly state or what is directly observed in collected data (e.g., *"I am waiting for the sale"*).
2. **Hypothesis**: A plausible explanation or theory derived from observed patterns (e.g., *Some wishlist additions represent price-waiting rather than immediate intent*).
3. **Causal Claim**: A claim about actual metric impact (e.g., *Price waiting causes 30% of non-conversion*).
   - **Rule**: The public-feedback engine can establish observations and generate hypotheses. **It must NOT claim causality without first-party behavioral experimentation data.**

---

## 5. Technology Stack

| Layer | Tool / Library | Purpose |
|---|---|---|
| **Language** | Python 3.10+ | Core language across all components |
| **Development** | Google Antigravity | Development environment |
| **LLM Inference** | Groq API (`llama-3.3-70b-versatile` / compatible) | Relevance classification, structured extraction, need interpretation, cluster labeling, synthesis |
| **Embeddings** | Local BGE (`BAAI/bge-small-en-v1.5` or `bge-base-en-v1.5`) | Local embedding generation for feedback, evidence, queries, and clusters |
| **Vector DB** | ChromaDB (Local/Persistent) | Vector storage, metadata filtering, semantic retrieval for RAG |
| **Structured DB** | SQLite (in-house/local) | Relational store for raw feedback, processed feedback, clusters, metrics, segments, opportunities |
| **Analytics Engine** | Python, pandas, NumPy, SQL, scikit-learn | Deterministic metric calculation (frequencies, prevalence, ratios, scoring) |
| **Clustering** | HDBSCAN / Agglomerative / K-Means (scikit-learn / hdbscan) | Unsupervised semantic clustering on BGE embeddings |
| **Dashboard** | Streamlit | Executive Discovery, Problem Explorer, Decision Journey, Research Assistant |

---

## 6. High-Level Architecture & Pipeline Flow

```
[ Public Data Sources (YouTube, Reddit, App Reviews, Web) ]
                           ↓
[ Source-Specific Collectors / Loaders (collectors/) ]
                           ↓
[ Raw Data Store (SQLite: raw_feedback) ]
                           ↓
[ Cleaning, Normalization & Deduplication (processing/) ]
                           ↓
[ Relevance Filtering (Groq LLM: scores 0-3) ]
                           ↓
[ Structured Extraction & Need Inference (Groq LLM) ]
                           ↓
[ Local BGE Embedding Generation (ai/embeddings.py) ]
                           ↓
[ Semantic Clustering & Emerging Theme Discovery (ai/clustering.py) ]
                           ↓
[ 2-Level Dynamic Problem Taxonomy (Level 1 & Level 2) ]
                           ↓
[ Deterministic Quantification & Segmentation (Python / SQL) ]
                           ↓
[ Opportunity Scoring & Ranking (analysis/opportunity.py) ]
                           ↓
[ Storage: SQLite + Local ChromaDB Vector Collections ]
                           ↓
[ Hybrid RAG Engine: SQL Metrics + ChromaDB Evidence + Groq Synthesis ]
                           ↓
[ Streamlit Interactive Research Dashboard & VoC Assistant ]
```

---

## 7. Data Sources & Ingestion Specifications

All data collection must be automated via code. Manual copy-pasting of reviews is strictly prohibited.

### A. YouTube (YouTube Data API v3)
- **Queries**: Search brand-agnostic shopping behaviors and platform experiences (*"Myntra shopping experience"*, *"online fashion fit problems"*, *"clothing haul sizing issues"*, *"Myntra wishlist"*, *"how to choose clothes online"*, etc.).
- **Capabilities**: Video search, metadata extraction, comment thread retrieval, pagination, rate limit handling, duplicate detection, normalized storage.

### B. Reddit
- **Method**: Official Reddit API (via PRAW/OAuth) or ingestion of legitimate public Reddit datasets (`.json`, `.csv`, `.parquet`).
- **Topics**: r/IndianFashionAddicts, r/TwoXIndia, r/mumbai, r/bangalore, r/india shopping threads, sizing/fit discussions, sales waiting.

### C. Hugging Face Datasets (`datasets` / Parquet / JSON)
- **Datasets**:
  - **`jlh/uci-shopper` (UCI Online Shoppers Purchasing Intention Dataset)**: 12,330 e-commerce sessions with attributes including page visits (`Administrative`, `Informational`, `ProductRelated` durations), `BounceRates`, `ExitRates`, `PageValues`, `VisitorType` (`Returning_Visitor` vs `New_Visitor`), `Month`, `SpecialDay`, and conversion outcome (`Revenue` True/False).
  - **Fashion & Review Datasets**: Additional e-commerce customer feedback and review datasets on sizing, quality, and hesitation.
- **Role in Engine**:
  - Provides empirical session-level ground truth to validate qualitative VoC hypotheses.
  - Links behavioral signals (e.g., high informational/comparison duration leading to bounce/exit without revenue) to discovered purchase barriers.
- **Capabilities**: Batch streaming via Hugging Face `datasets` API, local caching, schema mapping to normalized session and feedback stores.

### D. Public Web & Fashion Communities (Serper API)
- **Method**: Use Serper Google Search API (`SERPER_API_KEY`) to discover and query public forum threads, discussions, blogs, and community pages (e.g., Reddit threads, Quora, fashion blogs, shopping guides) on shopping hesitation, sizing, and wishlist behavior.
- **Capabilities**: Structured search queries, organic results snippet extraction, discussion/forum discovery, metadata parsing, and compliant text ingestion.

---

## 8. Common Data Schemas

### A. Normalized Raw Feedback Schema (`raw_feedback`)
All collectors must normalize output to this schema:
- `feedback_id` (TEXT, PK): Unique deterministic ID (e.g., hash or source-prefixed UUID)
- `source` (TEXT): `youtube`, `reddit`, `huggingface`, `web`
- `source_type` (TEXT): `comment`, `post`, `review`, `article`
- `source_id` (TEXT): Native platform ID
- `date` (TEXT / ISO-8601): Publication timestamp
- `text` (TEXT): Raw unmodified text
- `title` (TEXT, Nullable): Thread/video/post title
- `url` (TEXT, Nullable): Direct URL
- `product` (TEXT, Nullable): Specific product/brand mentioned
- `category` (TEXT, Nullable): Inferred or tagged category
- `rating` (FLOAT, Nullable): Star rating if available
- `engagement` (INTEGER, Nullable): Upvotes, likes, reply count
- `metadata` (JSON/TEXT): Source-specific attributes
- `collection_timestamp` (TEXT / ISO-8601): Ingestion timestamp

### B. LLM Structured Extraction Schema (`processed_feedback`)
- `feedback_id` (TEXT, FK)
- `relevance_score` (INTEGER): 0 (Irrelevant), 1 (Peripheral), 2 (Relevant), 3 (Highly Relevant)
- `relevance_reason` (TEXT)
- `relevance_confidence` (FLOAT)
- `user_intent` (TEXT): Broad user goal
- `wishlist_reason` (TEXT): Wishlist intent classification
- `purchase_intent` (TEXT): `high`, `medium`, `low`, `none`
- `purchase_barrier` (TEXT): Primary barrier observed
- `purchase_hesitation` (TEXT): Specific hesitation trigger
- `purchase_postponement_reason` (TEXT): Reason for delay
- `uncertainty_type` (TEXT): `fit`, `size`, `quality`, `material`, `price`, `authenticity`, `appearance`, `styling`
- `information_needed` (TEXT): What user sought
- `decision_stage` (TEXT): `discovery`, `initial_interest`, `wishlist`, `revisit`, `comparison`, `research`, `hesitation`, `postponement`, `abandonment`, `purchase`
- `behaviour_after_interest` (TEXT)
- `comparison_behaviour` (TEXT)
- `external_search_behaviour` (TEXT): What they searched outside the platform
- `competitor_behaviour` (TEXT)
- `purchase_outcome` (TEXT): `purchased`, `postponed`, `abandoned`, `switched_platform`, `undecided`
- `product_category` (TEXT): `apparel`, `footwear`, `accessories`, `beauty`, `other`
- `product_type` (TEXT)
- `price_sensitivity` (TEXT): `high`, `medium`, `low`
- `fit_concern` (BOOLEAN/TEXT)
- `size_concern` (BOOLEAN/TEXT)
- `quality_concern` (BOOLEAN/TEXT)
- `material_concern` (BOOLEAN/TEXT)
- `styling_concern` (BOOLEAN/TEXT)
- `occasion_concern` (BOOLEAN/TEXT)
- `review_concern` (BOOLEAN/TEXT)
- `social_validation_need` (BOOLEAN/TEXT)
- `trust_concern` (BOOLEAN/TEXT)
- `availability_concern` (BOOLEAN/TEXT)
- `return_exchange_concern` (BOOLEAN/TEXT)
- `user_segment_signals` (TEXT/JSON)
- `evidence_strength` (TEXT): `strong`, `moderate`, `weak`
- `evidence_span` (TEXT): Exact quote from raw text
- `evidence_type` (TEXT): `explicit` vs `inferred`
- `inferred_user_need` (TEXT): Underlying job-to-be-done / need
- `inference_confidence` (FLOAT)

---

## 9. Taxonomies

### A. Initial Wishlist Intent Taxonomy
1. `immediate_purchase_intent`: High intent, planning to buy quickly
2. `future_purchase_intent`: Intent to buy at an unspecified future date
3. `price_waiting`: Waiting for price drops, sales, or coupons
4. `comparison_shortlisting`: Saving 2+ options to decide later
5. `bookmarking`: Passive saving / personal visual catalog
6. `aspirational_interest`: Desire with low likelihood of buying (luxury / out-of-budget)
7. `occasion_planning`: Specific future event (wedding, festival, vacation)
8. `availability_monitoring`: Waiting for size or color restock
9. `social_style_inspiration`: Outfit matching / aesthetic board
10. `unknown` / `discovered_theme`: New cluster discovered dynamically

### B. Purchase Barrier Taxonomy (2-Level Hierarchy)
- **Level 1: Product Uncertainty**
  - Level 2: Fit, Size ambiguity, Material feel, Quality durability, Color mismatch, Actual appearance vs. studio photo, Authenticity
- **Level 1: Price & Timing**
  - Level 2: Waiting for sale/discount, Price comparison shock, Perceived value uncertainty, Payday timing, Occasion timing
- **Level 1: Availability & Logistics**
  - Level 2: Specific size out of stock, Out of stock entirely, Pincode delivery limitations, Restock uncertainty
- **Level 1: Decision Complexity**
  - Level 2: Choice overload (too many similar options), Inability to compare spec-by-spec, Lack of clear recommendations
- **Level 1: Trust & Post-Purchase Anxiety**
  - Level 2: Seller credibility, Fake review suspicion, Return & exchange friction / fees, Refund delays
- **Level 1: Styling & Social Validation**
  - Level 2: Wardrobe suitability (how to style), Occasion fit, Seeking peer/social approval
- **Level 1: Shopping Friction**
  - Level 2: Cluttered UI, Broken filters, Checkout friction

---

## 10. Quantification & Analytical Metrics Engine

All metrics must be computed deterministically via SQL/Python (never fabricated by an LLM).

| Metric | Definition |
|---|---|
| **Frequency ($N$)** | Count of relevant feedback items exhibiting the problem |
| **Prevalence ($\%$)** | $\frac{\text{Problem Count}}{\text{Total Relevant Feedback}} \times 100$ |
| **Source Breadth** | Number of distinct source channels where problem appears ($1 \dots 4$) |
| **Explicit Evidence Rate** | $\frac{\text{Explicit Mentions}}{\text{Total Mentions of Problem}} \times 100$ |
| **Inferred Evidence Rate** | $\frac{\text{Inferred Mentions}}{\text{Total Mentions of Problem}} \times 100$ |
| **Purchase Linkage Score** | Proportion of problem occurrences explicitly linked to hesitation, postponement, or abandonment |
| **Segment Concentration** | Breakdown across product categories (Apparel vs. Footwear) and price tiers |
| **Trend / Recency** | Distribution over time intervals |

### Opportunity Scoring Framework
A deterministic scoring composite ($0 - 100$) for PM prioritization:
$$\text{Opportunity Score} = f(\text{Prevalence}, \text{User Intensity}, \text{Purchase Linkage}, \text{Source Breadth}, \text{Evidence Confidence})$$
*Note: Strictly presented as a "Discovery / Prioritization Score", NOT a guaranteed causal conversion lift.*

---

## 11. Hybrid RAG & Natural Language Research Engine

### Architecture
1. **PM Query Understanding**: Dissects natural language query into quantitative metrics needed + semantic topics.
2. **Deterministic SQL Query**: Extracts exact counts, prevalence percentages, segment distributions from SQLite.
3. **ChromaDB Semantic Retrieval**: Retrieves representative evidence snippets and raw quotes using BGE embeddings with metadata filtering.
4. **Groq LLM Synthesis**: Synthesizes the quantitative tables and qualitative quotes into the standardized research response format.

### Mandatory Research Response Format
Every substantive response must include:
- **Finding**: Clear, concise discovery insight.
- **Quantification**: Exact frequency, prevalence, source breadth, and linkage metrics.
- **Affected Segments**: Categories, price tiers, and user types most impacted.
- **Observed Behaviour**: What users actually do (steps taken, external searches).
- **Representative Evidence**: Direct quotes with source attribution.
- **Confidence Level**: High / Medium / Low (based on sample size and cross-source consistency).
- **Interpretation**: Potential implications for wishlist-to-purchase behavior.
- **Contradictory Evidence**: Opposing user behaviors observed in data.
- **Remaining Unknowns / Hypotheses**: Testable hypotheses and what still requires first-party product experimentation.

---

## 12. Streamlit Dashboard Architecture

The dashboard comprises 4 primary modules:
1. **Executive Discovery**: High-level KPIs (total collected, relevant %, source breakdown, top 5 discovered barriers, emerging themes, top opportunity areas).
2. **Problem Explorer**: In-depth filterable analysis per problem cluster (prevalence, source breadth, verbatim quotes, category breakdown, contradictory signals).
3. **Decision Journey**: Visual map of the shopping path (`Discover → Like → Wishlist → Revisit → Compare → Research → Hesitate → Outcome`) with friction points highlighted.
4. **Research Assistant**: Natural language Q&A interface powered by the Hybrid RAG engine with evidence tracing.

---

## 13. Source Bias & Reliability Safeguards

- **Reddit Bias**: Overrepresents vocal, highly engaged power shoppers.
- **App Reviews Bias**: Skewed towards extreme negative bugs/shipping issues or short 5-star praise.
- **YouTube Comments Bias**: Influenced by specific video topics and creator style.
- **Product Reviews Bias**: Skewed towards buyers who completed purchase; blind to non-converting abandoners.
- **Safeguards**:
  - Never equate raw source frequency directly to total customer base prevalence without noting source distribution.
  - Require cross-source validation for high-confidence findings.
  - Distinctly tag `explicit` vs `inferred` evidence.
  - Explicitly output "Insufficient evidence to conclude" when data is sparse.
  - Zero hallucination policy: quotes and numbers must originate strictly from the database.

---

## 14. Project Directory Structure

```
AIwishlistDiscoveryEngine/
├── collectors/
│   ├── __init__.py
│   ├── youtube_collector.py      # YouTube Data API v3 collector
│   ├── reddit_collector.py       # Reddit API / public dataset loader
│   ├── hf_dataset_loader.py      # Hugging Face datasets & local files loader
│   └── web_collector.py          # Public web community collector (Serper)
├── data/
│   ├── raw/                      # Raw ingested datasets / backups
│   └── processed/                # Normalized cache files
├── database/
│   ├── __init__.py
│   ├── schema.py                 # SQLite schema definitions
│   └── db.py                     # DB connection and queries
├── processing/
│   ├── __init__.py
│   ├── cleaning.py               # Text cleaning, normalization
│   ├── deduplication.py          # Exact & near-duplicate detection
│   └── relevance.py              # Groq relevance classifier (0-3)
├── ai/
│   ├── __init__.py
│   ├── groq_client.py            # Groq API client with rate-limiting & retries
│   ├── extraction.py             # Structured schema extraction
│   ├── embeddings.py             # Local BGE model wrapper
│   └── clustering.py             # HDBSCAN / KMeans semantic clustering
├── analysis/
│   ├── __init__.py
│   ├── metrics.py                # Deterministic calculation engine
│   ├── segmentation.py           # Slice-and-dice by category/price/intent
│   └── opportunity.py            # Multi-dimensional opportunity scoring
├── vector/
│   ├── __init__.py
│   └── chroma_store.py           # ChromaDB collection management
├── rag/
│   ├── __init__.py
│   ├── retrieval.py              # Hybrid SQL + Vector retriever
│   └── research_engine.py        # PM Q&A synthesis engine
├── dashboard/
│   └── app.py                    # Streamlit multi-page interface
├── prompts/
│   ├── relevance_prompt.txt      # Prompt template for scoring
│   ├── extraction_prompt.txt     # Prompt template for extraction
│   └── research_prompt.txt       # Prompt template for synthesis
├── tests/                        # Unit and integration tests
├── .env.example
├── .gitignore
├── requirements.txt
├── main.py                       # Orchestration entrypoint
```

### 14.1 Environment Configuration & API Keys
```env
# LLM Inference
GROQ_API_KEY=your_groq_api_key

# Video & Comment Ingestion
YOUTUBE_API_KEY=your_youtube_data_api_v3_key

# Public Web Search & Forum Discovery (Serper)
SERPER_API_KEY=your_serper_api_key

# Optional Reddit API (if using live API instead of public dataset)
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
REDDIT_USER_AGENT=WishlistDiscoveryEngine/1.0

# Optional Hugging Face Token (if accessing gated/private datasets)
HF_TOKEN=your_huggingface_token
```

---

## 15. Phased Implementation Roadmap

- **Phase 1: Project Setup & Storage Foundation**
  - Virtual environment, dependencies, `.env`, SQLite schema (`database/schema.py`, `database/db.py`), local ChromaDB setup (`vector/chroma_store.py`).
- **Phase 2: YouTube Ingestion Pipeline (First Milestone)**
  - YouTube Data API collector, error handling, pagination, deduplication, raw SQLite storage.
- **Phase 3: Multi-Source Loaders (Hugging Face & Reddit)**
  - Hugging Face datasets loader (`collectors/hf_dataset_loader.py`) for fashion/shopping/wishlist reviews, Reddit loader, schema normalization.
- **Phase 4: Data Cleaning & Relevance Filtering**
  - Noise removal, exact/near deduplication, Groq-based relevance scoring (0-3).
- **Phase 5: Structured Extraction & Evidence Tracking**
  - Groq structured extractor, JSON parsing, explicit quote span preservation, user need inference.
- **Phase 6: Local BGE Embedding Pipeline**
  - Ingestion into local BGE embedding model, persistence into ChromaDB collections.
- **Phase 7: Semantic Clustering & Problem Discovery**
  - HDBSCAN / clustering on embeddings, cluster labeling, emerging problem taxonomy generation.
- **Phase 8: Quantification & Segmentation Engine**
  - Deterministic SQL/Python metrics (prevalence, linkage, source breadth, category slices).
- **Phase 9: Opportunity Scoring Engine**
  - Composite prioritization formula, ranking, confidence weights.
- **Phase 10: Hybrid RAG & PM Research Engine**
  - Hybrid retrieval (SQL metrics + ChromaDB vectors), Groq synthesis with mandatory response format.
- **Phase 11: Streamlit Research Dashboard**
  - 4 views: Executive Discovery, Problem Explorer, Decision Journey, Research Assistant.
