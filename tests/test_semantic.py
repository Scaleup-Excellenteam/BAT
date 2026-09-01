"""Unit tests for Part B: Semantic search engine and Gemini integration."""

import unittest
from unittest.mock import MagicMock
import numpy as np

from core.models import SentenceRecord
from services.gemini_service import GeminiService
from services.semantic_indexer import SemanticSearchEngine


class TestSemanticSearchEngine(unittest.TestCase):
    """Test suite for semantic search indexer and similarity ranking."""

    def setUp(self):
        self.mock_gemini = MagicMock(spec=GeminiService)
        self.mock_gemini.is_available.return_value = True
        self.engine = SemanticSearchEngine(
            gemini_service=self.mock_gemini,
            cache_file="test_dummy_cache.pkl",
        )
        self.sample_records = [
            SentenceRecord(
                sentence_id=1,
                original_text="import os module",
                normalized_text="import os module",
                source_path="test1.txt",
                offset=1,
            ),
            SentenceRecord(
                sentence_id=2,
                original_text="connect to network socket",
                normalized_text="connect to network socket",
                source_path="test2.txt",
                offset=10,
            ),
            SentenceRecord(
                sentence_id=3,
                original_text="read line from disk file",
                normalized_text="read line from disk file",
                source_path="test3.txt",
                offset=25,
            ),
        ]

    def test_search_returns_ranked_by_cosine_similarity(self):
        """Verify candidates are sorted by cosine similarity descending."""
        self.engine.records = self.sample_records
        self.engine.embeddings_matrix = np.array(
            [
                [1.0, 0.0, 0.0],
                [0.0, 1.0, 0.0],
                [0.0, 0.0, 1.0],
            ],
            dtype=np.float32,
        )

        self.mock_gemini.translate_to_english.side_effect = lambda q: q
        self.mock_gemini.get_embedding.return_value = [0.1, 0.9, 0.0]

        results = self.engine.search("open network port", top_k=2)

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].sentence, "connect to network socket")
        self.assertEqual(results[0].line_number, 10)
        self.assertGreater(results[0].similarity_score, results[1].similarity_score)

    def test_cross_lingual_translation_integration(self):
        """Verify non-English queries are translated before embedding retrieval."""
        self.engine.records = self.sample_records
        self.engine.embeddings_matrix = np.eye(3, dtype=np.float32)

        self.mock_gemini.translate_to_english.return_value = "read line from disk file"
        self.mock_gemini.get_embedding.return_value = [0.0, 0.0, 1.0]

        results = self.engine.search("קריאת קובץ מהדיסק", top_k=1)

        self.mock_gemini.translate_to_english.assert_called_once_with("קריאת קובץ מהדיסק")
        self.mock_gemini.get_embedding.assert_called_once_with("read line from disk file")
        self.assertEqual(results[0].sentence, "read line from disk file")

    def test_graceful_handling_when_service_unavailable(self):
        """Verify search returns empty list without raising exceptions when API is down."""
        self.mock_gemini.is_available.return_value = False
        empty_engine = SemanticSearchEngine(gemini_service=self.mock_gemini)

        results = empty_engine.search("any query")
        self.assertEqual(results, [])


if __name__ == "__main__":
    unittest.main()