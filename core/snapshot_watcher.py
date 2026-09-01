"""Online-side hot reload: watches the snapshot pointer and swaps snapshots live (ZDT).

`SnapshotWatcher` wraps a `DataManager` and exposes the same
`get_candidate_ids`/`get_sentence` surface `core.search_engine.search` and
`core.scoring.rank_candidates` already expect (see
`core.search_engine.SupportsCandidateIndex`), so it's a drop-in replacement
for a bare `DataManager` wherever the online service reads the index.

`refresh()` is the only place it touches the filesystem: it re-reads the
`CURRENT` pointer and, only if it changed, loads the new snapshot into a
brand-new `DataManager` and swaps it in with a single attribute assignment.
That assignment is the entire "swap" - a caller that already read
`self._manager` (directly, or via a `get_candidate_ids`/`get_sentence` call
already in progress) keeps working against the pre-swap `DataManager`
undisturbed, since that object is never mutated in place. Only calls that
happen *after* the assignment see the new snapshot. So a request already
being served keeps being served by the old snapshot, and the service never
needs to stop or restart for the swap.
"""

import os
from typing import List, Optional, Set

from core.indexer import DataManager
from core.models import SentenceRecord
from core.snapshot_store import read_current_snapshot_id, snapshot_cache_path


class SnapshotWatcher:
    """Serves the currently published snapshot under `snapshots_dir`, live-reloading on change."""

    def __init__(self, snapshots_dir: str, kmer_size: int = 4):
        self.snapshots_dir = snapshots_dir
        self.kmer_size = kmer_size
        self._manager: Optional[DataManager] = None
        self._loaded_snapshot_id: Optional[str] = None
        self.refresh()

    def refresh(self) -> bool:
        """Reload if a newer snapshot has been published since the last load.

        Returns True if it swapped in a new snapshot, False if the
        currently-published snapshot is already the one loaded (the common
        case - this makes it cheap enough to call before every query).
        """
        snapshot_id = read_current_snapshot_id(self.snapshots_dir)
        if snapshot_id is None or snapshot_id == self._loaded_snapshot_id:
            return False

        cache_path = snapshot_cache_path(self.snapshots_dir, snapshot_id)
        new_manager = DataManager(kmer_size=self.kmer_size, cache_file=cache_path)
        # root_dir is unused here: the cache file for this snapshot already
        # exists on disk, so load_data takes its cache-hit path and never
        # rescans a source directory.
        new_manager.load_data(os.path.dirname(cache_path))

        self._manager = new_manager
        self._loaded_snapshot_id = snapshot_id
        return True

    @property
    def current_snapshot_id(self) -> Optional[str]:
        return self._loaded_snapshot_id

    @property
    def sentences(self) -> List[SentenceRecord]:
        return self._manager.sentences if self._manager is not None else []

    def get_candidate_ids(self, query: str) -> Set[int]:
        if self._manager is None:
            return set()
        return self._manager.get_candidate_ids(query)

    def get_sentence(self, sentence_id: int) -> Optional[SentenceRecord]:
        if self._manager is None:
            return None
        return self._manager.get_sentence(sentence_id)
