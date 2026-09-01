"""Online query coordinator: combines exact and 1-edit fuzzy matching with TypoCache prioritization."""

from dataclasses import dataclass
from typing import List, Optional, Protocol, Set

from core.generator import generate_variations
from core.models import SentenceRecord
from core.normalizer import normalize_text
from core.typo_cache import TypoCache

MIN_RESULTS = 5

# מופע גלובלי של שמירת ותיעדוף תיקוני הקלדה
typo_cache = TypoCache()


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
    edit_type: str
    edit_position: Optional[int]
    matched_variant: Optional[str] = None  # מעקב אחר הווריאציה שנמצאה בפועל


def search(query: str, index: SupportsCandidateIndex) -> List[MatchCandidate]:
    """Find exact matches, falling back to 1-edit variations prioritized by TypoCache."""
    normalized_query = normalize_text(query)

    candidates = _find_occurrences(normalized_query, index, "exact", None)
    if len({c.sentence_id for c in candidates}) >= MIN_RESULTS:
        return candidates

    variations = generate_variations(normalized_query)
    # מתן עדיפות לשגיאות שנלמדו מחיפושים קודמים
    prioritized_variations = typo_cache.prioritize(normalized_query, variations)

    for variation in prioritized_variations:
        new_matches = _find_occurrences(
            variation.text, index, variation.edit_type, variation.position
        )
        if new_matches:
            # שמירת השגיאה והתיקון לחיפושים הבאים
            typo_cache.record_match(normalized_query, variation.text)
            candidates.extend(new_matches)

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
            matches.append(
                MatchCandidate(
                    sentence_id=sentence_id,
                    offset=offset,
                    match_length=len(text),
                    edit_type=edit_type,
                    edit_position=edit_position,
                    matched_variant=text,
                )
            )
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