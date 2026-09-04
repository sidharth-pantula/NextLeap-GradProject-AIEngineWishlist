"""Local ChromaDB vector store manager for feedback, evidence, and user needs."""
import os
from typing import Any, Dict, List, Optional

try:
    import chromadb
    from chromadb.config import Settings
    HAS_CHROMADB = True
except ImportError:
    HAS_CHROMADB = False


class ChromaStore:
    """Manages local persistent ChromaDB collections for semantic retrieval."""

    FEEDBACK_COLLECTION = "feedback_embeddings"
    EVIDENCE_COLLECTION = "evidence_embeddings"
    USER_NEEDS_COLLECTION = "user_needs_embeddings"

    def __init__(self, persist_dir: str = "chroma_db"):
        self.persist_dir = persist_dir
        os.makedirs(persist_dir, exist_ok=True)

        if HAS_CHROMADB:
            self.client = chromadb.PersistentClient(
                path=persist_dir,
                settings=Settings(anonymized_telemetry=False)
            )
        else:
            self.client = None

        self._collections: Dict[str, Any] = {}

    def get_collection(self, name: str):
        """Get or create a ChromaDB collection by name."""
        if not HAS_CHROMADB or self.client is None:
            return None
        if name not in self._collections:
            self._collections[name] = self.client.get_or_create_collection(
                name=name,
                metadata={"hnsw:space": "cosine"}
            )
        return self._collections[name]

    def add_feedback_embeddings(
        self,
        feedback_ids: List[str],
        embeddings: List[List[float]],
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None
    ) -> int:
        """Upsert feedback embeddings and text documents."""
        coll = self.get_collection(self.FEEDBACK_COLLECTION)
        if coll is None or not feedback_ids:
            return 0

        clean_metas = []
        if metadatas:
            for m in metadatas:
                # Chroma requires metadata values to be str, int, float, or bool
                clean_meta = {}
                for k, v in m.items():
                    if v is None:
                        continue
                    if isinstance(v, (str, int, float, bool)):
                        clean_meta[k] = v
                    else:
                        clean_meta[k] = str(v)
                clean_metas.append(clean_meta)
        else:
            clean_metas = None

        coll.upsert(
            ids=feedback_ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=clean_metas
        )
        return len(feedback_ids)

    def add_evidence_embeddings(
        self,
        evidence_ids: List[str],
        embeddings: List[List[float]],
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None
    ) -> int:
        """Upsert evidence quote embeddings."""
        coll = self.get_collection(self.EVIDENCE_COLLECTION)
        if coll is None or not evidence_ids:
            return 0
        coll.upsert(
            ids=evidence_ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )
        return len(evidence_ids)

    def query_feedback(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        where_filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Query feedback collection using dense vector embedding and optional metadata filter."""
        coll = self.get_collection(self.FEEDBACK_COLLECTION)
        if coll is None:
            return []

        results = coll.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where_filter
        )

        formatted = []
        if results and results.get("ids") and results["ids"][0]:
            ids = results["ids"][0]
            docs = results["documents"][0] if results.get("documents") else [""] * len(ids)
            metas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(ids)
            dists = results["distances"][0] if results.get("distances") else [0.0] * len(ids)

            for i in range(len(ids)):
                formatted.append({
                    "id": ids[i],
                    "document": docs[i],
                    "metadata": metas[i],
                    "distance": dists[i]
                })

        return formatted

    def query_evidence(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        where_filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Query evidence collection for verbatim user quotes."""
        coll = self.get_collection(self.EVIDENCE_COLLECTION)
        if coll is None:
            return []

        results = coll.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where_filter
        )

        formatted = []
        if results and results.get("ids") and results["ids"][0]:
            ids = results["ids"][0]
            docs = results["documents"][0] if results.get("documents") else [""] * len(ids)
            metas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(ids)
            dists = results["distances"][0] if results.get("distances") else [0.0] * len(ids)

            for i in range(len(ids)):
                formatted.append({
                    "id": ids[i],
                    "document": docs[i],
                    "metadata": metas[i],
                    "distance": dists[i]
                })

        return formatted

    def get_collection_counts(self) -> Dict[str, int]:
        """Return counts of documents in all collections."""
        counts = {}
        for col_name in [self.FEEDBACK_COLLECTION, self.EVIDENCE_COLLECTION, self.USER_NEEDS_COLLECTION]:
            coll = self.get_collection(col_name)
            counts[col_name] = coll.count() if coll is not None else 0
        return counts


_vector_store_instance: Optional[ChromaStore] = None


def get_vector_store(persist_dir: str = "chroma_db") -> ChromaStore:
    """Get or create singleton ChromaStore instance."""
    global _vector_store_instance
    if _vector_store_instance is None or _vector_store_instance.persist_dir != persist_dir:
        _vector_store_instance = ChromaStore(persist_dir=persist_dir)
    return _vector_store_instance
