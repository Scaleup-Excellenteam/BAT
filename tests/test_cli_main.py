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
from core.snapshot_store import build_snapshot, publish_snapshot
from core.snapshot_watcher import SnapshotWatcher


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


class TestRunCliSnapshotsDir(unittest.TestCase):
    """ZDT: run_cli can serve from a snapshots_dir published by the offline side."""

    def setUp(self):
        self._original_manager = cli_main.manager
        self.work_dir = tempfile.mkdtemp()
        self.snapshots_dir = os.path.join(self.work_dir, "snapshots")

    def tearDown(self):
        cli_main.manager = self._original_manager
        shutil.rmtree(self.work_dir)

    def test_run_cli_serves_from_the_published_snapshot_when_snapshots_dir_is_given(self):
        corpus_dir = os.path.join(self.work_dir, "corpus")
        os.makedirs(corpus_dir)
        with open(os.path.join(corpus_dir, "a.txt"), "w", encoding="utf-8") as f:
            f.write("hello there\n")
        snapshot_id = build_snapshot(corpus_dir, self.snapshots_dir)
        publish_snapshot(self.snapshots_dir, snapshot_id)

        with patch("builtins.input", side_effect=EOFError), \
             patch("sys.stdout", new_callable=StringIO):
            cli_main.run_cli(snapshots_dir=self.snapshots_dir)

        self.assertEqual(cli_main.manager.current_snapshot_id, snapshot_id)

    def test_run_cli_warns_when_snapshots_dir_has_nothing_published(self):
        with patch("builtins.input", side_effect=EOFError), \
             patch("sys.stdout", new_callable=StringIO) as out:
            cli_main.run_cli(snapshots_dir=self.snapshots_dir)

        self.assertIn(f"no published snapshot found in '{self.snapshots_dir}'", out.getvalue())


class TestHandleQueryHotReloadsFromSnapshots(unittest.TestCase):
    """The actual zero-downtime scenario: a new data source is built and published
    into snapshots_dir while cli/main.py's already-running `manager` keeps serving
    queries, and it picks up the change on the very next query - no restart."""

    def setUp(self):
        self.work_dir = tempfile.mkdtemp()
        self.snapshots_dir = os.path.join(self.work_dir, "snapshots")

        self.corpus_a = os.path.join(self.work_dir, "corpus_a")
        os.makedirs(self.corpus_a)
        with open(os.path.join(self.corpus_a, "a.txt"), "w", encoding="utf-8") as f:
            f.write("To be or not to be, that is the question.\n")

        self.corpus_b = os.path.join(self.work_dir, "corpus_b")
        os.makedirs(self.corpus_b)
        with open(os.path.join(self.corpus_b, "b.txt"), "w", encoding="utf-8") as f:
            f.write("A brand new data source added live.\n")

        snapshot_a = build_snapshot(self.corpus_a, self.snapshots_dir)
        publish_snapshot(self.snapshots_dir, snapshot_a)

        self._original_manager = cli_main.manager
        cli_main.manager = SnapshotWatcher(self.snapshots_dir)

    def tearDown(self):
        cli_main.manager = self._original_manager
        shutil.rmtree(self.work_dir)

    def test_query_is_served_from_the_snapshot_published_before_startup(self):
        with patch("sys.stdout", new_callable=StringIO) as out:
            cli_main.handle_query("to be")

        self.assertIn("To be or not to be, that is the question.", out.getvalue())

    def test_query_picks_up_a_newly_published_snapshot_with_no_restart(self):
        with patch("sys.stdout", new_callable=StringIO) as out:
            cli_main.handle_query("brand new data source")
        self.assertIn("No matching sentences found in corpus.", out.getvalue())

        # Offline side builds and publishes a new snapshot from a brand-new
        # data source. Nothing here restarts cli_main or reconstructs its
        # `manager` - it's the exact same SnapshotWatcher instance.
        snapshot_b = build_snapshot(self.corpus_b, self.snapshots_dir)
        publish_snapshot(self.snapshots_dir, snapshot_b)

        with patch("sys.stdout", new_callable=StringIO) as out:
            cli_main.handle_query("brand new data source")

        self.assertIn("A brand new data source added live.", out.getvalue())


if __name__ == "__main__":
    unittest.main()
