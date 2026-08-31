from dataclasses import dataclass
from typing import Optional

import pytest

from core.models import SentenceRecord
from core.scoring import rank_candidates, score_match


@dataclass
class FakeMatch:
    """Stand-in for whatever `search_engine.search()` yields."""

    sentence_id: int
    edit_type: str
    edit_position: Optional[int] = None


class TestScoreMatch:
    def test_exact_match_full_score(self):
        assert score_match(5, "exact", None) == 2 * 5

    @pytest.mark.parametrize(
        "position,expected_penalty",
        [(1, 5), (2, 4), (3, 3), (4, 2), (5, 1), (6, 1)],
    )
    def test_substitution_penalty_by_position(self, position, expected_penalty):
        query_length = 6
        matching_chars = query_length - 1
        expected = 2 * matching_chars - expected_penalty
        assert score_match(query_length, "substitution", position) == expected

    @pytest.mark.parametrize(
        "position,expected_penalty",
        [(1, 10), (2, 8), (3, 6), (4, 4), (5, 2), (7, 2)],
    )
    def test_insertion_penalty_by_position(self, position, expected_penalty):
        query_length = 7
        matching_chars = query_length - 1
        expected = 2 * matching_chars - expected_penalty
        assert score_match(query_length, "insertion", position) == expected

    @pytest.mark.parametrize(
        "position,expected_penalty",
        [(1, 10), (2, 8), (3, 6), (4, 4), (5, 2), (9, 2)],
    )
    def test_deletion_penalty_by_position(self, position, expected_penalty):
        query_length = 5
        matching_chars = query_length
        expected = 2 * matching_chars - expected_penalty
        assert score_match(query_length, "deletion", position) == expected

    def test_unknown_edit_type_raises(self):
        with pytest.raises(ValueError):
            score_match(3, "transposition", 1)


def _make_record(sentence_id, original, source_path="book.txt", offset=0):
    return SentenceRecord(
        sentence_id=sentence_id,
        original_text=original,
        normalized_text=original.lower(),
        source_path=source_path,
        offset=offset,
    )


class TestRankCandidates:
    def test_sorts_by_score_descending(self):
        records = {
            1: _make_record(1, "Cat sat.", offset=1),
            2: _make_record(2, "Cbt sat.", offset=2),
        }
        matches = [
            FakeMatch(1, "exact"),
            FakeMatch(2, "substitution", edit_position=1),
        ]
        results = rank_candidates("cat", matches, records.get)
        assert [r.completed_sentence for r in results] == ["Cat sat.", "Cbt sat."]
        assert results[0].score > results[1].score

    def test_ties_broken_lexicographically(self):
        records = {
            1: _make_record(1, "Zebra cat.", offset=1),
            2: _make_record(2, "Apple cat.", offset=2),
        }
        matches = [FakeMatch(1, "exact"), FakeMatch(2, "exact")]
        results = rank_candidates("cat", matches, records.get)
        assert results[0].score == results[1].score
        assert [r.completed_sentence for r in results] == ["Apple cat.", "Zebra cat."]

    def test_deduplicates_same_sentence_keeping_best_score(self):
        # Same sentence found via two different variations/ids;
        # one is an exact match, the other only via a substitution.
        records = {
            1: _make_record(1, "The cat sat.", offset=5),
            2: _make_record(1, "The cat sat.", offset=5),
        }
        matches = [
            FakeMatch(1, "substitution", edit_position=2),
            FakeMatch(2, "exact"),
        ]
        results = rank_candidates("cat", matches, records.get)
        assert len(results) == 1
        assert results[0].score == 2 * 3

    def test_limits_to_top_five(self):
        records = {i: _make_record(i, f"Sentence {i} cat.", offset=i) for i in range(10)}
        matches = [FakeMatch(i, "exact") for i in range(10)]
        results = rank_candidates("cat", matches, records.get)
        assert len(results) == 5

    def test_no_matches_returns_empty_list(self):
        results = rank_candidates("cat", [], lambda sentence_id: None)
        assert results == []

    def test_output_fields_map_from_sentence_record(self):
        records = {1: _make_record(1, "The cat sat.", source_path="a/b.txt", offset=42)}
        matches = [FakeMatch(1, "exact")]
        results = rank_candidates("cat", matches, records.get)
        result = results[0]
        assert result.completed_sentence == "The cat sat."
        assert result.source_text == "a/b.txt"
        assert result.offset == 42
        assert result.score == 2 * 3
