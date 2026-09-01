"""Incremental Semantic search indexer using Google Embeddings and NumPy."""

import os
import pickle
import random
from dataclasses import dataclass
from typing import List, Optional, Set, Tuple, Any
import numpy as np

from services.gemini_service import GeminiService

CACHE_FILE = "semantic_cache.pkl"
BATCH_ADD_SIZE = 100
MAX_TOTAL_VECTORS = 100000


@dataclass
class IndexedSentence:
    text: str
    source_path: str
    line_number: int


@dataclass
class SemanticMatchResult:
    sentence: str
    source_path: str
    line_number: int
    similarity_score: float


class SemanticSearchEngine:
    """Handles incremental embedding creation, caching, and cosine similarity search."""

    def __init__(self, gemini_service: GeminiService, cache_path: str = CACHE_FILE):
        self.gemini_service = gemini_service
        self.cache_path = cache_path
        self.sentences_metadata: List[IndexedSentence] = []
        self.embeddings_matrix: Optional[np.ndarray] = None

    def _extract_fields(self, item: Any) -> Optional[IndexedSentence]:
        try:
            if isinstance(item, str):
                text = item.strip()
                if len(text) > 5:
                    return IndexedSentence(text=text, source_path="archive", line_number=0)
                return None

            if isinstance(item, dict):
                text = (
                    item.get("original_text")
                    or item.get("text")
                    or item.get("sentence")
                    or item.get("content")
                    or ""
                )
                source = item.get("source_path") or item.get("source") or item.get("file_path") or ""
                line = int(item.get("offset") or item.get("line_number") or item.get("line") or 0)
            elif isinstance(item, (list, tuple)) and len(item) >= 1:
                text = item[0]
                source = item[1] if len(item) > 1 else ""
                line = int(item[2]) if len(item) > 2 else 0
            else:
                text = (
                    getattr(item, "original_text", None)
                    or getattr(item, "text", None)
                    or getattr(item, "sentence", None)
                    or getattr(item, "content", None)
                    or ""
                )
                source = getattr(item, "source_path", getattr(item, "source", getattr(item, "file_path", "")))
                line = int(getattr(item, "offset", getattr(item, "line_number", getattr(item, "line", 0))))

            text = str(text).strip()
            if text and len(text) > 5:
                return IndexedSentence(text=text, source_path=str(source), line_number=line)
        except Exception:
            pass
        return None

    def build_index(
        self,
        sentences: List[Any],
        batch_size: int = BATCH_ADD_SIZE,
        max_total: int = MAX_TOTAL_VECTORS,
    ) -> None:
        self._load_from_cache()
        current_count = len(self.sentences_metadata)

        if current_count >= max_total:
            print(f"Semantic cache is fully built with {current_count} vectors.")
            return

        if not sentences or not self.gemini_service.is_available():
            return

        existing_texts: Set[str] = {s.text for s in self.sentences_metadata}

        parsed_items: List[IndexedSentence] = []
        for s in sentences:
            item = self._extract_fields(s)
            if item and item.text not in existing_texts:
                parsed_items.append(item)

        if not parsed_items:
            print(f"All available sentences ({current_count}) are already indexed.")
            return

        how_many_to_add = min(batch_size, max_total - current_count, len(parsed_items))
        sampled = random.sample(parsed_items, how_many_to_add)

        print(
            f"Current cache: {current_count} vectors. "
            f"Generating embeddings for {len(sampled)} new random sentences..."
        )

        texts = [s.text for s in sampled]
        raw_embeddings = self.gemini_service.get_batch_embeddings(texts)

        new_records: List[IndexedSentence] = []
        new_vectors: List[List[float]] = []

        for meta, vec in zip(sampled, raw_embeddings):
            if vec is not None:
                new_records.append(meta)
                new_vectors.append(vec)

        if not new_vectors:
            print("[Warning] No new vectors were generated.")
            return

        new_matrix = np.array(new_vectors, dtype=np.float32)
        norms = np.linalg.norm(new_matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1e-10
        new_matrix = new_matrix / norms

        if self.embeddings_matrix is None or current_count == 0:
            self.sentences_metadata = new_records
            self.embeddings_matrix = new_matrix
        else:
            self.sentences_metadata.extend(new_records)
            self.embeddings_matrix = np.vstack([self.embeddings_matrix, new_matrix])

        self._save_to_cache()
        print(f"Successfully cached {len(self.sentences_metadata)} total semantic vectors.")

    def search(self, query: str, top_k: int = 5) -> List[SemanticMatchResult]:
        if self.embeddings_matrix is None or not self.sentences_metadata:
            return []

        # תרגום אוטומטי במידה והשאילתה אינה באנגלית
        search_query = self.gemini_service.translate_to_english(query)
        if search_query != query:
            print(f"[Cross-Lingual] Translated '{query}' -> '{search_query}'")

        query_vec = self.gemini_service.get_embedding(search_query)
        if query_vec is None:
            return []

        q = np.array(query_vec, dtype=np.float32)
        q_norm = np.linalg.norm(q)
        if q_norm > 0:
            q = q / q_norm

        scores = np.dot(self.embeddings_matrix, q)
        top_indices = np.argsort(scores)[::-1][:top_k]

        results = []
        for idx in top_indices:
            meta = self.sentences_metadata[idx]
            score = float(scores[idx])
            results.append(
                SemanticMatchResult(
                    sentence=meta.text,
                    source_path=meta.source_path,
                    line_number=meta.line_number,
                    similarity_score=score,
                )
            )
        return results

    def _save_to_cache(self) -> None:
        try:
            with open(self.cache_path, "wb") as f:
                pickle.dump((self.sentences_metadata, self.embeddings_matrix), f)
        except Exception as e:
            print(f"[Warning] Failed to save semantic cache: {e}")

    def _load_from_cache(self) -> bool:
        if not os.path.exists(self.cache_path):
            return False
        try:
            with open(self.cache_path, "rb") as f:
                self.sentences_metadata, self.embeddings_matrix = pickle.load(f)
            return True
        except Exception:
            return False
