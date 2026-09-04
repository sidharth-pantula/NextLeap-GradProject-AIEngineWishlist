"""Deduplication Engine supporting exact SHA-256 and near-duplicate Jaccard similarity."""
import hashlib
import re
from typing import Dict, List, Optional, Set, Tuple


class Deduplicator:
    """Manages exact and near-duplicate detection for raw and cleaned feedback items."""

    def __init__(self, jaccard_threshold: float = 0.85):
        self.jaccard_threshold = jaccard_threshold
        # Maps SHA-256 hash -> doc_id
        self._exact_hashes: Dict[str, str] = {}
        # Maps doc_id -> token set for near-duplicate Jaccard check
        self._doc_token_sets: Dict[str, Set[str]] = {}

    def _compute_hash(self, text: str) -> str:
        """Compute SHA-256 digest of normalized lowercase text."""
        normalized = re.sub(r'\s+', ' ', text.lower().strip())
        return hashlib.sha256(normalized.encode('utf-8')).hexdigest()

    def _tokenize(self, text: str) -> Set[str]:
        """Convert text into word tokens."""
        words = re.findall(r'\b\w{2,}\b', text.lower())
        return set(words)

    def _jaccard_similarity(self, set1: Set[str], set2: Set[str]) -> float:
        """Calculate Jaccard similarity coefficient between two token sets."""
        if not set1 or not set2:
            return 0.0
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        return intersection / union if union > 0 else 0.0

    def check_duplicate(self, text: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """Check if text is an exact or near duplicate of any previously seen record.
        
        Returns:
            (is_duplicate, duplicate_type, matched_doc_id)
        """
        if not text or not text.strip():
            return False, None, None

        # 1. Exact SHA-256 check
        h = self._compute_hash(text)
        if h in self._exact_hashes:
            return True, "EXACT_SHA256", self._exact_hashes[h]

        # 2. Near-duplicate Jaccard check
        tokens = self._tokenize(text)
        if tokens:
            for doc_id, indexed_tokens in self._doc_token_sets.items():
                sim = self._jaccard_similarity(tokens, indexed_tokens)
                if sim >= self.jaccard_threshold:
                    return True, f"NEAR_DUPLICATE_JACCARD_{sim:.2f}", doc_id

        return False, None, None

    def add(self, doc_id: str, text: str) -> None:
        """Register a document into the deduplication index."""
        if not text or not text.strip():
            return
        h = self._compute_hash(text)
        self._exact_hashes[h] = doc_id
        tokens = self._tokenize(text)
        if tokens:
            self._doc_token_sets[doc_id] = tokens

    def clear(self) -> None:
        """Clear all deduplication index entries."""
        self._exact_hashes.clear()
        self._doc_token_sets.clear()
