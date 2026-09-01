"""Coverage for core/snapshot_watcher.py - the online-side hot reload half of ZDT."""
import os
import shutil
import tempfile
import unittest
from unittest.mock import patch

from core.indexer import DataManager
from core.snapshot_store import build_snapshot, publish_snapshot
from core.snapshot_watcher import SnapshotWatcher


class TestSnapshotWatcher(unittest.TestCase):
    def setUp(self):
        self.work_dir = tempfile.mkdtemp()
        self.snapshots_dir = os.path.join(self.work_dir, "snapshots")

        self.corpus_a = os.path.join(self.work_dir, "corpus_a")
        os.makedirs(self.corpus_a)
        with open(os.path.join(self.corpus_a, "a.txt"), "w", encoding="utf-8") as f:
            f.write("To be or not to be.\n")

        self.corpus_b = os.path.join(self.work_dir, "corpus_b")
        os.makedirs(self.corpus_b)
        with open(os.path.join(self.corpus_b, "b.txt"), "w", encoding="utf-8") as f:
            f.write("A completely different sentence.\n")

    def tearDown(self):
        shutil.rmtree(self.work_dir)

    def _publish(self, corpus_dir: str) -> str:
        snapshot_id = build_snapshot(corpus_dir, self.snapshots_dir)
        publish_snapshot(self.snapshots_dir, snapshot_id)
        return snapshot_id

    def test_watcher_with_no_published_snapshot_returns_no_results(self):
        watcher = SnapshotWatcher(self.snapshots_dir)

        self.assertIsNone(watcher.current_snapshot_id)
        self.assertEqual(watcher.get_candidate_ids("to be"), set())
        self.assertIsNone(watcher.get_sentence(0))

    def test_watcher_serves_the_snapshot_published_before_it_was_created(self):
        snapshot_id = self._publish(self.corpus_a)

        watcher = SnapshotWatcher(self.snapshots_dir)

        self.assertEqual(watcher.current_snapshot_id, snapshot_id)
        sentence = watcher.get_sentence(0)
        self.assertIsNotNone(sentence)
        self.assertEqual(sentence.original_text, "To be or not to be.")

    def test_refresh_is_a_noop_when_pointer_has_not_changed(self):
        self._publish(self.corpus_a)
        watcher = SnapshotWatcher(self.snapshots_dir)

        with patch.object(DataManager, "load_data") as mock_load:
            changed = watcher.refresh()

        self.assertFalse(changed)
        mock_load.assert_not_called()

    def test_refresh_swaps_in_a_newly_published_snapshot_with_no_restart(self):
        self._publish(self.corpus_a)
        watcher = SnapshotWatcher(self.snapshots_dir)
        self.assertEqual(watcher.get_sentence(0).original_text, "To be or not to be.")

        second_id = self._publish(self.corpus_b)
        changed = watcher.refresh()

        self.assertTrue(changed)
        self.assertEqual(watcher.current_snapshot_id, second_id)
        self.assertEqual(watcher.get_sentence(0).original_text, "A completely different sentence.")

    def test_a_reference_held_before_refresh_keeps_serving_the_old_snapshot(self):
        # This is the actual zero-downtime property: an in-flight request
        # that already grabbed the manager before the swap must keep
        # reading the old snapshot's data - the swap must not mutate the
        # old object in place.
        self._publish(self.corpus_a)
        watcher = SnapshotWatcher(self.snapshots_dir)
        manager_before_swap = watcher._manager

        self._publish(self.corpus_b)
        watcher.refresh()

        self.assertEqual(manager_before_swap.get_sentence(0).original_text, "To be or not to be.")
        self.assertIsNot(manager_before_swap, watcher._manager)


if __name__ == "__main__":
    unittest.main()
