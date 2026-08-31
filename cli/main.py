"""Interactive CLI loop for the Sentence Autocomplete Engine."""

from core.models import AutoCompleteData
from core.normalizer import normalize_text
from core.scoring import rank_candidates

import data_manager
import search_engine

RESET_TOKEN = "#"


def format_result(rank: int, result: AutoCompleteData) -> str:
    return (
        f"{rank}. {result.completed_sentence}"
        f"  [source: {result.source_text}, line {result.offset}, score: {result.score}]"
    )


def handle_query(query: str) -> None:
    normalized_query = normalize_text(query)
    matches = search_engine.search(query)
    results = rank_candidates(normalized_query, matches, data_manager.get_sentence)

    if not results:
        print("No matching sentences found.")
        return

    for rank, result in enumerate(results, start=1):
        print(format_result(rank, result))


def run_cli() -> None:
    print("Sentence Autocomplete Engine. Type '#' to reset the session, Ctrl+C to exit.")
    while True:
        try:
            query = input("> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if query == RESET_TOKEN:
            print("Session reset.")
            continue

        if not query.strip():
            continue

        handle_query(query)


if __name__ == "__main__":
    run_cli()
