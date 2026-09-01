"""Offline entrypoint: build a new snapshot from a corpus directory and publish it.

Usage:
    python -m cli.build_snapshot <root_dir> <snapshots_dir>

This is the whole offline side of the zero-downtime hand-off. Point it at a
directory of `.txt` files - a newly added data source, dropped in locally
or synced in remotely - and a `snapshots_dir` shared with the running
service, and it builds a new versioned snapshot, validates it, and only
then atomically flips the CURRENT pointer to it. It never touches the
snapshot that's already published unless the new build is proven good, and
the already-running service picks up the change on its own (see
`core.snapshot_watcher.SnapshotWatcher`) - no restart required.
"""

import sys
from typing import List, Optional

from core.snapshot_store import SnapshotValidationError, build_snapshot, publish_snapshot

USAGE = "Usage: python -m cli.build_snapshot <root_dir> <snapshots_dir>"


def main(argv: Optional[List[str]] = None) -> int:
    """Build and publish a snapshot. Returns a process exit code."""
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2:
        print(USAGE)
        return 2

    root_dir, snapshots_dir = argv
    try:
        snapshot_id = build_snapshot(root_dir, snapshots_dir)
    except SnapshotValidationError as err:
        print(f"[build_snapshot] Build failed validation, nothing published: {err}")
        return 1

    publish_snapshot(snapshots_dir, snapshot_id)
    print(f"[build_snapshot] Published snapshot '{snapshot_id}' from '{root_dir}'.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
