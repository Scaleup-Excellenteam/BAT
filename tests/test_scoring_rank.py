"""Additional coverage for core.scoring.

tests/test_scoring.py (pre-existing) is actually a duplicate copy of
core/scoring.py's source and contains no test functions at all - pytest
collects zero tests from it. This file adds real coverage for
get_penalty/calculate_score/rank_candidates without touching that file.
"""
from types import SimpleNamespace

from core.models import SentenceRecord
from core.scoring import calculate_score, get_penalty, rank_candidates


def test_get_penalty_with_no_error_type_is_zero():
    assert get_penalty(None, None) == 0


def test_get_penalty_substitution_table_positions_one_to_four():
    assert get_penalty("substitution", 1) == 5
    assert get_penalty("substitution", 2) == 4
    assert get_penalty("substitution", 3) == 3
    assert get_penalty("substitution", 4) == 2


def test_get_penalty_insertion_and_deletion_table_positions_one_to_four():
    for position, expected in [(1, 10), (2, 8), (3, 6), (4, 4)]:
        assert get_penalty("insertion", position) == expected
        assert get_penalty("deletion", position) == expected


def test_calculate_score_exact_match_is_double_the_query_length():
    assert calculate_score(5, None, None) == 10


def test_calculate_score_matches_readme_substitution_example():
    # README: query "20 be" vs sentence "...To be..." -> substituted at
    # position 1 -> (2 * 4) - 5 = 3
    assert calculate_score(5, "substitution", 1) == 3


def _record(text, sentence_id=0):
    return SentenceRecord(
        sentence_id=sentence_id,
        original_text=text,
        normalized_text=text.lower(),
        source_path="f.txt",
        offset=1,
    )


def test_rank_candidates_keeps_the_higher_score_for_duplicate_sentences():
    record = _record("to be or not to be", 0)
    matches = [
        SimpleNamespace(sentence_id=0, error_type="substitution", error_index=1),
        SimpleNamespace(sentence_id=0, error_type=None, error_index=None),  # exact: higher score
    ]

    results = rank_candidates("to be", matches, {0: record}.get)

    assert len(results) == 1
    assert results[0].score == 10  # 2 * len("to be"), the exact-match score


def test_rank_candidates_sorts_by_score_then_lexicographically():
    record_a = _record("Alpha sentence", 0)
    record_b = _record("Beta sentence", 1)
    matches = [
        SimpleNamespace(sentence_id=0, error_type=None, error_index=None),
        SimpleNamespace(sentence_id=1, error_type="deletion", error_index=1),
    ]

    results = rank_candidates("alpha", matches, {0: record_a, 1: record_b}.get)

    assert [r.completed_sentence for r in results] == ["Alpha sentence", "Beta sentence"]


def test_rank_candidates_skips_matches_with_no_resolvable_sentence():
    matches = [SimpleNamespace(sentence_id=999, error_type=None, error_index=None)]

    results = rank_candidates("anything", matches, lambda _id: None)

    assert results == []
