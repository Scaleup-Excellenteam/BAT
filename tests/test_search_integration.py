"""End-to-end check of core.search_engine against Dev 1's real DataManager
(core.indexer), instead of the FakeIndex stub used in test_search.py -
this is what actually proves the two modules interoperate correctly.
"""
import shutil
import tempfile
import unittest
from pathlib import Path

from core.indexer import DataManager
from core.search_engine import search


class TestSearchIntegration(unittest.TestCase):
    def setUp(self):
        self.corpus_dir = tempfile.mkdtemp()
        (Path(self.corpus_dir) / "hamlet.txt").write_text(
            "To be or not to be, that is the question.\n"
            "Whether 'tis nobler in the mind to suffer\n",
            encoding="utf-8",
        )
        self.data_manager = DataManager()
        self.data_manager.load_data(self.corpus_dir)

    def tearDown(self):
        shutil.rmtree(self.corpus_dir)

    def test_exact_match(self):
        results = search("to be", self.data_manager)
        exact = [r for r in results if r.edit_type == "exact"]
        self.assertEqual({r.offset for r in exact}, {0, 13})

    def test_substitution_match(self):
        # "to pe" -> "to be" via substituting 'p' for 'b' at position 4
        results = search("to pe", self.data_manager)
        substitutions = [r for r in results if r.edit_type == "substitution"]
        self.assertTrue(
            any(r.offset == 0 and r.edit_position == 4 for r in substitutions)
        )

    def test_deletion_match(self):
        # "or knot" has an extra 'k' at position 4 that must be deleted
        results = search("or knot", self.data_manager)
        deletions = [r for r in results if r.edit_type == "deletion"]
        self.assertTrue(any(r.edit_position == 4 for r in deletions))

    def test_insertion_match(self):
        # "or nt" is missing the 'o' at position 5
        results = search("or nt", self.data_manager)
        insertions = [r for r in results if r.edit_type == "insertion"]
        self.assertTrue(any(r.edit_position == 5 for r in insertions))


if __name__ == "__main__":
    unittest.main()
