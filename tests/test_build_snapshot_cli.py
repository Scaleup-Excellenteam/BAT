"""Coverage for cli/build_snapshot.py - the offline entrypoint of the ZDT hand-off."""
import os
import shutil
import tempfile
import unittest
from io import StringIO
from unittest.mock import patch

import cli.build_snapshot as build_snapshot_cli
from core.snapshot_store import read_current_snapshot_id


class TestBuildSnapshotCli(unittest.TestCase):
    def setUp(self):
        self.work_dir = tempfile.mkdtemp()
        self.corpus_dir = os.path.join(self.work_dir, "corpus")
        self.snapshots_dir = os.path.join(self.work_dir, "snapshots")
        os.makedirs(self.corpus_dir)
        with open(os.path.join(self.corpus_dir, "a.txt"), "w", encoding="utf-8") as f:
            f.write("A brand new data source line.\n")

    def tearDown(self):
        shutil.rmtree(self.work_dir)

    def test_main_builds_and_publishes_a_snapshot_from_a_valid_corpus(self):
        exit_code = build_snapshot_cli.main([self.corpus_dir, self.snapshots_dir])

        self.assertEqual(exit_code, 0)
        self.assertIsNotNone(read_current_snapshot_id(self.snapshots_dir))

    def test_main_reports_the_published_snapshot_id(self):
        with patch("sys.stdout", new_callable=StringIO) as out:
            build_snapshot_cli.main([self.corpus_dir, self.snapshots_dir])

        snapshot_id = read_current_snapshot_id(self.snapshots_dir)
        self.assertIn(snapshot_id, out.getvalue())

    def test_main_does_not_publish_when_corpus_has_no_usable_sentences(self):
        empty_corpus = os.path.join(self.work_dir, "empty")
        os.makedirs(empty_corpus)

        exit_code = build_snapshot_cli.main([empty_corpus, self.snapshots_dir])

        self.assertNotEqual(exit_code, 0)
        self.assertIsNone(read_current_snapshot_id(self.snapshots_dir))

    def test_main_returns_usage_error_when_arguments_are_missing(self):
        exit_code = build_snapshot_cli.main([self.corpus_dir])

        self.assertEqual(exit_code, 2)


if __name__ == "__main__":
    unittest.main()
