"""Online query coordinator: combines exact and 1-edit fuzzy matching.

Expected contract from core.indexer (built during the offline phase):

    index.sentences: List[SentenceRecord]
        All indexed sentences, where sentences[i].sentence_id == i.

    index.get_candidate_ids(kmer: str) -> Set[int]
        Sentence ids whose normalized_text contains this k-mer, where
        k == KMER_SIZE. This is a narrowing filter only, built from an
        n-gram index - it is NOT a guarantee that the full search string
        matches, so search_engine still confirms every candidate with an
        exact substring check (and that's also how it recovers the offset).

KMER_SIZE must match whatever n-gram length core.indexer built its index
with - keep this constant in sync with dev 1's core/indexer.py.

search_engine does not deduplicate or rank candidates - a query and its
1-edit variations can match the same sentence more than once (e.g. via two
different edits, or the same edit at different offsets). Deduplication,
scoring and top-5 ranking happen downstream in core.scoring / cli.
"""
from dataclasses import dataclass
from typing import List, Protocol, Set

from core.generator import generate_variations
from core.models import SentenceRecord

KMER_SIZE = 4


class SupportsCandidateIndex(Protocol):
    sentences: List[SentenceRecord]

    def get_candidate_ids(self, kmer: str) -> Set[int]:
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
    for sentence_id in _candidate_sentence_ids(text, index):
        sentence = index.sentences[sentence_id]
        for offset in _find_all_offsets(sentence.normalized_text, text):
            matches.append(MatchCandidate(sentence, offset, len(text), edit_type, edit_position))
    return matches


def _candidate_sentence_ids(text: str, index: SupportsCandidateIndex) -> Set[int]:
    if len(text) < KMER_SIZE:
        # Too short to form a k-mer - the index can't narrow this down,
        # so fall back to checking every indexed sentence.
        return set(range(len(index.sentences)))

    kmers = (text[i:i + KMER_SIZE] for i in range(len(text) - KMER_SIZE + 1))
    candidate_ids: Set[int] = set()
    for i, kmer in enumerate(kmers):
        ids = index.get_candidate_ids(kmer)
        candidate_ids = ids if i == 0 else candidate_ids & ids
        if not candidate_ids:
            break
    return candidate_ids


def _find_all_offsets(haystack: str, needle: str) -> List[int]:
    offsets = []
    start = 0
    while True:
        offset = haystack.find(needle, start)
        if offset == -1:
            break
        offsets.append(offset)
        start = offset + 1
    return offsets
