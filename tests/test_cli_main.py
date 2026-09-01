"""Coverage for cli/main.py - previously untested entirely."""
import os
import shutil
import tempfile
import unittest
from io import StringIO
from unittest.mock import patch

import cli.main as cli_main
from core.indexer import DataManager
from core.models import AutoCompleteData


class TestFormatResult(unittest.TestCase):
    def test_format_result_includes_rank_sentence_source_line_and_score(self):
        result = AutoCompleteData(
            completed_sentence="To be or not to be.",
            source_text="hamlet.txt",
            offset=3,
            score=42,
        )

        line = cli_main.format_result(1, result)

        self.assertTrue(line.startswith("1."))
        self.assertIn("To be or not to be.", line)
        self.assertIn("hamlet.txt", line)
        self.assertIn("line 3", line)
        self.assertIn("score: 42", line)


class TestHandleQuery(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        with open(os.path.join(self.test_dir, "corpus.txt"), "w", encoding="utf-8") as f:
            f.write("To be or not to be, that is the question.\n")

        self._original_manager = cli_main.manager
        cli_main.manager = DataManager()
        cli_main.manager.load_data(self.test_dir)

    def tearDown(self):
        cli_main.manager = self._original_manager
        shutil.rmtree(self.test_dir)

    def test_handle_query_prints_no_matches_message_for_unrelated_query(self):
        with patch("sys.stdout", new_callable=StringIO) as out:
            cli_main.handle_query("zzzzz totally unrelated")

        self.assertIn("No matching sentences found.", out.getvalue())

    def test_handle_query_prints_ranked_result_for_known_sentence(self):
        with patch("sys.stdout", new_callable=StringIO) as out:
            cli_main.handle_query("to be")

        printed = out.getvalue()
        self.assertIn("To be or not to be, that is the question.", printed)
        self.assertIn("1.", printed)


class TestRunCli(unittest.TestCase):
    def setUp(self):
        self._original_manager = cli_main.manager

    def tearDown(self):
        cli_main.manager = self._original_manager

    def test_run_cli_warns_when_data_dir_missing(self):
        cli_main.manager = DataManager()
        missing_dir = os.path.join(tempfile.gettempdir(), "definitely-not-a-real-bat-archive-dir")

        with patch("builtins.input", side_effect=EOFError), \
             patch("sys.stdout", new_callable=StringIO) as out:
            cli_main.run_cli(missing_dir)

        self.assertIn(f"Warning: Directory '{missing_dir}' not found.", out.getvalue())

    def test_run_cli_loads_existing_data_dir_into_the_manager(self):
        cli_main.manager = DataManager()
        test_dir = tempfile.mkdtemp()
        try:
            with open(os.path.join(test_dir, "a.txt"), "w", encoding="utf-8") as f:
                f.write("hello there\n")

            with patch("builtins.input", side_effect=EOFError), \
                 patch("sys.stdout", new_callable=StringIO):
                cli_main.run_cli(test_dir)

            self.assertEqual(len(cli_main.manager.sentences), 1)
        finally:
            shutil.rmtree(test_dir)


if __name__ == "__main__":
    unittest.main()
