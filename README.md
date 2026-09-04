# AI-Powered Voice-of-Customer (VoC) Wishlist Discovery Engine

An end-to-end analytical intelligence platform that ingests unstructured customer feedback across Reddit, YouTube, HuggingFace datasets, and forums to uncover why shoppers abandon wishlists and what friction prevents conversion.

---

## 📌 Overview

The **Wishlist Discovery Engine** uses a hybrid AI architecture:
- **Deterministic Analytics (SQL / Python)** for mathematical accuracy and quantification.
- **Large Language Models (Groq / Llama 3)** for schema extraction, sentiment classification, and semantic synthesis.
- **Local Dense Embeddings & Vector Search (BGE-Small + ChromaDB)** for local semantic clustering and semantic retrieval.
- **Emerging Theme Discovery (HDBSCAN / KMeans)** for unsupervised taxonomy generation.
- **RAG & Interactive Dashboard** built on Streamlit with deep-dive drilldowns and verbatim evidence traceability.

---

## 🚀 Key Features

1. **Multi-Source Data Ingestion**:
   - Reddit API (`reddit_collector.py`)
   - YouTube Data API v3 (`youtube_collector.py`)
   - HuggingFace E-commerce Reviews (`hf_dataset_loader.py`)
   - Serper Web & Forum Search (`web_collector.py`)

2. **Data Processing & AI Enrichment Pipeline**:
   - Exact & MinHash LSH Near-Deduplication (`deduplication.py`)
   - Noise filtering & Text Normalization (`cleaning.py`)
   - Zero-shot / Few-shot Relevance Scoring (0–3 scale) (`relevance.py`)
   - Structured Schema Extraction (Frictions, Inferred Needs, Emotional Tone, Verbatim Quotes) (`extraction.py`)

3. **Semantic Discovery & Taxonomy**:
   - Local BGE Small v1.5 Embeddings
   - HDBSCAN / KMeans Clustering with Outlier Handling (`clustering.py`)
   - Dynamic 2-Level Problem Taxonomy Generation (`taxonomy.py`)

4. **Analytics & Hybrid RAG**:
   - Deterministic Metrics (Prevalence, Frequency, Friction-Need Linkages) (`metrics.py`)
   - Hybrid Context Synthesis (SQL Ground Truth + Vector Retrieval) (`hybrid_rag.py`)

5. **Executive Streamlit Dashboard**:
   - Executive Summary & KPI Metrics
   - Theme Discovery & Clustering Explorer
   - Deep-Dive Verbatim & Quote Inspector
   - Natural Language Query Interface (RAG)

---

## 🛠️ Project Structure

```
AIwishlistDiscoveryEngine/
├── ai/                     # LLM client, relevance classifier, extraction, clustering, taxonomy
├── analysis/               # Deterministic metrics calculation & reporting
├── collectors/             # Reddit, YouTube, HuggingFace & Web collectors
├── config/                 # System configuration & logging setup
├── dashboard/              # Streamlit dashboard pages & components
├── database/               # SQLite schema, queries, and migrations
├── docs/                   # Problem statement and reference documentation
├── processing/             # Text cleaning and MinHash LSH deduplication
├── prompts/                # Groq / LLM prompt templates
├── rag/                    # Hybrid RAG pipeline & retriever
├── tests/                  # Pytest test suite covering all phases
├── vector/                 # Local embeddings & ChromaDB store
├── architecture.md         # Full system design and architecture specification
├── context.md              # Project context & problem breakdown
├── requirements.txt        # Python dependencies
└── main.py                 # Pipeline runner CLI
```

---

## ⚙️ Setup & Installation

### 1. Clone the Repository
```bash
git clone https://github.com/sidharth-pantula/NextLeap-GradProject-AIEngineWishlist.git
cd NextLeap-GradProject-AIEngineWishlist
```

### 2. Set Up Virtual Environment
```bash
python -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Copy `.env.example` to `.env` and fill in your API keys:
```bash
cp .env.example .env
```
Key variables:
- `GROQ_API_KEY`: Groq API key for Llama 3 LLM calls
- `YOUTUBE_API_KEY`: Google Cloud YouTube Data API v3 key
- `REDDIT_CLIENT_ID` / `REDDIT_CLIENT_SECRET`: Reddit application credentials
- `SERPER_API_KEY`: Serper.dev Google Search API key

---

## 🏃 Usage

### Run the Full Ingestion & Processing Pipeline:
```bash
python main.py
```

### Launch the Streamlit Dashboard:
```bash
streamlit run dashboard/app.py
```

### Run Tests:
```bash
pytest
```

---

## 📜 License
MIT License
