from typing import List, Optional, Set

from core.generator import generate_variations
from core.models import SentenceRecord
from core.search_engine import search


def test_generate_variations_substitution():
    variations = generate_variations("ab")
    subs = [v for v in variations if v.edit_type == "substitution"]
    assert any(v.text == "cb" and v.position == 1 for v in subs)
    assert any(v.text == "ac" and v.position == 2 for v in subs)
    # 25 other letters + space, minus itself, for each of the 2 positions
    assert len(subs) == 2 * 26


def test_generate_variations_deletion():
    variations = generate_variations("ab")
    deletions = [v for v in variations if v.edit_type == "deletion"]
    assert {(v.text, v.position) for v in deletions} == {("b", 1), ("a", 2)}


def test_generate_variations_insertion():
    variations = generate_variations("ab")
    insertions = [v for v in variations if v.edit_type == "insertion"]
    assert any(v.text == "cab" and v.position == 1 for v in insertions)
    assert any(v.text == "acb" and v.position == 2 for v in insertions)
    assert any(v.text == "abc" and v.position == 3 for v in insertions)
    # 27 possible chars, at each of len+1=3 positions
    assert len(insertions) == 27 * 3


def test_generate_variations_no_duplicated_original():
    variations = generate_variations("a")
    assert all(v.text != "a" for v in variations)


class FakeIndex:
    """Deliberately over-inclusive stand-in for core.indexer.DataManager.

    The real get_candidate_ids narrows down by a k-mer of the query, but
    returning every sentence id is still a valid (if inefficient)
    implementation of the same contract - it's a candidate filter, not a
    verified match. This isolates these tests to search_engine's own
    confirm+offset+tag logic rather than DataManager's indexing details."""

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


def test_search_finds_exact_match():
    sentence = _make_sentence("to be or not to be")
    index = FakeIndex([sentence])

    results = search("to be", index)

    exact = [r for r in results if r.edit_type == "exact"]
    assert len(exact) == 2
    assert {r.offset for r in exact} == {0, 13}
    assert all(r.match_length == len("to be") for r in exact)
    assert all(r.edit_position == 0 for r in exact)


def test_search_finds_substitution_match():
    sentence = _make_sentence("to be or not to be")
    index = FakeIndex([sentence])

    # "to pe" is a 1-substitution variation of "to be" (b -> p at position 4)
    results = search("to pe", index)

    substitutions = [r for r in results if r.edit_type == "substitution"]
    assert any(
        r.offset == 0 and r.edit_position == 4 and r.match_length == 5
        for r in substitutions
    )


def test_search_finds_deletion_match():
    sentence = _make_sentence("or not")
    index = FakeIndex([sentence])

    # "or knot" has an extra 'k' at position 4 that must be deleted to match
    results = search("or knot", index)

    deletions = [r for r in results if r.edit_type == "deletion"]
    assert any(r.offset == 0 and r.edit_position == 4 for r in deletions)


def test_search_finds_insertion_match():
    sentence = _make_sentence("or not")
    index = FakeIndex([sentence])

    # "or nt" is missing the 'o' at position 5, which must be inserted to match
    results = search("or nt", index)

    insertions = [r for r in results if r.edit_type == "insertion"]
    assert any(r.offset == 0 and r.edit_position == 5 for r in insertions)


def test_search_finds_short_query():
    # DataManager handles short queries (< kmer_size) with its own
    # full-scan fallback - search_engine just needs to pass them through
    # and confirm the match like any other candidate.
    sentence = _make_sentence("well hi there")
    index = FakeIndex([sentence])

    results = search("hi", index)

    exact = [r for r in results if r.edit_type == "exact"]
    assert any(r.offset == 5 for r in exact)


def test_search_no_match_returns_empty_for_unrelated_sentences():
    sentence = _make_sentence("completely unrelated text")
    index = FakeIndex([sentence])

    results = search("xyzzy", index)

    assert results == []


def test_search_normalizes_the_raw_query():
    sentence = _make_sentence("to be or not to be")
    index = FakeIndex([sentence])

    # search() must normalize the raw query itself, same as normalize_text
    # would - it shouldn't rely on the caller having already done it.
    results = search("  To, Be!!  ", index)

    exact = [r for r in results if r.edit_type == "exact"]
    assert any(r.offset == 0 for r in exact)


def test_search_skips_fuzzy_variations_once_exact_has_enough_results():
    sentences = [_make_sentence(f"a cat sat number {i}", sentence_id=i) for i in range(5)]
    index = FakeIndex(sentences)

    results = search("cat", index)

    assert len({r.sentence.sentence_id for r in results}) == 5
    assert all(r.edit_type == "exact" for r in results)
