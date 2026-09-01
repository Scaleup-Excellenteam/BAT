"""Filesystem hand-off between offline snapshot builds and online serving (ZDT).

Offline builds never touch the snapshot currently being served: each build
writes into its own new directory under `snapshots_dir`, instead of
overwriting the currently-active index in place. Only after a build is
validated does `publish_snapshot` flip a small `CURRENT` pointer file to it,
via write-to-a-temp-file-then-`os.replace`, so the flip itself is atomic -
a reader only ever sees the fully old or fully new pointer contents, never a
partial write. The online side (`core.snapshot_watcher.SnapshotWatcher`)
only ever reads this pointer, so a new data source can be built and
published while the service keeps running, with no restart and no dropped
requests.
"""

import os
import pickle
import time
from typing import Optional

from core.indexer import CACHE_FILE_NAME, DataManager

POINTER_FILE_NAME = "CURRENT"


class SnapshotValidationError(Exception):
    """Raised when a snapshot build or publish is refused because the data isn't usable."""


def build_snapshot(root_dir: str, snapshots_dir: str, kmer_size: int = 4) -> str:
    """Offline stage: index `root_dir` into a brand-new versioned snapshot directory.

    Returns the new snapshot id. Raises SnapshotValidationError, without
    creating a usable snapshot, if the build produced no sentences. Never
    reads or modifies the CURRENT pointer or any other snapshot - the
    currently-published snapshot (if any) keeps being served untouched
    until a later `publish_snapshot` call.
    """
    os.makedirs(snapshots_dir, exist_ok=True)
    snapshot_id = _new_snapshot_id(snapshots_dir)
    snapshot_dir = os.path.join(snapshots_dir, snapshot_id)
    os.makedirs(snapshot_dir)

    cache_path = os.path.join(snapshot_dir, CACHE_FILE_NAME)
    manager = DataManager(kmer_size=kmer_size, cache_file=cache_path)
    manager.load_data(root_dir)

    if not _cache_is_valid(cache_path):
        raise SnapshotValidationError(
            f"Build from '{root_dir}' produced no usable snapshot at '{snapshot_dir}'."
        )

    return snapshot_id


def publish_snapshot(snapshots_dir: str, snapshot_id: str) -> None:
    """Atomically mark `snapshot_id` as the snapshot the online side should serve.

    Refuses (raising SnapshotValidationError, without writing anything) to
    publish a snapshot that doesn't exist or doesn't validate. Otherwise
    writes the pointer to a temp file in `snapshots_dir` and `os.replace`s
    it into place - on POSIX this rename is atomic, so a concurrent reader
    of the pointer file never observes a half-written value.
    """
    cache_path = snapshot_cache_path(snapshots_dir, snapshot_id)
    if not _cache_is_valid(cache_path):
        raise SnapshotValidationError(f"Refusing to publish invalid snapshot '{snapshot_id}'.")

    pointer_path = os.path.join(snapshots_dir, POINTER_FILE_NAME)
    tmp_path = f"{pointer_path}.tmp.{os.getpid()}"
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(snapshot_id)
    os.replace(tmp_path, pointer_path)


def read_current_snapshot_id(snapshots_dir: str) -> Optional[str]:
    """Return the currently published snapshot id, or None if nothing has been published yet."""
    pointer_path = os.path.join(snapshots_dir, POINTER_FILE_NAME)
    try:
        with open(pointer_path, "r", encoding="utf-8") as f:
            snapshot_id = f.read().strip()
    except FileNotFoundError:
        return None
    return snapshot_id or None


def snapshot_cache_path(snapshots_dir: str, snapshot_id: str) -> str:
    """Path to the index cache file for `snapshot_id`, for loading it into a DataManager."""
    return os.path.join(snapshots_dir, snapshot_id, CACHE_FILE_NAME)


def _cache_is_valid(cache_path: str) -> bool:
    """A snapshot is valid if its cache file exists, unpickles, and has at least one sentence."""
    if not os.path.isfile(cache_path):
        return False
    try:
        with open(cache_path, "rb") as f:
            data = pickle.load(f)
    except Exception:
        return False
    return bool(data.get("sentences"))


def _new_snapshot_id(snapshots_dir: str) -> str:
    """A sortable, collision-avoiding id: a UTC timestamp, deduplicated if two builds race
    within the same second."""
    base = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    candidate = base
    suffix = 1
    while os.path.exists(os.path.join(snapshots_dir, candidate)):
        suffix += 1
        candidate = f"{base}-{suffix}"
    return candidate
