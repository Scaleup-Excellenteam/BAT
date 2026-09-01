"""Edge-case coverage for core.indexer.DataManager, beyond the happy-path
cases already covered in tests/test_indexer.py."""
import os
import shutil
import tempfile
import unittest

from core.indexer import DataManager


class TestDataManagerEdgeCases(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_load_data_missing_directory_raises_file_not_found(self):
        manager = DataManager()
        missing = os.path.join(self.test_dir, "does-not-exist")

        with self.assertRaises(FileNotFoundError):
            manager.load_data(missing)

    def test_load_data_ignores_non_txt_files(self):
        with open(os.path.join(self.test_dir, "notes.md"), "w", encoding="utf-8") as f:
            f.write("This markdown line should never be indexed.\n")
        with open(os.path.join(self.test_dir, "corpus.txt"), "w", encoding="utf-8") as f:
            f.write("This text line should be indexed.\n")

        manager = DataManager()
        manager.load_data(self.test_dir)

        self.assertEqual(len(manager.sentences), 1)
        self.assertEqual(manager.sentences[0].original_text, "This text line should be indexed.")

    def test_load_data_skips_blank_and_whitespace_only_lines(self):
        with open(os.path.join(self.test_dir, "corpus.txt"), "w", encoding="utf-8") as f:
            f.write("First real sentence.\n\n   \n\t\nSecond real sentence.\n")

        manager = DataManager()
        manager.load_data(self.test_dir)

        self.assertEqual(len(manager.sentences), 2)
        self.assertEqual(manager.sentences[0].original_text, "First real sentence.")
        self.assertEqual(manager.sentences[1].original_text, "Second real sentence.")

    def test_get_sentence_returns_none_for_out_of_range_ids(self):
        with open(os.path.join(self.test_dir, "corpus.txt"), "w", encoding="utf-8") as f:
            f.write("Only sentence.\n")

        manager = DataManager()
        manager.load_data(self.test_dir)

        self.assertIsNone(manager.get_sentence(-1))
        self.assertIsNone(manager.get_sentence(1))

    def test_get_candidate_ids_empty_query_returns_empty_set(self):
        with open(os.path.join(self.test_dir, "corpus.txt"), "w", encoding="utf-8") as f:
            f.write("Some sentence here.\n")

        manager = DataManager()
        manager.load_data(self.test_dir)

        self.assertEqual(manager.get_candidate_ids(""), set())


if __name__ == "__main__":
    unittest.main()
