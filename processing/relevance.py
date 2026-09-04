import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from database.db import Database, get_db
from ai.groq_client import GroqClient
from .cleaning import TextCleaner

DEFAULT_PROMPT_PATH = "prompts/relevance_prompt.txt"


class RelevanceClassifier:
    """Grades customer feedback relevance on a 0 to 3 scale using Groq LLM with heuristic fallback."""

    def __init__(
        self,
        groq_client: Optional[GroqClient] = None,
        db: Optional[Database] = None,
        prompt_path: str = DEFAULT_PROMPT_PATH
    ):
        self.groq = groq_client or GroqClient()
        self.db = db or get_db()
        self.cleaner = TextCleaner()
        self.prompt_template = ""
        if os.path.exists(prompt_path):
            with open(prompt_path, "r", encoding="utf-8") as f:
                self.prompt_template = f.read()

    def _heuristic_score(self, text: str, source: str = "web", source_type: str = "comment") -> Dict[str, Any]:
        """High-precision rule-based relevance scoring when LLM is unavailable or offline."""
        clean_res = self.cleaner.clean(text)
        if not clean_res["is_valid"]:
            return {
                "relevance_score": 0,
                "relevance_reason": f"Filtered as invalid/spam: {', '.join(clean_res['flags'])}",
                "relevance_confidence": 0.95
            }

        t = clean_res["cleaned_text"].lower()

        # Score 3: High intent & explicit wishlist/hesitation/conversion signals
        score_3_patterns = [
            r"\bwishlist\b", r"\bsaved?\b", r"\bhesitat(e|ion|ing)\b", r"\bpostpon(e|ing)\b",
            r"\bprice drop\b", r"\bwaiting for (the )?sale\b", r"\bcart\b", r"\bcheckout\b",
            r"\babandon(ed|ing)\b", r"\bcompar(e|ing|ison)\b", r"\bwhy (i|people) (didn't|don't) buy\b",
            r"\bmyntra vs\b", r"\bajio vs\b", r"\beors\b", r"\bdiwali sale\b"
        ]

        # Score 2: Shopping barriers (fit, sizing, quality, returns, price)
        score_2_patterns = [
            r"\bsiz(e|ing)\b", r"\bfit\b", r"\bquality\b", r"\bmaterial\b", r"\bfabric\b",
            r"\breturn(s|ing)?\b", r"\bexchange\b", r"\bexpensive\b", r"\bworth (it|the price)\b",
            r"\breview(s)?\b", r"\bstitching\b", r"\bphoto review\b", r"\bcheap\b", r"\brefund\b"
        ]

        # Score 1: General fashion / outfit talk
        score_1_patterns = [
            r"\bdress\b", r"\boutfit\b", r"\bwear\b", r"\bcolor\b", r"\bpretty\b", r"\bcute\b",
            r"\bstyle\b", r"\blook\b", r"\bclothes\b", r"\bcollection\b"
        ]

        if any(re.search(pat, t) for pat in score_3_patterns):
            return {
                "relevance_score": 3,
                "relevance_reason": "Explicitly discusses wishlist behavior, purchase hesitation, sales waiting, or comparison dynamics.",
                "relevance_confidence": 0.90
            }
        elif any(re.search(pat, t) for pat in score_2_patterns):
            return {
                "relevance_score": 2,
                "relevance_reason": "Discusses shopping friction, sizing, fabric quality, returns, or price perceptions.",
                "relevance_confidence": 0.85
            }
        elif any(re.search(pat, t) for pat in score_1_patterns):
            return {
                "relevance_score": 1,
                "relevance_reason": "General fashion or aesthetic discussion without shopping consideration friction.",
                "relevance_confidence": 0.80
            }

        return {
            "relevance_score": 0,
            "relevance_reason": "Irrelevant non-fashion content.",
            "relevance_confidence": 0.85
        }

    def score_record(
        self,
        text: str,
        source: str = "web",
        source_type: str = "comment",
        use_llm: bool = True
    ) -> Dict[str, Any]:
        """Grade a single record using Groq LLM or heuristic fallback."""
        if use_llm and self.groq.is_available() and self.prompt_template:
            prompt = self.prompt_template.format(
                text=text[:2000],
                source=source,
                source_type=source_type
            )
            response = self.groq.complete_json(prompt)
            if response and "relevance_score" in response:
                score = int(response["relevance_score"])
                # Clamp score between 0 and 3
                score = max(0, min(3, score))
                return {
                    "relevance_score": score,
                    "relevance_reason": str(response.get("relevance_reason", "")),
                    "relevance_confidence": float(response.get("relevance_confidence", 0.85))
                }

        # Fast high-precision heuristic rule engine
        return self._heuristic_score(text, source, source_type)

    def process_raw_feedback_batch(
        self,
        limit: int = 100,
        min_relevance: int = 0,
        use_llm: bool = False
    ) -> int:
        """Process unprocessed raw_feedback records and insert into processed_feedback."""
        sql = """
        SELECT r.* FROM raw_feedback r
        LEFT JOIN processed_feedback p ON r.feedback_id = p.feedback_id
        WHERE p.feedback_id IS NULL
        LIMIT :limit;
        """
        raw_rows = self.db.execute_query(sql, {"limit": limit})
        if not raw_rows:
            return 0

        processed_records = []
        for row in raw_rows:
            raw_text = row["text"]
            cleaned_info = self.cleaner.clean(raw_text)
            
            if not cleaned_info["is_valid"]:
                grading = {
                    "relevance_score": 0,
                    "relevance_reason": f"Filtered: {', '.join(cleaned_info['flags'])}",
                    "relevance_confidence": 0.95
                }
            else:
                grading = self.score_record(
                    text=cleaned_info["cleaned_text"],
                    source=row.get("source", "web"),
                    source_type=row.get("source_type", "comment"),
                    use_llm=use_llm
                )

            now = datetime.now(timezone.utc).isoformat()
            if grading["relevance_score"] >= min_relevance:
                processed_item = {
                    "feedback_id": row["feedback_id"],
                    "cleaned_text": cleaned_info["cleaned_text"] or raw_text,
                    "relevance_score": grading["relevance_score"],
                    "relevance_reason": grading["relevance_reason"],
                    "relevance_confidence": grading["relevance_confidence"],
                    "processing_timestamp": now
                }
                processed_records.append(processed_item)

        inserted_count = 0
        if processed_records:
            insert_sql = """
            INSERT INTO processed_feedback (
                feedback_id, cleaned_text, relevance_score, relevance_reason, relevance_confidence, processing_timestamp
            ) VALUES (
                :feedback_id, :cleaned_text, :relevance_score, :relevance_reason, :relevance_confidence, :processing_timestamp
            ) ON CONFLICT(feedback_id) DO UPDATE SET
                cleaned_text = excluded.cleaned_text,
                relevance_score = excluded.relevance_score,
                relevance_reason = excluded.relevance_reason,
                relevance_confidence = excluded.relevance_confidence,
                processing_timestamp = excluded.processing_timestamp;
            """
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.executemany(insert_sql, processed_records)
                inserted_count = len(processed_records)

        return inserted_count
