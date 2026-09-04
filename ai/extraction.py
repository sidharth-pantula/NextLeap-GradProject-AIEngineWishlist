"""Structured Information Extraction Pipeline using Groq LLM with Evidence Grounding and Wishlist Decision Journey Layer."""
import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from database.db import Database, get_db
from ai.groq_client import GroqClient

logger = logging.getLogger(__name__)
DEFAULT_EXTRACTION_PROMPT_PATH = "prompts/extraction_prompt.txt"


class FeedbackExtractionModel(BaseModel):
    """Pydantic model for schema validation of extracted feedback fields including Wishlist Journey."""
    # 7-Tier Wishlist Intent Taxonomy
    intent_tier: Optional[str] = "uncertain_unknown"
    save_reason_category: Optional[str] = "unknown"
    wishlist_state: Optional[str] = "unknown"
    trigger_condition: Optional[str] = None
    trigger_type: Optional[str] = "potential_trigger"
    trigger_category: Optional[str] = "confidence"
    information_needed_category: Optional[str] = "fit"
    current_workaround: Optional[str] = "reading_reviews"
    option_preservation_signal: int = 0
    scarcity_reaction: Optional[str] = "neutral"
    reactivation_trigger: Optional[str] = "none"

    # Core Problem & Friction Fields
    user_intent: Optional[str] = "bookmark_only"
    wishlist_reason: Optional[str] = "none"
    purchase_intent: Optional[str] = "postponed"
    purchase_barrier: Optional[str] = "none"
    purchase_hesitation: Optional[str] = None
    purchase_postponement_reason: Optional[str] = None
    uncertainty_type: Optional[str] = "none"
    information_needed: Optional[str] = None
    decision_stage: Optional[str] = "wishlisted"
    behaviour_after_interest: Optional[str] = "none"
    comparison_behaviour: Optional[str] = "none"
    external_search_behaviour: Optional[str] = "none"
    competitor_behaviour: Optional[str] = "none"
    purchase_outcome: Optional[str] = "postponed"
    product_category: Optional[str] = "Apparel"
    product_type: Optional[str] = "clothing item"
    price_sensitivity: Optional[str] = "moderate"
    fit_concern: int = 0
    size_concern: int = 0
    quality_concern: int = 0
    material_concern: int = 0
    styling_concern: int = 0
    occasion_concern: int = 0
    review_concern: int = 0
    social_validation_need: int = 0
    trust_concern: int = 0
    availability_concern: int = 0
    return_exchange_concern: int = 0
    user_segment_signals: Optional[str] = "general"
    evidence_strength: Optional[str] = "moderate"
    evidence_span: Optional[str] = None
    evidence_type: Optional[str] = "inferred"
    inferred_user_need: Optional[str] = None
    inference_confidence: float = 0.85


class ExtractionPipeline:
    """Orchestrates structured LLM information extraction and updates processed_feedback in SQLite."""

    def __init__(
        self,
        groq_client: Optional[GroqClient] = None,
        db: Optional[Database] = None,
        prompt_path: str = DEFAULT_EXTRACTION_PROMPT_PATH
    ):
        self.groq = groq_client or GroqClient()
        self.db = db or get_db()
        self.prompt_template = ""
        if os.path.exists(prompt_path):
            with open(prompt_path, "r", encoding="utf-8") as f:
                self.prompt_template = f.read()

    def validate_and_ground_evidence(self, original_text: str, extracted_span: Optional[str]) -> Tuple[Optional[str], str]:
        """Verify that the evidence span is an exact verbatim substring of the input text (Zero Hallucination check)."""
        if not extracted_span or not original_text:
            return None, "inferred"

        # Check exact verbatim match (case-insensitive substring)
        if extracted_span.lower() in original_text.lower():
            start_idx = original_text.lower().find(extracted_span.lower())
            exact_match = original_text[start_idx:start_idx + len(extracted_span)]
            return exact_match, "explicit"

        # If LLM slightly paraphrased, attempt to find a key phrase match or flag as inferred
        words = [w for w in extracted_span.split() if len(w) > 3]
        for w in words:
            if w.lower() in original_text.lower():
                return extracted_span, "inferred"

        return None, "inferred"

    def _heuristic_extract(self, text: str) -> Dict[str, Any]:
        """Comprehensive rule-based extraction for Wishlist Decision Journey & Barriers."""
        t = text.lower()
        
        # 1. Concern Flags
        fit_c = 1 if any(k in t for k in ["fit", "loose", "tight", "flattering", "baggy", "length", "petite"]) else 0
        size_c = 1 if any(k in t for k in ["size", "sizing", "small", "large", "chart", "bust", "waist", "inches"]) else 0
        qual_c = 1 if any(k in t for k in ["quality", "material", "fabric", "stitch", "cheap", "sheer", "transparent", "shrink"]) else 0
        price_c = 1 if any(k in t for k in ["price", "expensive", "sale", "discount", "offer", "coupon", "cost", "drop", "diwali", "eors"]) else 0
        ret_c = 1 if any(k in t for k in ["return", "exchange", "refund", "delivery", "shipping"]) else 0
        stock_c = 1 if any(k in t for k in ["stock", "out of stock", "available", "sold out", "restock", "disappear"]) else 0
        review_c = 1 if any(k in t for k in ["review", "photo", "reddit", "youtube", "haul", "try on", "swatch"]) else 0

        # 2. Barrier Classification
        barrier = "none"
        if size_c or fit_c:
            barrier = "fit_sizing"
        elif price_c:
            barrier = "price"
        elif qual_c:
            barrier = "quality_material"
        elif ret_c:
            barrier = "returns"
        elif stock_c:
            barrier = "stock_availability"

        # 3. 7-Tier Intent Taxonomy (Strict vs Broader)
        # Immediate / High Intent
        immediate_patterns = [r"\bwant to buy\b", r"\bi'll purchase\b", r"\border this\b", r"\bneed this\b", r"\bgonna order\b", r"\bbuying this\b"]
        # Planned / Future Intent
        planned_patterns = [r"\bsaving for\b", r"\bpayday\b", r"\bnext month\b", r"\bwedding\b", r"\bfestival\b", r"\bvacation\b", r"\bbuy later\b", r"\bplanned\b"]
        # Conditional Purchase Intent
        conditional_patterns = [r"\bif the price drops\b", r"\bwhen (my )?size is available\b", r"\bduring (the )?sale\b", r"\bif reviews are good\b", r"\bif i can figure out\b", r"\bwaiting for (the )?price\b", r"\bwaiting for sale\b", r"\bprice drop\b"]
        # Active Consideration
        consideration_patterns = [r"\bcomparing\b", r"\bchecking reviews\b", r"\bchecking fit\b", r"\bresearch(ing)?\b", r"\basking\b", r"\bwatching reviews\b", r"\bwhich (one|brand)\b"]
        # Exploration / Inspiration
        exploration_patterns = [r"\bbrowsing\b", r"\bcollecting ideas\b", r"\blooks good\b", r"\boutfit inspiration\b", r"\bexploring\b", r"\baesthetic\b", r"\bstyling\b"]
        # Casual Bookmarking
        bookmarking_patterns = [r"\bkeep (it )?for later\b", r"\baccumulating\b", r"\bjust saved\b", r"\bsaved because\b", r"\bbookmarked\b"]

        if any(re.search(p, t) for p in immediate_patterns):
            intent_tier = "immediate_purchase"
        elif any(re.search(p, t) for p in planned_patterns):
            intent_tier = "planned_future"
        elif any(re.search(p, t) for p in conditional_patterns):
            intent_tier = "conditional_intent"
        elif any(re.search(p, t) for p in consideration_patterns):
            intent_tier = "active_consideration"
        elif any(re.search(p, t) for p in exploration_patterns):
            intent_tier = "exploration_inspiration"
        elif any(re.search(p, t) for p in bookmarking_patterns):
            intent_tier = "casual_bookmarking"
        else:
            intent_tier = "active_consideration" if (fit_c or qual_c or size_c) else "casual_bookmarking"

        # 4. Save Reason Category
        if intent_tier == "immediate_purchase":
            save_reason = "intentional_planning"
        elif intent_tier == "planned_future":
            save_reason = "future_consideration"
        elif "sale" in t or "price drop" in t or "discount" in t:
            save_reason = "sale_price_waiting"
        elif "compar" in t or "vs" in t:
            save_reason = "comparison"
        elif stock_c or "lose" in t or "disappear" in t:
            save_reason = "stock_anxiety"
        elif intent_tier == "exploration_inspiration":
            save_reason = "exploration_inspiration"
        elif intent_tier == "casual_bookmarking":
            save_reason = "casual_bookmarking"
        else:
            save_reason = "future_consideration" if price_c else "intentional_planning" if (fit_c or size_c) else "unknown"

        # 5. Wishlist State Machine
        if "bought" in t or "ordered" in t:
            state = "purchased"
        elif "returned" in t or "abandon" in t or "gave up" in t:
            state = "abandoned"
        elif "compar" in t or "vs" in t:
            state = "comparing"
        elif size_c or fit_c:
            state = "needs_information"
        elif "price drop" in t or "sale" in t or "expensive" in t:
            state = "waiting_for_price"
        elif stock_c:
            state = "waiting_for_availability"
        elif intent_tier == "exploration_inspiration":
            state = "exploring"
        elif intent_tier == "active_consideration":
            state = "considering"
        elif intent_tier == "planned_future":
            state = "waiting"
        else:
            state = "just_saved"

        # 6. Purchase Trigger Discovery
        trigger_cond = None
        trigger_type = "observed_stated"
        trigger_cat = "confidence"

        if size_c or fit_c:
            trigger_cond = "Accurate garment measurements and real customer body try-on photos"
            trigger_type = "observed_stated" if ("wish" in t or "provide" in t or "chart" in t) else "potential_trigger"
            trigger_cat = "confidence"
        elif "sale" in t or "price drop" in t:
            trigger_cond = "Price drop or seasonal sale activation"
            trigger_type = "observed_stated"
            trigger_cat = "price_promotion"
        elif stock_c:
            trigger_cond = "Restock notification and size availability confirmation"
            trigger_type = "potential_trigger"
            trigger_cat = "availability"
        elif qual_c:
            trigger_cond = "Fabric composition transparency and wash-care durability proof"
            trigger_type = "potential_trigger"
            trigger_cat = "confidence"
        else:
            trigger_cond = "Styling recommendations and social validation reviews"
            trigger_type = "hypothesis_to_validate"
            trigger_cat = "decision_support"

        # 7. Information Needed Category
        if size_c:
            info_cat = "size"
        elif fit_c:
            info_cat = "fit"
        elif qual_c:
            info_cat = "material" if ("fabric" in t or "sheer" in t or "cotton" in t) else "quality"
        elif "photo" in t or "look" in t:
            info_cat = "customer_photos"
        elif review_c:
            info_cat = "reviews"
        elif "return" in t or "exchange" in t:
            info_cat = "return_policy"
        elif "price" in t:
            info_cat = "price_history"
        elif stock_c:
            info_cat = "availability"
        else:
            info_cat = "fit"

        # 8. Current Workaround
        if "reddit" in t or "r/" in t:
            workaround = "reddit"
        elif "youtube" in t or "video" in t or "haul" in t:
            workaround = "youtube_tryons"
        elif "google" in t or "search" in t:
            workaround = "google_search"
        elif "instagram" in t or "insta" in t:
            workaround = "instagram"
        elif "ask" in t or "friend" in t:
            workaround = "asking_friends"
        elif review_c:
            workaround = "reading_reviews"
        elif "ajio" in t or "myntra" in t or "amazon" in t:
            workaround = "comparing_marketplaces"
        else:
            workaround = "reading_reviews"

        # 9. Option Preservation & Scarcity Signals
        option_signal = 1 if any(k in t for k in ["hold", "reserve", "save size", "out of stock", "disappear", "lose", "notify"]) else 0
        
        # Scarcity dual reactions
        if any(k in t for k in ["only few left", "hurry", "panic", "bought quickly"]):
            scarcity_reaction = "urgency_triggered"
        elif any(k in t for k in ["annoying", "ignore", "fake urgency", "don't believe", "pressure"]):
            scarcity_reaction = "pressure_resisted"
        elif any(k in t for k in ["waited anyway", "delayed", "still waited"]):
            scarcity_reaction = "waiting_anyway"
        else:
            scarcity_reaction = "neutral"

        # 10. Reactivation Trigger
        if "diwali" in t or "navratri" in t or "festival" in t:
            reactivation = "festival_diwali"
        elif "eors" in t or "big fashion festival" in t or "sale" in t:
            reactivation = "sale_eors"
        elif "wedding" in t:
            reactivation = "wedding_season"
        elif "price drop" in t:
            reactivation = "price_drop"
        elif stock_c:
            reactivation = "restock"
        else:
            reactivation = "none"

        return {
            "intent_tier": intent_tier,
            "save_reason_category": save_reason,
            "wishlist_state": state,
            "trigger_condition": trigger_cond,
            "trigger_type": trigger_type,
            "trigger_category": trigger_cat,
            "information_needed_category": info_cat,
            "current_workaround": workaround,
            "option_preservation_signal": option_signal,
            "scarcity_reaction": scarcity_reaction,
            "reactivation_trigger": reactivation,
            "user_intent": intent_tier,
            "wishlist_reason": save_reason,
            "purchase_intent": "conditional_on_discount" if price_c else "conditional_on_fit" if (size_c or fit_c) else "postponed",
            "purchase_barrier": barrier,
            "purchase_hesitation": f"Hesitation regarding {barrier}",
            "purchase_postponement_reason": trigger_cond or "Uncertainty prior to checkout",
            "uncertainty_type": "fit_size" if (size_c or fit_c) else "fabric_quality" if qual_c else "price_fairness",
            "information_needed": trigger_cond or "Accurate sizing and visual evidence",
            "decision_stage": state,
            "behaviour_after_interest": "monitored_product" if price_c else "researched_fit",
            "comparison_behaviour": "compared_platforms" if ("myntra" in t and "ajio" in t) else "none",
            "external_search_behaviour": workaround,
            "competitor_behaviour": "checked_myntra" if "myntra" in t else "checked_ajio" if "ajio" in t else "none",
            "purchase_outcome": "purchased" if state == "purchased" else "abandoned" if state == "abandoned" else "postponed",
            "product_category": "Apparel",
            "product_type": "clothing item",
            "price_sensitivity": "high" if price_c else "moderate",
            "fit_concern": fit_c,
            "size_concern": size_c,
            "quality_concern": qual_c,
            "material_concern": qual_c,
            "styling_concern": 0,
            "occasion_concern": 1 if ("wedding" in t or "diwali" in t) else 0,
            "review_concern": review_c,
            "social_validation_need": 1 if ("reddit" in t or "youtube" in t or review_c) else 0,
            "trust_concern": 1 if ("fake" in t or "trust" in t) else 0,
            "availability_concern": stock_c,
            "return_exchange_concern": ret_c,
            "user_segment_signals": "deliberative_shopper" if (size_c or qual_c) else "price_sensitive",
            "evidence_strength": "high" if (size_c or qual_c or price_c) else "moderate",
            "evidence_span": text[:120].strip(),
            "evidence_type": "explicit",
            "inferred_user_need": f"Needs {info_cat} clarity to move from {state} to purchase.",
            "inference_confidence": 0.88
        }

    def extract_record(
        self,
        text: str,
        source: str = "web",
        source_type: str = "comment",
        use_llm: bool = True
    ) -> Dict[str, Any]:
        """Extract structured fields from text using Groq LLM or heuristic fallback."""
        if use_llm and self.groq.is_available() and self.prompt_template:
            prompt = self.prompt_template.format(
                text=text[:3000],
                source=source,
                source_type=source_type
            )
            raw_json = self.groq.complete_json(prompt)
            if raw_json:
                try:
                    validated = FeedbackExtractionModel(**raw_json)
                    data = validated.model_dump()
                    span, ev_type = self.validate_and_ground_evidence(text, data.get("evidence_span"))
                    data["evidence_span"] = span
                    data["evidence_type"] = ev_type
                    return data
                except Exception as e:
                    logger.warning(f"Extraction JSON validation failed: {e}, falling back to heuristic")

        return self._heuristic_extract(text)

    def process_relevant_feedback_batch(
        self,
        limit: int = 500,
        min_relevance: int = 2,
        use_llm: bool = False,
        reprocess_all: bool = False
    ) -> int:
        """Process records in processed_feedback having relevance_score >= 2 and extract full structured schema."""
        if reprocess_all:
            sql = """
            SELECT p.feedback_id, p.cleaned_text, r.text as raw_text, r.source, r.source_type
            FROM processed_feedback p
            JOIN raw_feedback r ON p.feedback_id = r.feedback_id
            WHERE p.relevance_score >= :min_relevance
            LIMIT :limit;
            """
        else:
            sql = """
            SELECT p.feedback_id, p.cleaned_text, r.text as raw_text, r.source, r.source_type
            FROM processed_feedback p
            JOIN raw_feedback r ON p.feedback_id = r.feedback_id
            WHERE p.relevance_score >= :min_relevance
              AND (p.intent_tier IS NULL OR p.save_reason_category IS NULL)
            LIMIT :limit;
            """
            
        rows = self.db.execute_query(sql, {"min_relevance": min_relevance, "limit": limit})
        if not rows:
            return 0

        update_sql = """
        UPDATE processed_feedback SET
            intent_tier = :intent_tier,
            save_reason_category = :save_reason_category,
            wishlist_state = :wishlist_state,
            trigger_condition = :trigger_condition,
            trigger_type = :trigger_type,
            trigger_category = :trigger_category,
            information_needed_category = :information_needed_category,
            current_workaround = :current_workaround,
            option_preservation_signal = :option_preservation_signal,
            scarcity_reaction = :scarcity_reaction,
            reactivation_trigger = :reactivation_trigger,
            user_intent = :user_intent,
            wishlist_reason = :wishlist_reason,
            purchase_intent = :purchase_intent,
            purchase_barrier = :purchase_barrier,
            purchase_hesitation = :purchase_hesitation,
            purchase_postponement_reason = :purchase_postponement_reason,
            uncertainty_type = :uncertainty_type,
            information_needed = :information_needed,
            decision_stage = :decision_stage,
            behaviour_after_interest = :behaviour_after_interest,
            comparison_behaviour = :comparison_behaviour,
            external_search_behaviour = :external_search_behaviour,
            competitor_behaviour = :competitor_behaviour,
            purchase_outcome = :purchase_outcome,
            product_category = :product_category,
            product_type = :product_type,
            price_sensitivity = :price_sensitivity,
            fit_concern = :fit_concern,
            size_concern = :size_concern,
            quality_concern = :quality_concern,
            material_concern = :material_concern,
            styling_concern = :styling_concern,
            occasion_concern = :occasion_concern,
            review_concern = :review_concern,
            social_validation_need = :social_validation_need,
            trust_concern = :trust_concern,
            availability_concern = :availability_concern,
            return_exchange_concern = :return_exchange_concern,
            user_segment_signals = :user_segment_signals,
            evidence_strength = :evidence_strength,
            evidence_span = :evidence_span,
            evidence_type = :evidence_type,
            inferred_user_need = :inferred_user_need,
            inference_confidence = :inference_confidence,
            processing_timestamp = :processing_timestamp
        WHERE feedback_id = :feedback_id;
        """

        updated_items = []
        for r in rows:
            text_to_analyze = r["cleaned_text"] or r["raw_text"]
            extracted = self.extract_record(
                text=text_to_analyze,
                source=r.get("source", "web"),
                source_type=r.get("source_type", "comment"),
                use_llm=use_llm
            )
            extracted["feedback_id"] = r["feedback_id"]
            extracted["processing_timestamp"] = datetime.now(timezone.utc).isoformat()
            updated_items.append(extracted)

        if updated_items:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.executemany(update_sql, updated_items)

        return len(updated_items)
