"""Scoring, deduplication and ranking for autocomplete candidates.

Score = (2 * matching_chars) - penalty, where only correctly matching
characters earn points and at most one edit (substitution, insertion or
deletion) separates the query from a candidate sentence.

This module does not re-derive the alignment itself: it consumes the
edit classification already produced by `search_engine.search(query)`.
Each item yielded by that call must expose:

    sentence_id:   int
    edit_type:     "exact" | "substitution" | "insertion" | "deletion"
    edit_position: int | None
                   1-based position in the *normalized query* where the
                   edit occurred (the substituted/inserted char, or the
                   query position a missing char belongs at). None when
                   edit_type == "exact".

This is the contract `core/search_engine.py` (Developer 2) must satisfy.
"""

from typing import Callable, Dict, Iterable, List, Optional, Protocol

from core.models import AutoCompleteData, SentenceRecord

_SUBSTITUTION_PENALTIES = {1: 5, 2: 4, 3: 3, 4: 2}
_INSERTION_DELETION_PENALTIES = {1: 10, 2: 8, 3: 6, 4: 4}
_DEFAULT_SUBSTITUTION_PENALTY = 1
_DEFAULT_INSERTION_DELETION_PENALTY = 2


def _substitution_penalty(position: int) -> int:
    return _SUBSTITUTION_PENALTIES.get(position, _DEFAULT_SUBSTITUTION_PENALTY)


def _insertion_deletion_penalty(position: int) -> int:
    return _INSERTION_DELETION_PENALTIES.get(position, _DEFAULT_INSERTION_DELETION_PENALTY)


class MatchCandidate(Protocol):
    """Expected shape of items yielded by `search_engine.search(query)`."""

    sentence_id: int
    edit_type: str
    edit_position: Optional[int]


def score_match(query_length: int, edit_type: str, edit_position: Optional[int]) -> int:
    """Score a single candidate match per the scoring spec.

    matching_chars and the penalty bucket are fully determined by the
    edit type, the query length and the 1-based position of the edit -
    no text scanning required.
    """
    if edit_type == "exact":
        return 2 * query_length

    if edit_type == "substitution":
        matching_chars = query_length - 1
        return 2 * matching_chars - _substitution_penalty(edit_position)

    if edit_type == "insertion":
        # Query has one extra character the sentence does not have.
        matching_chars = query_length - 1
        return 2 * matching_chars - _insertion_deletion_penalty(edit_position)

    if edit_type == "deletion":
        # Query is missing a character the sentence has.
        matching_chars = query_length
        return 2 * matching_chars - _insertion_deletion_penalty(edit_position)

    raise ValueError(f"Unknown edit_type: {edit_type!r}")


def rank_candidates(
    normalized_query: str,
    matches: Iterable[MatchCandidate],
    get_sentence: Callable[[int], SentenceRecord],
    limit: int = 5,
) -> List[AutoCompleteData]:
    """Score, deduplicate and rank matches from `search_engine.search()`.

    Deduplicates by completed sentence text (keeping the highest score),
    sorts by score descending then lexicographically by sentence, and
    returns at most `limit` results as `AutoCompleteData`.
    """
    query_length = len(normalized_query)
    best_by_sentence: Dict[str, AutoCompleteData] = {}

    for match in matches:
        record = get_sentence(match.sentence_id)
        score = score_match(query_length, match.edit_type, match.edit_position)

        existing = best_by_sentence.get(record.original_text)
        if existing is None or score > existing.score:
            best_by_sentence[record.original_text] = AutoCompleteData(
                completed_sentence=record.original_text,
                source_text=record.source_path,
                offset=record.offset,
                score=score,
            )

    ranked = sorted(
        best_by_sentence.values(),
        key=lambda item: (-item.score, item.completed_sentence),
    )
    return ranked[:limit]
