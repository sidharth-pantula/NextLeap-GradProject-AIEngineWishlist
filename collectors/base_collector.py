"""Abstract Base Collector interface for the VoC Discovery Engine."""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from database.db import Database, get_db


class BaseCollector(ABC):
    """Abstract base class ensuring all source collectors normalize into raw_feedback."""

    def __init__(self, db: Optional[Database] = None):
        self.db = db or get_db()

    @abstractmethod
    def collect(self, *args, **kwargs) -> List[Dict[str, Any]]:
        """Collect source records."""
        pass

    @abstractmethod
    def normalize_record(self, raw_item: Dict[str, Any]) -> Dict[str, Any]:
        """Convert a source-specific record into the standardized raw_feedback schema."""
        pass

    def save_normalized(self, normalized_records: List[Dict[str, Any]]) -> int:
        """Batch save normalized records to SQLite raw_feedback table."""
        return self.db.batch_insert_raw_feedback(normalized_records)
