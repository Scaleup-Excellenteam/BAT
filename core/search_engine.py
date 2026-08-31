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
"""
from dataclasses import dataclass
from typing import List, Optional, Protocol, Set

from core.generator import generate_variations
from core.models import SentenceRecord


class SupportsCandidateIndex(Protocol):
    def get_candidate_ids(self, query: str) -> Set[int]:
        ...

    def get_sentence(self, sentence_id: int) -> Optional[SentenceRecord]:
        ...


@dataclass(frozen=True)
class MatchCandidate:
    sentence: SentenceRecord
    offset: int
    match_length: int
    edit_type: str      # "exact" | "substitution" | "insertion" | "deletion"
    edit_position: int  # 1-based position in the query; 0 for exact matches


def search(query: str, index: SupportsCandidateIndex) -> List[MatchCandidate]:
    """Find every exact and 1-edit-fuzzy occurrence of query in the index."""
    candidates: List[MatchCandidate] = []

    candidates.extend(_find_occurrences(query, index, "exact", 0))

    for variation in generate_variations(query):
        candidates.extend(
            _find_occurrences(variation.text, index, variation.edit_type, variation.position)
        )

    return candidates


def _find_occurrences(
    text: str, index: SupportsCandidateIndex, edit_type: str, edit_position: int
) -> List[MatchCandidate]:
    matches: List[MatchCandidate] = []
    for sentence_id in index.get_candidate_ids(text):
        sentence = index.get_sentence(sentence_id)
        if sentence is None:
            continue
        for offset in _find_all_offsets(sentence.normalized_text, text):
            matches.append(MatchCandidate(sentence, offset, len(text), edit_type, edit_position))
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
