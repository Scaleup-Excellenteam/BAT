"""Test-only adapter from BAT's public pipeline to the assignment API."""

from types import SimpleNamespace

from core.indexer import DataManager
from core.models import AutoCompleteData
from core.normalizer import normalize_text
from core.scoring import rank_candidates
from core.search_engine import search


_manager: DataManager | None = None


def configure_adapter(manager: DataManager) -> None:
    """Configure the BAT data manager used by bounded completion requests."""
    global _manager
    _manager = manager


def get_best_k_completions(prefix: str) -> list[AutoCompleteData]:
    """Exercise BAT's existing search and ranking path without changing it."""
    if _manager is None:
        raise RuntimeError("BAT system-test adapter is not configured")

    matches = search(prefix, _manager)
    adapted_matches = [
        SimpleNamespace(
            sentence_id=match.sentence_id,
            error_type=None if match.edit_type == "exact" else match.edit_type,
            error_index=match.edit_position,
        )
        for match in matches
    ]
    return rank_candidates(
        normalize_text(prefix),
        adapted_matches,
        _manager.get_sentence,
        top_k=5,
    )
