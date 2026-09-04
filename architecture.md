# Technical Architecture & System Design Document
## AI-Powered Voice-of-Customer (VoC) Wishlist-to-Purchase Discovery Engine

---

## 1. Executive Summary & Design Principles

The **AI-Powered Wishlist-to-Purchase Discovery Engine** is a specialized analytical platform designed to uncover the latent friction points, uncertainties, comparison behaviors, and unmet user needs that prevent e-commerce fashion shoppers from converting wishlisted products into completed purchases within 30 days.

```
+--------------------------------------------------------------------------------------------------+
|                                    CORE EPISTEMIC MANDATE                                        |
|  1. Observations != Hypotheses != Causal Claims                                                 |
|  2. LLMs are used for extraction, semantic synthesis, and interpretation — NEVER for math.       |
|  3. All metrics (prevalence, frequencies, rankings) are deterministically computed in SQL/Python.|
|  4. No monetary solution bias: Discover root customer problems first.                            |
+--------------------------------------------------------------------------------------------------+
```

### Core Architectural Principles
1. **Source Agnostic Downstream Processing**: Ingestion modules normalize all disparate sources into a strictly typed `raw_feedback` schema. All downstream AI, vector, and analytical modules operate purely on normalized records.
2. **Epistemic Traceability**: Every insight, metric, and problem cluster must trace back to verbatim user quotes, source IDs, explicit vs. inferred categorization, and confidence scores.
3. **Hybrid RAG (Analytical + Vector)**: Semantic vector retrieval provides qualitative context, while direct SQL execution provides deterministic statistical ground truth.
4. **Unsupervised Emerging Theme Discovery**: The system does not force feedback into rigid pre-defined buckets; HDBSCAN clustering on local BGE embeddings discovers emergent themes dynamically.
5. **Local-First & Resource Efficient**: Local BGE embedding models and local ChromaDB/SQLite stores eliminate recurring embedding API costs and cloud vendor lock-in.

---

## 2. End-to-End System Architecture

```mermaid
flowchart TD
    subgraph Data_Sources["Data Ingestion Layer"]
        YT["YouTube Data API v3<br/>(youtube_collector.py)"]
        RD["Reddit Ingestion<br/>(reddit_collector.py)"]
        HF["Hugging Face Datasets<br/>(hf_dataset_loader.py)"]
        WEB["Serper Web/Forum Search<br/>(web_collector.py)"]
    end

    subgraph Raw_Store["Storage Layer (Raw)"]
        RAW_DB[("SQLite: raw_feedback")]
    end

    subgraph Processing_Pipeline["Processing & AI Intelligence Pipeline"]
        CLEAN["Cleaning & Normalization<br/>(cleaning.py)"]
        DEDUP["Exact & Near Deduplication<br/>(deduplication.py)"]
        REL["Relevance Classifier 0-3<br/>(Groq LLM / relevance.py)"]
        EXT["Structured Schema Extractor<br/>(Groq LLM / extraction.py)"]
        NEED["User Need Inference & Quotes<br/>(Groq LLM / extraction.py)"]
    end

    subgraph ML_Vector["ML & Semantic Discovery Layer"]
        BGE["Local BGE Embeddings<br/>(BAAI/bge-small-en-v1.5)"]
        CHROMA[("ChromaDB Vector Store<br/>(chroma_store.py)")]
        CLUST["Semantic Clustering<br/>(HDBSCAN / KMeans / clustering.py)"]
        TAX["Dynamic 2-Level Taxonomy<br/>(Problem Discovery)"]
    end

    subgraph Analytics_Engine["Deterministic Analytics Engine"]
        METRICS["Quantification Metrics<br/>(Frequency, Prevalence, Linkage)"]
        SEG["Segmentation Engine<br/>(Category, Price, Intent Slices)"]
        OPP["Opportunity Prioritization<br/>(Multi-Dimensional Scoring)"]
    end

    subgraph Processed_Store["Storage Layer (Analytical & Vector)"]
        PROC_DB[("SQLite Analytics Tables<br/>(processed_feedback, clusters, metrics, opportunities)")]
    end

    subgraph Hybrid_RAG["Hybrid RAG & Research Engine"]
        QUERY_DEC["PM Query Decomposition<br/>(retrieval.py)"]
        SQL_EXEC["Deterministic SQL Analytics Query"]
        VEC_RET["Semantic Evidence & Quote Retrieval"]
        SYNTH["Groq LLM Synthesis<br/>(research_engine.py)"]
    end

    subgraph Presentation["Streamlit Interface Layer"]
        DASH_EXEC["1. Executive Discovery View"]
        DASH_EXPL["2. Problem Explorer View"]
        DASH_JOUR["3. Decision Journey View"]
        DASH_CHAT["4. VoC Research Assistant Chat"]
    end

    YT --> RAW_DB
    RD --> RAW_DB
    HF --> RAW_DB
    WEB --> RAW_DB

    RAW_DB --> CLEAN
    CLEAN --> DEDUP
    DEDUP --> REL
    REL -->|Score >= 2| EXT
    EXT --> NEED

    NEED --> BGE
    BGE --> CHROMA
    BGE --> CLUST
    CLUST --> TAX
    TAX --> METRICS

    NEED --> PROC_DB
    TAX --> PROC_DB
    METRICS --> SEG --> OPP --> PROC_DB

    QUERY_DEC --> SQL_EXEC --> PROC_DB
    QUERY_DEC --> VEC_RET --> CHROMA
    SQL_EXEC --> SYNTH
    VEC_RET --> SYNTH

    PROC_DB --> DASH_EXEC
    PROC_DB --> DASH_EXPL
    PROC_DB --> DASH_JOUR
    SYNTH --> DASH_CHAT
```

---

## 3. Data Ingestion Subsystem

The Ingestion layer adopts a unified `BaseCollector` interface to decouple specific data protocols from database storage.

```mermaid
classDiagram
    class BaseCollector {
        <<abstract>>
        +collect() List[RawFeedbackRecord]
        +normalize(raw_record) RawFeedbackRecord
        +save_to_db(records) int
    }
    class YouTubeCollector {
        -api_key: str
        -search_queries: List[str]
        +search_videos()
        +fetch_comments()
    }
    class RedditCollector {
        -client_id: str
        -client_secret: str
        +load_from_api()
        +load_from_dataset()
    }
    class HFDatasetLoader {
        -dataset_name: str
        -split: str
        +stream_and_map()
        +load_local_file()
    }
    class WebSerperCollector {
        -serper_api_key: str
        +search_queries: List[str]
        +query_snippets_and_forums()
    }

    BaseCollector <|-- YouTubeCollector
    BaseCollector <|-- RedditCollector
    BaseCollector <|-- HFDatasetLoader
    BaseCollector <|-- WebSerperCollector
```

### Ingestion Components & Strategies
1. **`YouTubeCollector` (`collectors/youtube_collector.py`)**:
   - Uses YouTube Data API v3.
   - Searches behavior-centric queries (e.g., *"Myntra haul sizing issue"*, *"online clothes purchase hesitation"*, *"AJIO quality review"*).
   - Paginates top-level comment threads and replies, extracts metadata (likes, dates, author).
2. **`HFDatasetLoader` (`collectors/hf_dataset_loader.py`)**:
   - Ingests **`jlh/uci-shopper`** (UCI Online Shoppers Purchasing Intention Dataset with 12,330 sessions) containing quantitative session duration (`Informational_Duration`, `ProductRelated_Duration`), `BounceRates`, `ExitRates`, `VisitorType`, and `Revenue` outcomes.
   - Ingests complementary fashion e-commerce customer feedback and review datasets.
   - Maps review text to `raw_feedback` and structured session logs to `shopper_sessions` table in SQLite.
3. **`WebSerperCollector` (`collectors/web_collector.py`)**:
   - Queries Google Search index via Serper API (`SERPER_API_KEY`) for Indian fashion discussions, reddit forum threads, and buyer hesitation articles.
   - Parses organic search snippets and deep forum posts.
4. **`RedditCollector` (`collectors/reddit_collector.py`)**:
   - Ingests public Reddit submissions and comments from subreddits (`r/IndianFashionAddicts`, `r/TwoXIndia`, `r/india`) via OAuth API or pre-collected dumps.

---

## 4. Processing, Relevance & AI Extraction Pipeline

```mermaid
sequenceDiagram
    autonumber
    participant Raw as SQLite (raw_feedback)
    participant Pipe as Pipeline Orchestrator
    participant Groq as Groq API (LLM)
    participant BGE as Local BGE Embeddings
    participant Chroma as ChromaDB
    participant DB as SQLite (Analytical)

    Pipe->>Raw: Fetch uncleaned raw records
    Pipe->>Pipe: Clean text & Deduplicate (Hash + MinHash)
    
    loop For Each Cleaned Record
        Pipe->>Groq: Relevance Classification Prompt (Score 0-3)
        Groq-->>Pipe: {score: 3, reason: "...", confidence: 0.95}
        
        alt Score >= 2 (Relevant / Highly Relevant)
            Pipe->>Groq: Structured Extraction & Need Inference Prompt
            Groq-->>Pipe: Extracted JSON (intent, barrier, uncertainty, quote_span)
            Pipe->>BGE: Generate 384d Dense Vector for text & need
            BGE-->>Pipe: Embedding Vector
            Pipe->>Chroma: Upsert vector + metadata (id, category, barrier)
            Pipe->>DB: Insert processed_feedback record
        else Score < 2 (Irrelevant / Peripheral)
            Pipe->>DB: Log non-relevant record status
        end
    end
```

### 1. Cleaning & Deduplication (`processing/cleaning.py`, `deduplication.py`)
- **Cleaning**: Strips broken HTML entities, emojis/control characters, promotional URLs, spam bots, and malformed encoding.
- **Exact Deduplication**: SHA-256 hash of normalized text.
- **Near Deduplication**: MinHash / Levenshtein distance matching for copied cross-posts and multi-platform promotional spam.

### 2. Relevance Classification (`processing/relevance.py`)
Classifies feedback on a strict 4-level scale using Groq LLM:
- `0 (Irrelevant)`: Spam, random text, non-fashion, bot output.
- `1 (Peripheral)`: General fashion chit-chat without decision-making context.
- `2 (Relevant)`: Discusses online fashion shopping, fit, sizing, quality, returns, or price perceptions.
- `3 (Highly Relevant)`: Explicitly discusses wishlist behavior, hesitation, postponement, cart abandonment, product comparison, or external research.

### 3. Structured Information Extraction (`ai/extraction.py`)
For all records with `relevance_score >= 2`, Groq extracts a strictly typed, nullable JSON object containing:
- **Intent**: `user_intent`, `wishlist_reason`, `purchase_intent`
- **Barriers & Friction**: `purchase_barrier`, `purchase_hesitation`, `purchase_postponement_reason`, `uncertainty_type`
- **Behavioral Indicators**: `decision_stage`, `behaviour_after_interest`, `comparison_behaviour`, `external_search_behaviour`
- **Specific Concerns (Flags)**: `fit_concern`, `size_concern`, `quality_concern`, `material_concern`, `styling_concern`, `trust_concern`, `return_exchange_concern`, `price_sensitivity`
- **Evidence Provenance**: `evidence_span` (verbatim substring), `evidence_type` (`explicit` vs `inferred`), `inferred_user_need`, `inference_confidence`

---

## 5. Machine Learning, Embeddings & Clustering Architecture

```mermaid
flowchart LR
    subgraph Embedding_Generation
        TEXT["Processed Text & Inferred Needs"] --> BGE_MOD["Local BGE Model<br/>(BAAI/bge-small-en-v1.5)"]
        BGE_MOD --> DENSE_VEC["384-dimensional Vectors"]
    end

    subgraph Vector_Indexing
        DENSE_VEC --> CHROMA_STORE[("ChromaDB Collections<br/>- feedback<br/>- evidence<br/>- user_needs")]
    end

    subgraph Unsupervised_Discovery
        DENSE_VEC --> UMAP_RED["Dimensionality Reduction<br/>(UMAP / PCA optional)"]
        UMAP_RED --> HDBSCAN_CLUST["HDBSCAN Clustering<br/>(Density-Based Discovery)"]
        HDBSCAN_CLUST --> OUTLIERS["Outliers / Emerging Themes"]
        HDBSCAN_CLUST --> DENSE_CLUST["Core Problem Clusters"]
        DENSE_CLUST --> GROQ_LABEL["Groq LLM Cluster Labeling"]
        GROQ_LABEL --> TAXONOMY["Dynamic 2-Level Problem Taxonomy"]
    end
```

### Embedding Pipeline (`ai/embeddings.py`)
- Model: `BAAI/bge-small-en-v1.5` (Fast, lightweight 384-dimensional dense vectors running locally on CPU/GPU via `sentence-transformers`).
- Consistency: Same embedding model applied across feedback items, evidence spans, search queries, and cluster representations.

### Semantic Clustering & Problem Discovery (`ai/clustering.py`)
1. **Clustering Engine**: HDBSCAN (Hierarchical Density-Based Spatial Clustering of Applications with Noise) as primary algorithm, with Agglomerative / K-Means as fallbacks.
2. **Noise Isolation**: Isolates natural outliers without forcing random noise into predefined clusters.
3. **Automated Cluster Labeling**: Groq analyzes representative centroid exemplars per cluster to produce:
   - `cluster_label` (Concise naming)
   - `cluster_description` (Root cause synthesis)
   - `level_1_category` & `level_2_category` assignment
   - `sub_themes`

---

## 6. Deterministic Quantification, Segmentation & Opportunity Engine

The analytics engine operates strictly on deterministic SQL queries and Pandas operations.

```mermaid
flowchart TD
    subgraph Data_Inputs
        DB_PROC[("processed_feedback")]
        DB_CLUST[("problem_clusters")]
    end

    subgraph Metrics_Calculation["Deterministic Metrics Engine (metrics.py)"]
        F1["Frequency (N) = Count of occurrences"]
        F2["Prevalence (%) = N / Total_Relevant * 100"]
        F3["Source Breadth = Count(DISTINCT source)"]
        F4["Explicit Rate = N_explicit / N * 100"]
        F5["Linkage Score = N_hesitated_or_abandoned / N * 100"]
    end

    subgraph Segmentation_Engine["Segmentation Engine (segmentation.py)"]
        S1["Product Category Breakdown (Apparel vs Footwear vs Accessories)"]
        S2["Price Sensitivity (Budget vs Mid vs Premium)"]
        S3["Intent Depth (High vs Low Intent)"]
    end

    subgraph Opportunity_Framework["Opportunity Scoring (opportunity.py)"]
        OPP_FORM["Composite Formula (0 - 100):<br/>Score = 0.25*Prevalence + 0.25*Linkage + 0.20*SourceBreadth + 0.15*ExplicitRate + 0.15*Intensity"]
    end

    DB_PROC --> Metrics_Calculation
    DB_CLUST --> Metrics_Calculation
    Metrics_Calculation --> Segmentation_Engine
    Segmentation_Engine --> Opportunity_Framework
    Opportunity_Framework --> DB_OUT[("SQLite metrics & opportunities tables")]
```

### Quantification Mathematical Formulas

$$\text{Prevalence}(P) = \left( \frac{\sum_{i \in \text{Relevant}} \mathbb{I}(i \in P)}{|\text{Relevant Feedback}|} \right) \times 100$$

$$\text{Source Breadth}(P) = |\text{Unique Sources}(P)| \quad \text{where } \text{Sources} \in \{\text{youtube}, \text{reddit}, \text{huggingface}, \text{web}\}$$

$$\text{Explicit Rate}(P) = \left( \frac{\sum_{i \in P} \mathbb{I}(\text{evidence\_type} = \text{'explicit'})}{|P|} \right) \times 100$$

$$\text{Purchase Linkage Score}(P) = \left( \frac{\sum_{i \in P} \mathbb{I}(\text{outcome} \in \{\text{'postponed'}, \text{'abandoned'}, \text{'hesitated'}\})}{|P|} \right) \times 100$$

$$\text{Opportunity Score}(P) = w_1 \cdot \widetilde{\text{Prev}} + w_2 \cdot \widetilde{\text{Link}} + w_3 \cdot \widetilde{\text{Breadth}} + w_4 \cdot \widetilde{\text{Expl}} + w_5 \cdot \widetilde{\text{Conf}}$$

*Note: All weights $w_i$ sum to 1.0, generating a normalized score between 0 and 100 for PM roadmap prioritization.*

---

## 7. Storage Architecture & Relational Schemas

```mermaid
erDiagram
    raw_feedback ||--o| processed_feedback : "1 to 1"
    processed_feedback }o--|| problem_clusters : "belongs to"
    processed_feedback ||--o{ evidence_records : "contains"
    problem_clusters ||--o{ cluster_metrics : "quantified by"
    problem_clusters ||--o| opportunity_scores : "ranked by"

    raw_feedback {
        text feedback_id PK
        text source
        text source_type
        text source_id
        text date
        text text
        text title
        text url
        text product
        text category
        real rating
        integer engagement
        text metadata_json
        text collection_timestamp
    }

    processed_feedback {
        text feedback_id PK, FK
        integer relevance_score
        text relevance_reason
        real relevance_confidence
        text user_intent
        text wishlist_reason
        text purchase_intent
        text purchase_barrier
        text purchase_hesitation
        text purchase_postponement_reason
        text uncertainty_type
        text decision_stage
        text purchase_outcome
        text product_category
        text price_sensitivity
        text evidence_span
        text evidence_type
        text inferred_user_need
        real inference_confidence
        integer cluster_id FK
        text processing_timestamp
    }

    problem_clusters {
        integer cluster_id PK
        text level_1_category
        text level_2_category
        text cluster_label
        text cluster_description
        integer cluster_size
        text representative_quote
        real confidence_score
    }

    cluster_metrics {
        integer metric_id PK
        integer cluster_id FK
        integer frequency
        real prevalence_pct
        integer source_breadth
        real explicit_evidence_rate
        real purchase_linkage_score
        text segment_breakdown_json
        text calculation_timestamp
    }

    opportunity_scores {
        integer opportunity_id PK
        integer cluster_id FK
        real opportunity_score
        integer priority_rank
        text rationale
    }

    shopper_sessions {
        integer session_id PK
        integer administrative_pages
        real administrative_duration
        integer informational_pages
        real informational_duration
        integer product_related_pages
        real product_related_duration
        real bounce_rate
        real exit_rate
        real page_value
        real special_day
        text month
        integer operating_systems
        integer browser
        integer region
        integer traffic_type
        text visitor_type
        integer weekend
        integer revenue_converted
    }
```

---

## 8. Hybrid RAG & PM Research Engine

The Research Engine solves the fundamental flaw of naive vector RAG (which cannot calculate sums or percentages accurately) by combining structured analytical queries with semantic context.

```mermaid
flowchart TD
    subgraph User_Query
        Q["PM Question:<br/>'Why do users hesitate to buy wishlisted footwear, and what is the top barrier?'"]
    end

    subgraph Router_Decomposer["Query Understanding & Routing (retrieval.py)"]
        DEC["Decompose Intent:<br/>1. Filter: product_category = 'footwear'<br/>2. Metric: Group by purchase_barrier, compute prevalence & linkage<br/>3. Semantic: Retrieve representative verbatim quotes"]
    end

    subgraph Dual_Retrieval
        SQL["Deterministic SQLite Query:<br/>SELECT purchase_barrier, COUNT(*), AVG(linkage) FROM ..."]
        VEC["ChromaDB Vector Retrieval:<br/>Query: 'footwear hesitation barrier' (where category='footwear')"]
    end

    subgraph Synthesis["Groq LLM Synthesis (research_engine.py)"]
        PROMPT["System Prompt + Deterministic SQL Table + Verbatim Quotes"]
        LLM["Groq LLaMA 3.3 70B Engine"]
    end

    subgraph Formatted_Output["Standardized VoC Research Output"]
        OUT["- Finding<br/>- Quantification (Exact % and N)<br/>- Affected Segments<br/>- Observed Behaviour<br/>- Representative Evidence (Direct Quotes)<br/>- Confidence Level (High/Med/Low)<br/>- Interpretation<br/>- Contradictory Evidence<br/>- Remaining Unknowns & Testable Hypotheses"]
    end

    Q --> DEC
    DEC --> SQL
    DEC --> VEC
    SQL --> PROMPT
    VEC --> PROMPT
    PROMPT --> LLM
    LLM --> OUT
```

---

## 9. Streamlit Presentation Architecture

```mermaid
graph TD
    subgraph Streamlit_App["Streamlit Application (dashboard/app.py)"]
        NAV["Sidebar Navigation & Global Filters (Source, Category, Date, Intent)"]
        
        subgraph View1["1. Executive Discovery"]
            V1_KPI["KPI Cards: Total Feedback, Relevant %, Top 5 Purchase Barriers"]
            V1_CHARTS["Source & Category Distribution Charts"]
            V1_OPP["Top Opportunity Prioritization Leaderboard"]
        end
        
        subgraph View2["2. Problem Explorer"]
            V2_TREE["2-Level Problem Taxonomy Browser"]
            V2_METRICS["Prevalence, Source Breadth & Purchase Linkage Drilldown"]
            V2_QUOTES["Verbatim Evidence Viewer with Explicit/Inferred Tags"]
            V2_CONTR["Contradictory Behavior Analyzer"]
        end
        
        subgraph View3["3. Decision Journey"]
            V3_FUNNEL["Observed Funnel: Discover → Wishlist → Compare → Hesitate → Drop"]
            V3_HOTSPOTS["Friction Hotspot Callouts & External Research Exits"]
        end
        
        subgraph View4["4. VoC Research Assistant"]
            V4_CHAT["Natural Language Chat Interface with Suggested PM Prompts"]
            V4_RESP["Structured Synthesis with SQL Metrics & Citation Traceability"]
        end
    end

    NAV --> View1
    NAV --> View2
    NAV --> View3
    NAV --> View4
```

---

## 10. Project Directory & Component Mapping

```
AIwishlistDiscoveryEngine/
├── collectors/                   # Modular Data Ingestion Layer
│   ├── __init__.py
│   ├── base_collector.py         # Abstract Base Collector
│   ├── youtube_collector.py      # YouTube Data API v3 Ingestion
│   ├── hf_dataset_loader.py      # Hugging Face & Local Dataset Ingestion
│   ├── reddit_collector.py       # Reddit API & Dataset Ingestion
│   └── web_collector.py          # Serper Google Search API Ingestion
│
├── database/                     # Relational Persistence
│   ├── __init__.py
│   ├── schema.py                 # SQLite Schema Definitions & DDL
│   └── db.py                     # Connection Pooling, CRUD & Transaction Helpers
│
├── processing/                   # Data Transformation & Filtering
│   ├── __init__.py
│   ├── cleaning.py               # Text Normalization & Sanitization
│   ├── deduplication.py          # Exact (SHA256) & Near (MinHash) Deduplication
│   └── relevance.py              # Groq-based Relevance Scoring (0-3)
│
├── ai/                           # AI, ML & NLP Modules
│   ├── __init__.py
│   ├── groq_client.py            # Resilient Groq Client (Rate-limiting & Retries)
│   ├── extraction.py             # Structured Schema & User Need Extractor
│   ├── embeddings.py             # Local BGE Embedding Model Wrapper
│   └── clustering.py             # HDBSCAN / Semantic Clustering & Taxonomy
│
├── vector/                       # Vector Store Management
│   ├── __init__.py
│   └── chroma_store.py           # ChromaDB Client & Collection Management
│
├── analysis/                     # Deterministic Analytics Engine
│   ├── __init__.py
│   ├── metrics.py                # Frequency, Prevalence & Linkage Math
│   ├── segmentation.py           # Multi-dimensional Segmentation Slicing
│   └── opportunity.py            # Opportunity Scoring & Prioritization
│
├── rag/                          # Hybrid RAG & Synthesis Engine
│   ├── __init__.py
│   ├── retrieval.py              # Hybrid SQL + ChromaDB Dual Retriever
│   └── research_engine.py        # PM Q&A Orchestrator & Synthesizer
│
├── dashboard/                    # Presentation Layer
│   ├── __init__.py
│   ├── app.py                    # Main Streamlit Entrypoint
│   └── views/                    # Multi-page Views
│       ├── executive_view.py
│       ├── problem_explorer.py
│       ├── decision_journey.py
│       └── research_chat.py
│
├── prompts/                      # Version-Controlled LLM Prompts
│   ├── relevance_prompt.txt
│   ├── extraction_prompt.txt
│   └── research_prompt.txt
│
├── tests/                        # Test Suite (Unit & Pipeline Tests)
│   ├── test_collectors.py
│   ├── test_cleaning.py
│   ├── test_extraction.py
│   └── test_metrics.py
│
├── data/                         # Local Data Directory (Gitignored)
│   ├── raw/
│   └── processed/
│
├── .env.example                  # Environment Configuration Template
├── .gitignore
├── requirements.txt              # Production Dependencies
├── main.py                       # Pipeline CLI Orchestration
├── context.md                    # Problem & Blueprint Specification
├── architecture.md               # This System Architecture Document
└── README.md
```

---

## 11. Security, Rate Limiting & Reliability Safeguards

1. **Credential Isolation**: Zero hardcoded secrets. All API keys (`GROQ_API_KEY`, `YOUTUBE_API_KEY`, `SERPER_API_KEY`, `REDDIT_*`, `HF_TOKEN`) are loaded from `.env` via `python-dotenv`.
2. **API Resilience & Rate Limiting**:
   - Exponential backoff with jitter on Groq and YouTube API rate limit errors (HTTP 429).
   - Local token batching for Groq structured extraction.
3. **Zero Hallucination Grounding**:
   - Extraction prompts enforce strict extraction from provided text only.
   - LLM generation in RAG is grounded strictly in supplied SQL summary tables and retrieved ChromaDB quotes.
4. **Data Integrity & Immutability**:
   - `raw_feedback` table is strictly append-only; cleaning and processing never overwrite original text.
   - Evidence spans are preserved verbatim for full auditability.
