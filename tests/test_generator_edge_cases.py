"""Edge-case coverage for core.generator, beyond the ordinary-length-query
cases already covered in tests/test_search.py."""
from core.generator import QueryVariation, generate_variations


def test_generate_variations_empty_query_produces_only_single_character_insertions():
    variations = generate_variations("")

    # no positions to substitute or delete in an empty query - only a single
    # insertion point (index 0), one variation per alphabet character
    assert all(v.edit_type == "insertion" for v in variations)
    assert len(variations) == 27
    assert {v.text for v in variations} == set("abcdefghijklmnopqrstuvwxyz ")


def test_generate_variations_deletion_of_single_character_query_yields_empty_string():
    variations = generate_variations("a")

    deletions = [v for v in variations if v.edit_type == "deletion"]

    assert deletions == [QueryVariation("", "deletion", 1)]


def test_generate_variations_insertion_positions_span_one_through_length_plus_one():
    variations = generate_variations("cat")

    insertions = [v for v in variations if v.edit_type == "insertion"]

    assert {v.position for v in insertions} == {1, 2, 3, 4}
