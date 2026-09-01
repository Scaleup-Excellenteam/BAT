"""Independent bounded-corpus oracle for autocomplete system tests."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import string


_PUNCTUATION = frozenset(string.punctuation)


@dataclass(frozen=True, slots=True)
class CorpusLine:
    """One original line selected for the bounded corpus."""

    sentence: str
    source_text: str
    offset: int


@dataclass(frozen=True, slots=True)
class OracleResult:
    """One independently calculated autocomplete result."""

    completed_sentence: str
    source_text: str
    offset: int
    score: int


def normalize_for_oracle(text: str) -> str:
    """Normalize text without calling production normalization code.

    Args:
        text: Raw query or sentence.

    Returns:
        Lowercase text with ASCII punctuation and repeated whitespace removed.
    """
    without_punctuation = "".join(
        character for character in text.lower() if character not in _PUNCTUATION
    )
    return " ".join(without_punctuation.split())


def _replacement_penalty(position: int) -> int:
    """Return the substitution penalty for a one-based position.

    Args:
        position: One-based edit position.

    Returns:
        Required substitution penalty.
    """
    return (5, 4, 3, 2)[position - 1] if position <= 4 else 1


def _length_edit_penalty(position: int) -> int:
    """Return the insertion/deletion penalty for a one-based position.

    Args:
        position: One-based edit position.

    Returns:
        Required insertion/deletion penalty.
    """
    return (10, 8, 6, 4)[position - 1] if position <= 4 else 2


def _score_at_start(query: str, sentence: str, start: int) -> int | None:
    """Find the best query score at one sentence character position.

    Args:
        query: Normalized non-empty query.
        sentence: Normalized sentence.
        start: Character position at which matching begins.

    Returns:
        Best valid score at this position, or ``None`` for no match.
    """
    query_length = len(query)
    suffix = sentence[start:]
    scores: list[int] = []

    same_length = suffix[:query_length]
    if len(same_length) == query_length:
        mismatches = [
            index
            for index, (query_char, sentence_char) in enumerate(
                zip(query, same_length, strict=True)
            )
            if query_char != sentence_char
        ]
        if not mismatches:
            scores.append(2 * query_length)
        elif len(mismatches) == 1:
            position = mismatches[0] + 1
            scores.append(
                2 * (query_length - 1) - _replacement_penalty(position)
            )

    if query_length > 1:
        shorter_target = suffix[: query_length - 1]
        if len(shorter_target) == query_length - 1:
            for deleted_index in range(query_length):
                if query[:deleted_index] + query[deleted_index + 1 :] == shorter_target:
                    position = deleted_index + 1
                    scores.append(
                        2 * (query_length - 1) - _length_edit_penalty(position)
                    )

    longer_target = suffix[: query_length + 1]
    if len(longer_target) == query_length + 1:
        for inserted_index in range(query_length + 1):
            if (
                longer_target[:inserted_index] + longer_target[inserted_index + 1 :]
                == query
            ):
                position = inserted_index + 1
                scores.append(2 * query_length - _length_edit_penalty(position))

    return max(scores) if scores else None


def best_score(query: str, sentence: str) -> int | None:
    """Calculate the best valid substring score for one sentence.

    Args:
        query: Raw user query.
        sentence: Raw original sentence.

    Returns:
        Highest valid exact or one-edit score, or ``None``.
    """
    normalized_query = normalize_for_oracle(query)
    normalized_sentence = normalize_for_oracle(sentence)
    if not normalized_query:
        return None

    scores = (
        _score_at_start(normalized_query, normalized_sentence, start)
        for start in range(len(normalized_sentence))
    )
    valid_scores = [score for score in scores if score is not None]
    return max(valid_scores) if valid_scores else None


def rank_all(query: str, corpus: list[CorpusLine]) -> list[OracleResult]:
    """Independently rank every valid occurrence in the bounded corpus.

    Args:
        query: Raw user query.
        corpus: Selected original source lines.

    Returns:
        All valid results in deterministic system-test order.
    """
    results = []
    for line in corpus:
        score = best_score(query, line.sentence)
        if score is not None:
            results.append(
                OracleResult(
                    completed_sentence=line.sentence,
                    source_text=line.source_text,
                    offset=line.offset,
                    score=score,
                )
            )
    return sorted(
        results,
        key=lambda result: (
            -result.score,
            result.completed_sentence,
        ),
    )


def top_five(query: str, corpus: list[CorpusLine]) -> list[OracleResult]:
    """Return the independently calculated top five results.

    Args:
        query: Raw user query.
        corpus: Selected original source lines.

    Returns:
        At most five deterministic oracle results.
    """
    return rank_all(query, corpus)[:5]


def read_bounded_corpus(
    corpus_dir: Path,
    relative_files: list[str],
    max_non_empty_lines: int,
    offset_base: int = 0,
) -> list[CorpusLine]:
    """Read exactly the lines represented by the saved sample cache.

    Args:
        corpus_dir: Root directory containing copied sample files.
        relative_files: Stable manifest paths in registry order.
        max_non_empty_lines: Per-file non-empty-line cap.
        offset_base: Whether physical source-line offsets start at zero or one.

    Returns:
        Selected original lines with Archive-relative source paths.
    """
    if offset_base not in (0, 1):
        raise ValueError("offset_base must be 0 or 1")

    corpus: list[CorpusLine] = []
    for relative_file in relative_files:
        path = corpus_dir / relative_file
        selected = 0
        with path.open(encoding="utf-8", errors="replace") as stream:
            for offset, raw_line in enumerate(stream):
                if not raw_line.strip():
                    continue
                corpus.append(
                    CorpusLine(
                        sentence=raw_line.rstrip("\r\n"),
                        source_text=f"Archive/{relative_file}",
                        offset=offset + offset_base,
                    )
                )
                selected += 1
                if selected == max_non_empty_lines:
                    break
    return corpus
