from typing import List, Set

from core.generator import generate_variations
from core.models import SentenceRecord
from core.search_engine import KMER_SIZE, search


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
    """Stand-in for core.indexer's Index, matching its real contract:
    an n-gram candidate filter (get_candidate_ids) plus the sentence list -
    NOT a direct exact-match/offset lookup (that's search_engine's job)."""

    def __init__(self, sentences: List[SentenceRecord]):
        self.sentences = sentences
        self._kmer_to_ids: dict[str, Set[int]] = {}
        for sentence in sentences:
            text = sentence.normalized_text
            for i in range(len(text) - KMER_SIZE + 1):
                kmer = text[i:i + KMER_SIZE]
                self._kmer_to_ids.setdefault(kmer, set()).add(sentence.sentence_id)

    def get_candidate_ids(self, kmer: str) -> Set[int]:
        return self._kmer_to_ids.get(kmer, set())


def _make_sentence(text: str) -> SentenceRecord:
    return SentenceRecord(
        sentence_id=0,
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


def test_search_falls_back_to_full_scan_for_short_queries():
    # "hi" is shorter than KMER_SIZE, so no k-mer can be formed for it -
    # search must still find it via the full-scan fallback.
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
