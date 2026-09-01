"""Online query coordinator: combines exact and 1-edit fuzzy matching.

Expected contract from core.indexer.DataManager (built during the offline
phase - see core/indexer.py on feature/offline-indexer):

    index.get_candidate_ids(query: str) -> Set[int]
        Sentence ids that might contain `query` as a substring. This is a
        narrowing filter only (internally keyed off query's first few
        characters, with a full-scan fallback for short queries) - it is
        NOT a guarantee that the full string matches, so search_engine
        still confirms every candidate with an exact substring check
        (and that's also how it recovers the match offset).

    index.get_sentence(sentence_id: int) -> Optional[SentenceRecord]
        O(1) lookup of a sentence by id.

search_engine does not deduplicate or rank candidates - a query and its
1-edit variations can match the same sentence more than once (e.g. via two
different edits, or the same edit at different offsets). Deduplication,
scoring and top-5 ranking happen downstream in core.scoring / cli.

Fuzzy variations are only generated and checked if the exact match alone
doesn't already cover MIN_RESULTS distinct sentences - exact matches always
score at least as high as a fuzzy match of the same query, so there's no
ranking benefit to paying for 1-edit variation generation once we already
have enough.

MatchCandidate's shape (sentence_id, edit_type, edit_position) is the
contract core.scoring.rank_candidates consumes - see core/scoring.py.
"""
from dataclasses import dataclass
from typing import List, Optional, Protocol, Set

from core.generator import generate_variations
from core.models import SentenceRecord
from core.normalizer import normalize_text

MIN_RESULTS = 5


class SupportsCandidateIndex(Protocol):
    def get_candidate_ids(self, query: str) -> Set[int]:
        ...

    def get_sentence(self, sentence_id: int) -> Optional[SentenceRecord]:
        ...


@dataclass(frozen=True)
class MatchCandidate:
    sentence_id: int
    offset: int
    match_length: int
    edit_type: str                # "exact" | "substitution" | "insertion" | "deletion"
    edit_position: Optional[int]  # 1-based position in the query; None for exact matches


def search(query: str, index: SupportsCandidateIndex) -> List[MatchCandidate]:
    """Find exact matches for query, falling back to 1-edit-fuzzy matches
    only if the exact match doesn't already cover MIN_RESULTS sentences."""
    normalized_query = normalize_text(query)
    if not normalized_query:
        return []

    candidates = _find_occurrences(normalized_query, index, "exact", None)
    if len({c.sentence_id for c in candidates}) >= MIN_RESULTS:
        return candidates

    for variation in generate_variations(normalized_query):
        candidates.extend(
            _find_occurrences(variation.text, index, variation.edit_type, variation.position)
        )

    return candidates


def _find_occurrences(
    text: str, index: SupportsCandidateIndex, edit_type: str, edit_position: Optional[int]
) -> List[MatchCandidate]:
    matches: List[MatchCandidate] = []
    for sentence_id in index.get_candidate_ids(text):
        sentence = index.get_sentence(sentence_id)
        if sentence is None:
            continue
        for offset in _find_all_offsets(sentence.normalized_text, text):
            matches.append(MatchCandidate(sentence_id, offset, len(text), edit_type, edit_position))
    return matches


def _find_all_offsets(haystack: str, needle: str) -> List[int]:
    if not needle:
        return []
    offsets = []
    start = 0
    while True:
        offset = haystack.find(needle, start)
        if offset == -1:
            break
        offsets.append(offset)
        start = offset + 1
    return offsets
