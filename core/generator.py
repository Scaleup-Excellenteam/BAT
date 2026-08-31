"""Generates every string within edit distance 1 of a normalized query.

A "1-edit" variation is produced by exactly one substitution, insertion, or
deletion applied to the query. Each variation records the edit type and the
1-based position (in the ORIGINAL query) where the edit occurred, since the
scoring penalties in core.scoring depend on that position.
"""
from dataclasses import dataclass
from typing import List

# Normalized text only ever contains lowercase letters and single spaces
# (see core.normalizer), so that is the alphabet edits are drawn from.
ALPHABET = "abcdefghijklmnopqrstuvwxyz "


@dataclass(frozen=True)
class QueryVariation:
    text: str
    edit_type: str  # "substitution" | "insertion" | "deletion"
    position: int   # 1-based index in the original query where the edit occurred


def generate_variations(query: str) -> List[QueryVariation]:
    """Return every 1-edit substitution/deletion/insertion variation of query."""
    variations: List[QueryVariation] = []
    variations.extend(_substitutions(query))
    variations.extend(_deletions(query))
    variations.extend(_insertions(query))
    return variations


def _substitutions(query: str) -> List[QueryVariation]:
    result = []
    for i, original_char in enumerate(query):
        for char in ALPHABET:
            if char != original_char:
                variant = query[:i] + char + query[i + 1:]
                result.append(QueryVariation(variant, "substitution", i + 1))
    return result


def _deletions(query: str) -> List[QueryVariation]:
    result = []
    for i in range(len(query)):
        variant = query[:i] + query[i + 1:]
        result.append(QueryVariation(variant, "deletion", i + 1))
    return result


def _insertions(query: str) -> List[QueryVariation]:
    result = []
    for i in range(len(query) + 1):
        for char in ALPHABET:
            variant = query[:i] + char + query[i:]
            result.append(QueryVariation(variant, "insertion", i + 1))
    return result
