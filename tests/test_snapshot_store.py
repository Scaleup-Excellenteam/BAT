"""Coverage for core/snapshot_store.py - the offline->filesystem hand-off (ZDT)."""
import os
import shutil
import tempfile
import unittest

from core.snapshot_store import (
    SnapshotValidationError,
    build_snapshot,
    publish_snapshot,
    read_current_snapshot_id,
    snapshot_cache_path,
)


class TestBuildSnapshot(unittest.TestCase):
    def setUp(self):
        self.work_dir = tempfile.mkdtemp()
        self.corpus_dir = os.path.join(self.work_dir, "corpus")
        self.snapshots_dir = os.path.join(self.work_dir, "snapshots")
        os.makedirs(self.corpus_dir)
        with open(os.path.join(self.corpus_dir, "a.txt"), "w", encoding="utf-8") as f:
            f.write("To be or not to be.\n")

    def tearDown(self):
        shutil.rmtree(self.work_dir)

    def test_build_snapshot_creates_new_versioned_directory_with_cache(self):
        snapshot_id = build_snapshot(self.corpus_dir, self.snapshots_dir)

        snapshot_dir = os.path.join(self.snapshots_dir, snapshot_id)
        self.assertTrue(os.path.isdir(snapshot_dir))
        self.assertTrue(os.path.isfile(snapshot_cache_path(self.snapshots_dir, snapshot_id)))

    def test_build_snapshot_does_not_touch_existing_pointer(self):
        first_id = build_snapshot(self.corpus_dir, self.snapshots_dir)
        publish_snapshot(self.snapshots_dir, first_id)

        build_snapshot(self.corpus_dir, self.snapshots_dir)

        # A second build must never move the pointer on its own - only
        # publish_snapshot is allowed to do that.
        self.assertEqual(read_current_snapshot_id(self.snapshots_dir), first_id)

    def test_build_snapshot_raises_on_empty_corpus(self):
        empty_corpus = os.path.join(self.work_dir, "empty")
        os.makedirs(empty_corpus)

        with self.assertRaises(SnapshotValidationError):
            build_snapshot(empty_corpus, self.snapshots_dir)

    def test_build_snapshot_ids_are_unique_even_within_the_same_second(self):
        first_id = build_snapshot(self.corpus_dir, self.snapshots_dir)
        second_id = build_snapshot(self.corpus_dir, self.snapshots_dir)

        self.assertNotEqual(first_id, second_id)


class TestPublishAndReadPointer(unittest.TestCase):
    def setUp(self):
        self.work_dir = tempfile.mkdtemp()
        self.corpus_dir = os.path.join(self.work_dir, "corpus")
        self.snapshots_dir = os.path.join(self.work_dir, "snapshots")
        os.makedirs(self.corpus_dir)
        with open(os.path.join(self.corpus_dir, "a.txt"), "w", encoding="utf-8") as f:
            f.write("Hello there.\n")

    def tearDown(self):
        shutil.rmtree(self.work_dir)

    def test_read_current_snapshot_id_returns_none_when_nothing_published(self):
        self.assertIsNone(read_current_snapshot_id(self.snapshots_dir))

    def test_publish_snapshot_makes_it_the_current_snapshot(self):
        snapshot_id = build_snapshot(self.corpus_dir, self.snapshots_dir)

        publish_snapshot(self.snapshots_dir, snapshot_id)

        self.assertEqual(read_current_snapshot_id(self.snapshots_dir), snapshot_id)

    def test_publish_snapshot_leaves_no_leftover_temp_files(self):
        snapshot_id = build_snapshot(self.corpus_dir, self.snapshots_dir)

        publish_snapshot(self.snapshots_dir, snapshot_id)

        leftovers = [name for name in os.listdir(self.snapshots_dir) if ".tmp." in name]
        self.assertEqual(leftovers, [])

    def test_publish_snapshot_refuses_nonexistent_snapshot_id(self):
        with self.assertRaises(SnapshotValidationError):
            publish_snapshot(self.snapshots_dir, "does-not-exist")

        self.assertIsNone(read_current_snapshot_id(self.snapshots_dir))

    def test_publish_snapshot_can_move_pointer_forward_to_a_later_build(self):
        first_id = build_snapshot(self.corpus_dir, self.snapshots_dir)
        publish_snapshot(self.snapshots_dir, first_id)

        second_id = build_snapshot(self.corpus_dir, self.snapshots_dir)
        publish_snapshot(self.snapshots_dir, second_id)

        self.assertEqual(read_current_snapshot_id(self.snapshots_dir), second_id)


if __name__ == "__main__":
    unittest.main()
