"""Specification-based online completion tests over a bounded corpus."""

from __future__ import annotations

import pytest

from tests.system.adapter import get_best_k_completions
from tests.system.conftest import canonicalize_sample_results
from tests.system.oracle import CorpusLine, best_score, top_five


EDIT_SENTENCE = "qvwxabcdef"

QUERY_MATRIX = {
    "exact_long": "the python profilers",
    "sentence_middle": "deterministic profiling",
    "inside_word": "ternet protocol",
    "two_errors": "baze6x",
    "long_edit_after_trie_depth": "this document provydes a terminology",
}

PENALTY_CASES = [
    pytest.param("zvwxabcdef", 13, id="replacement-position-1"),
    pytest.param("qzwxabcdef", 14, id="replacement-position-2"),
    pytest.param("qvzxabcdef", 15, id="replacement-position-3"),
    pytest.param("qvwzabcdef", 16, id="replacement-position-4"),
    pytest.param("qvwxzbcdef", 17, id="replacement-position-5"),
    pytest.param("qvwxabcdez", 17, id="replacement-last-position"),
    pytest.param("zqvwxabcdef", 10, id="extra-position-1"),
    pytest.param("qzvwxabcdef", 12, id="extra-position-2"),
    pytest.param("qvzwxabcdef", 14, id="extra-position-3"),
    pytest.param("qvwzxabcdef", 16, id="extra-position-4"),
    pytest.param("qvwxzabcdef", 18, id="extra-position-5"),
    pytest.param("qvwxabcdefz", 18, id="extra-after-last-position"),
    pytest.param("qvxabcdef", 12, id="missing-position-3"),
    pytest.param("qvwabcdef", 14, id="missing-position-4"),
    pytest.param("qvwxbcdef", 16, id="missing-position-5"),
]

BOUNDARY_QUERIES = [
    pytest.param("wholelineuniquetoken", id="whole-source-line"),
    pytest.param("endboundaryuniquetoken", id="sentence-end"),
    pytest.param("mnrstuv", id="inside-word-exact"),
    pytest.param("mnrxtuv", id="inside-word-replacement"),
    pytest.param("qvwxabcde", id="shorter-query-is-exact-prefix"),
    pytest.param("wholelineuniquetokenzz", id="query-two-characters-too-long"),
]

SPEC_SCORE_CASES = [
    pytest.param("To be", 10, id="exact"),
    pytest.param("or Not", 12, id="case-insensitive"),
    pytest.param("be, that", 14, id="punctuation-normalized"),
    pytest.param("2o be", 3, id="replacement-position-1"),
    pytest.param("to pe", 6, id="replacement-position-4"),
    pytest.param("or knot", 8, id="extra-position-4"),
    pytest.param("or nt", 8, id="missing-position-5"),
    pytest.param("not be", None, id="more-than-one-edit"),
]


def test_bounded_corpus_uses_configured_offset_base(
    bounded_corpus: list[CorpusLine],
    offset_base: int,
) -> None:
    """Keep line numbering configurable because the specification is silent."""
    assert bounded_corpus[0].offset == offset_base


@pytest.mark.parametrize(("query", "expected_score"), SPEC_SCORE_CASES)
def test_oracle_reproduces_specification_examples(
    query: str,
    expected_score: int | None,
) -> None:
    """Lock the independent oracle to the specification's examples."""
    sentence = "To be or not to be, that is the question."
    assert best_score(query, sentence) == expected_score


@pytest.mark.parametrize("query", QUERY_MATRIX.values(), ids=QUERY_MATRIX.keys())
def test_realistic_top_five_matches_oracle(
    query: str,
    configured_sample_system: object,
    bounded_corpus: list[CorpusLine],
) -> None:
    """Compare BAT's complete ordered result with the bounded-corpus oracle."""
    del configured_sample_system
    expected = top_five(query, bounded_corpus)
    actual = canonicalize_sample_results(get_best_k_completions(query))
    assert actual == expected


@pytest.mark.parametrize(("query", "expected_target_score"), PENALTY_CASES)
def test_every_edit_penalty_band(
    query: str,
    expected_target_score: int,
    configured_sample_system: object,
    bounded_corpus: list[CorpusLine],
) -> None:
    """Check every specified edit-penalty band."""
    del configured_sample_system
    actual = canonicalize_sample_results(get_best_k_completions(query))
    assert actual == top_five(query, bounded_corpus)

    target = next(
        (result for result in actual if result.completed_sentence == EDIT_SENTENCE),
        None,
    )
    assert target is not None, "controlled penalty result was omitted from the top five"
    assert target.score == expected_target_score


@pytest.mark.parametrize("query", BOUNDARY_QUERIES)
def test_substring_and_sentence_boundaries(
    query: str,
    configured_sample_system: object,
    bounded_corpus: list[CorpusLine],
) -> None:
    """Check full-line, sentence-end, and inside-word substring matching."""
    del configured_sample_system
    actual = canonicalize_sample_results(get_best_k_completions(query))
    assert actual == top_five(query, bounded_corpus)


def test_normalization_variants_have_identical_top_five(
    configured_sample_system: object,
    bounded_corpus: list[CorpusLine],
) -> None:
    """Check case, punctuation, and whitespace normalization."""
    del configured_sample_system
    variants = (
        "normalization marker to be or not to be",
        "NORMALIZATION MARKER TO BE OR NOT TO BE",
        "  normalization   marker: to be, or not to be!!!  ",
        "normalization\tmarker to\tbe or   not to be",
    )
    expected = top_five(variants[0], bounded_corpus)
    for query in variants:
        assert top_five(query, bounded_corpus) == expected
        assert canonicalize_sample_results(get_best_k_completions(query)) == expected


def test_best_occurrence_within_sentence_sets_score(
    configured_sample_system: object,
    bounded_corpus: list[CorpusLine],
) -> None:
    """Prefer an exact occurrence over a corrected occurrence in one sentence."""
    del configured_sample_system
    query = "competitionuniquetoken"
    expected = top_five(query, bounded_corpus)
    actual = canonicalize_sample_results(get_best_k_completions(query))
    assert actual == expected
    assert actual[0].score == 2 * len(query)


def test_repeated_characters_use_highest_scoring_alignment(
    configured_sample_system: object,
    bounded_corpus: list[CorpusLine],
) -> None:
    """Choose the least-penalized correction when characters repeat."""
    del configured_sample_system
    query = "bookkeeperuniquetoken"
    expected = top_five(query, bounded_corpus)
    actual = canonicalize_sample_results(get_best_k_completions(query))
    assert actual == expected
    assert actual[0].score == 2 * len(query) - 4


def test_results_expose_required_fields(configured_sample_system: object) -> None:
    """Check the four required output fields and their basic types."""
    del configured_sample_system
    results = get_best_k_completions("uniquelysingleresulttoken")
    assert results
    for result in results:
        assert isinstance(result.completed_sentence, str)
        assert isinstance(result.source_text, str)
        assert isinstance(result.offset, int)
        assert isinstance(result.score, int)
