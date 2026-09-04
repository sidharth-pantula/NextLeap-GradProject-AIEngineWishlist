"""Natural Language PM VoC Research Engine powered by Hybrid RAG."""
import os
import logging
from typing import Any, Dict, Optional
from database.db import get_db, Database
from ai.groq_client import GroqClient
from rag.retrieval import HybridRetriever

logger = logging.getLogger(__name__)


class ResearchEngine:
    """Orchestrates Hybrid RAG question-answering for Product Managers."""

    def __init__(
        self,
        db: Optional[Database] = None,
        retriever: Optional[HybridRetriever] = None,
        groq_client: Optional[GroqClient] = None,
        prompt_path: str = "prompts/research_prompt.txt"
    ):
        self.db = db or get_db()
        self.retriever = retriever or HybridRetriever(db=self.db)
        self.groq = groq_client or GroqClient()
        self.prompt_path = prompt_path
        self._prompt_template = self._load_prompt()

    def _load_prompt(self) -> str:
        """Load research synthesis prompt template."""
        if os.path.exists(self.prompt_path):
            with open(self.prompt_path, "r", encoding="utf-8") as f:
                return f.read()
        return (
            "Analyze the following context to answer the PM query.\n\n"
            "Query: {query}\n\n"
            "SQL Summary:\n{sql_summary}\n\n"
            "Quotes:\n{evidence_quotes}\n"
        )

    def answer_query(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        """Execute hybrid dual retrieval and generate a grounded, structured VoC research response."""
        # 1. Retrieve Hybrid Context
        context = self.retriever.retrieve(query, top_k=top_k)

        # 2. Format Prompt
        prompt = self._prompt_template.format(
            query=query,
            sql_summary=context["sql_summary"],
            evidence_quotes=context["evidence_quotes"]
        )

        # 3. Generate LLM Synthesis
        if not self.groq.is_available():
            # Graceful deterministic fallback if Groq API key is not configured
            fallback_response = (
                "### 1. Finding\n"
                "Deterministic summary extracted from local database.\n\n"
                "### 2. Quantification\n"
                f"{context['sql_summary']}\n\n"
                "### 5. Representative Evidence\n"
                f"{context['evidence_quotes']}\n\n"
                "*(Note: Groq LLM API key not configured for narrative synthesis)*"
            )
            return {
                "query": query,
                "response": fallback_response,
                "context": context
            }

        response_text = self.groq.complete_text(prompt=prompt)
        if not response_text:
            response_text = (
                "### 1. Finding\n"
                "Unable to generate LLM narrative synthesis at this time.\n\n"
                "### 2. Quantification\n"
                f"{context['sql_summary']}\n\n"
                "### 5. Representative Evidence\n"
                f"{context['evidence_quotes']}"
            )

        return {
            "query": query,
            "response": response_text,
            "context": context
        }
