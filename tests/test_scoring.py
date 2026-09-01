"""Regression tests for actual Part A scores across the full search pipeline."""

import tempfile
import unittest
from pathlib import Path

from core.indexer import DataManager
from core.normalizer import normalize_text
from core.scoring import calculate_score, rank_candidates
from core.search_engine import search


class TestScoring(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        Path(self.directory.name, "hamlet.txt").write_text(
            "To be or not to be, that is the question.\n", encoding="utf-8"
        )
        self.manager = DataManager()
        self.manager.load_data(self.directory.name)

    def test_documented_scores_use_real_search_metadata(self):
        for query, expected in [("To be", 10), ("or Not", 12), ("to pe", 6), ("or knot", 8), ("or nt", 8)]:
            with self.subTest(query=query):
                matches = search(query, self.manager)
                results = rank_candidates(normalize_text(query), matches, self.manager.get_sentence)
                self.assertEqual(len(results), 1)
                self.assertEqual(results[0].score, expected)
                self.assertEqual(results[0].offset, 1)

    def test_exact_tag_keeps_all_matching_characters(self):
        self.assertEqual(calculate_score(5, "exact", None), 10)
        self.assertEqual(calculate_score(5, None, None), 10)

    def test_insertion_keeps_existing_query_characters(self):
        self.assertEqual(calculate_score(5, "insertion", 5), 8)

    def test_exact_ranks_ahead_of_alphabetically_earlier_fuzzy_result(self):
        Path(self.directory.name, "ranking.txt").write_text("a bat\nz cat\n", encoding="utf-8")
        manager = DataManager()
        manager.load_data(self.directory.name)
        results = rank_candidates("cat", search("cat", manager), manager.get_sentence)
        self.assertEqual(results[0].completed_sentence, "z cat")
        self.assertGreater(results[0].score, next(r.score for r in results if r.completed_sentence == "a bat"))

    def test_normalized_empty_query_has_no_results(self):
        for query in ("", "   ", "!!!"):
            with self.subTest(query=query):
                self.assertEqual(search(query, self.manager), [])
