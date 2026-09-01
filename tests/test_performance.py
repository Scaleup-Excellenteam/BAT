"""Complexity/performance-characteristic coverage.

These assert *structural* efficiency properties (output size, growth rate,
index selectivity) rather than wall-clock timings, so they stay meaningful
and non-flaky in CI.
"""
import os
import shutil
import tempfile
import unittest
from types import SimpleNamespace

from core.generator import generate_variations
from core.indexer import DataManager
from core.models import SentenceRecord
from core.scoring import rank_candidates


def test_generate_variations_total_count_scales_linearly_with_query_length():
    short_query = "abcde"      # length 5
    long_query = "abcdefghi"   # length 9

    short_total = len(generate_variations(short_query))
    long_total = len(generate_variations(long_query))

    # total variations per query = 54*L + 27 (26 substitutions + 1 deletion +
    # 27 insertions at each of L positions, plus one extra insertion point) -
    # i.e. O(L), not O(L^2) or worse.
    assert short_total == 54 * len(short_query) + 27
    assert long_total == 54 * len(long_query) + 27
    assert long_total - short_total == 54 * (len(long_query) - len(short_query))


def test_rank_candidates_output_size_is_bounded_by_top_k_regardless_of_input_size():
    records = {
        i: SentenceRecord(i, f"sentence number {i}", f"sentence number {i}", "f.txt", 1)
        for i in range(1000)
    }
    matches = [
        SimpleNamespace(sentence_id=i, error_type=None, error_index=None)
        for i in range(1000)
    ]

    results = rank_candidates("sentence", matches, records.get, top_k=5)

    # output stays O(top_k) even when fed 1000 raw candidate matches
    assert len(results) == 5


class TestIndexSelectivity(unittest.TestCase):
    """The inverted k-mer index should prune down to matching sentences
    rather than degrading into a full scan of the whole corpus."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        filler = [f"filler sentence number {i} about nothing in particular" for i in range(200)]
        filler.append("a very distinctive zephyr occurs exactly once here")
        with open(os.path.join(self.test_dir, "corpus.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(filler) + "\n")

        self.manager = DataManager()
        self.manager.load_data(self.test_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_candidate_lookup_prunes_unrelated_sentences_instead_of_scanning_all(self):
        candidates = self.manager.get_candidate_ids("zephyr")

        self.assertEqual(len(candidates), 1)
        self.assertLess(len(candidates), len(self.manager.sentences))


if __name__ == "__main__":
    unittest.main()
