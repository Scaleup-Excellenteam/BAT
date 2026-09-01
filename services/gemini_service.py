"""Gemini Service for Semantic Vector Search, Embeddings, and Cross-Lingual Translation."""

import os
from typing import Any, List, Optional
from dotenv import load_dotenv

load_dotenv()


def _load_env_fallback(filepath: str = ".env") -> None:
    if not os.path.exists(filepath):
        return
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip("\"'")
                if key and key not in os.environ:
                    os.environ[key] = val
    except Exception:
        pass


_load_env_fallback()

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None

EMBEDDING_MODEL = "gemini-embedding-2-preview"
TRANSLATION_MODEL = "gemini-3.6-flash"


class GeminiService:
    """Handles Vector Embeddings and Cross-Lingual Query Translation."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.client = None

        if self.api_key and genai:
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                print(f"[Warning] Failed to initialize Gemini SDK Client: {e}")
        elif not self.api_key:
            print("[Warning] GEMINI_API_KEY not found in environment or .env file.")

    def is_available(self) -> bool:
        return bool(self.api_key and self.client)

    def _extract_vector(self, emb_obj: Any) -> Optional[List[float]]:
        if emb_obj is None:
            return None
        if hasattr(emb_obj, "values"):
            return list(emb_obj.values)
        if hasattr(emb_obj, "embedding") and hasattr(emb_obj.embedding, "values"):
            return list(emb_obj.embedding.values)
        if isinstance(emb_obj, dict):
            return emb_obj.get("values") or emb_obj.get("embedding")
        if isinstance(emb_obj, (list, tuple)):
            return list(emb_obj)
        return None

    def get_embedding(self, text: str) -> Optional[List[float]]:
        """Retrieves a single embedding vector for a given text."""
        if not self.is_available() or not text.strip():
            return None

        try:
            response = self.client.models.embed_content(
                model=EMBEDDING_MODEL,
                contents=text,
            )
            if hasattr(response, "embeddings") and response.embeddings:
                return self._extract_vector(response.embeddings[0])
            if hasattr(response, "embedding"):
                return self._extract_vector(response.embedding)
        except Exception as e:
            print(f"[Embedding Error]: {e}")
        return None

    def get_batch_embeddings(
        self, texts: List[str], chunk_size: int = 50
    ) -> List[Optional[List[float]]]:
        """Retrieves embedding vectors in batches."""
        if not self.is_available() or not texts:
            return [None] * len(texts)

        all_embeddings: List[Optional[List[float]]] = []
        for i in range(0, len(texts), chunk_size):
            chunk = texts[i : i + chunk_size]
            chunk_results: List[Optional[List[float]]] = []

            try:
                response = self.client.models.embed_content(
                    model=EMBEDDING_MODEL,
                    contents=chunk,
                )
                if hasattr(response, "embeddings") and response.embeddings:
                    for emb in response.embeddings:
                        chunk_results.append(self._extract_vector(emb))
            except Exception:
                pass

            if len(chunk_results) != len(chunk):
                chunk_results = [self.get_embedding(t) for t in chunk]

            all_embeddings.extend(chunk_results)

        return all_embeddings

    def translate_to_english(self, query: str) -> str:
        """Translates non-English queries into English search keywords."""
        if not self.is_available() or not query.strip():
            return query

        if all(ord(c) < 128 for c in query):
            return query

        prompt = (
            "Translate the following search query into a concise English search phrase. "
            "Output ONLY the translated search keywords without quotes or explanations:\n"
            f"{query}"
        )

        try:
            response = self.client.models.generate_content(
                model=TRANSLATION_MODEL,
                contents=prompt,
            )
            if response and response.text:
                return response.text.strip().replace('"', "")
        except Exception as e:
            print(f"[Translation Error]: {e}")

        return query