"""Gemini API integration for Embeddings and Cross-lingual Translation."""

import os
from typing import List, Optional
from dotenv import load_dotenv

# טעינת משתני סביבה מקובץ .env
load_dotenv()

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None


class GeminiService:
    """Service wrapper for Google Gemini Embeddings and Translation."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.client = None
        if self.api_key and genai:
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                print(f"[Warning] Failed to initialize Gemini Client: {e}")

    def is_available(self) -> bool:
        """בודק האם השירות זמין והוגדר מפתח תקין."""
        return self.client is not None

    def get_embedding(self, text: str) -> Optional[List[float]]:
        """מייצר וקטור ייצוג (Embedding) עבור טקסט בודד."""
        if not self.is_available() or not text.strip():
            return None
        try:
            response = self.client.models.embed_content(
                model="text-embedding-004",
                contents=text,
            )
            return response.embedding.values
        except Exception as e:
            print(f"[Error] Gemini Embedding failed: {e}")
            return None

    def get_batch_embeddings(self, texts: List[str]) -> List[Optional[List[float]]]:
        """מייצר וקטורי ייצוג עבור רשימת משפטים במרוכז."""
        if not self.is_available() or not texts:
            return [None] * len(texts)
        try:
            response = self.client.models.embed_content(
                model="text-embedding-004",
                contents=texts,
            )
            # אם מוחזרת רשימת embeddings
            if hasattr(response, "embeddings"):
                return [emb.values for emb in response.embeddings]
            elif hasattr(response, "embedding"):
                return [response.embedding.values]
            return [None] * len(texts)
        except Exception as e:
            print(f"[Error] Batch Embedding failed: {e}")
            return [None] * len(texts)

    def translate_to_english(self, query: str) -> str:
        """מזהה ומתרגם שאילתה לאנגלית אם היא נכתבה בשפה אחרת."""
        if not self.is_available() or not query.strip():
            return query

        # בדיקה פשוטה אם יש תווים שאינם אסקיי (למשל עברית/ערבית)
        if all(ord(c) < 128 for c in query):
            return query

        try:
            prompt = (
                "Translate the following search query into a concise English phrase. "
                "Output ONLY the translated search keywords without quotes or explanations:\n"
                f"{query}"
            )
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )
            translated = response.text.strip() if response.text else query
            return translated
        except Exception as e:
            print(f"[Warning] Translation failed, using original query: {e}")
            return query