"""Edge-case coverage for core.search_engine, beyond tests/test_search.py
and tests/test_search_integration.py."""
from typing import List, Optional, Set

from core.models import SentenceRecord
from core.search_engine import search


class FakeIndex:
    """Deliberately over-inclusive stand-in for core.indexer.DataManager -
    see the identical helper in tests/test_search.py for why that's a valid
    (if inefficient) implementation of the get_candidate_ids contract."""

    def __init__(self, sentences: List[SentenceRecord]):
        self._sentences = sentences

    def get_candidate_ids(self, query: str) -> Set[int]:
        if not query:
            return set()
        return {s.sentence_id for s in self._sentences}

    def get_sentence(self, sentence_id: int) -> Optional[SentenceRecord]:
        if 0 <= sentence_id < len(self._sentences):
            return self._sentences[sentence_id]
        return None


def _make_sentence(text: str, sentence_id: int = 0) -> SentenceRecord:
    return SentenceRecord(
        sentence_id=sentence_id,
        original_text=text,
        normalized_text=text,
        source_path="dummy.txt",
        offset=0,
    )


def test_search_does_not_deduplicate_matches_for_the_same_sentence():
    # search_engine explicitly documents that it doesn't deduplicate - a
    # query and its 1-edit variations can hit the same sentence more than
    # once. "aa" is reachable from "a" via more than one insertion variation
    # (inserting 'a' at position 1 or position 2), both landing on offset 0.
    sentence = _make_sentence("aa")
    index = FakeIndex([sentence])

    results = search("a", index)

    distinct_sentences = {r.sentence_id for r in results}
    assert len(results) > len(distinct_sentences)


def test_search_finds_match_at_the_end_of_a_sentence():
    sentence = _make_sentence("the cat sat")
    index = FakeIndex([sentence])

    results = search("sat", index)

    exact = [r for r in results if r.edit_type == "exact"]
    assert any(r.offset == len("the cat ") for r in exact)


def test_search_returns_no_matches_when_no_single_edit_bridges_query_to_corpus():
    sentence = _make_sentence("hello world")
    index = FakeIndex([sentence])

    # "zzz" cannot become any substring of "hello world" via a single
    # substitution, insertion, or deletion - no 2/3/4-length substring of
    # the sentence contains a 'z' at all.
    results = search("zzz", index)

    assert results == []
