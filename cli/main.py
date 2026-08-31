"""Interactive CLI loop for the Sentence Autocomplete Engine."""

import os
from core.models import AutoCompleteData
from core.normalizer import normalize_text
from core.indexer import DataManager
from core.scoring import rank_candidates
import core.search_engine as search_engine

RESET_TOKEN = "#"

manager = DataManager()


def format_result(rank: int, result: AutoCompleteData) -> str:
    return (
        f"{rank}. {result.completed_sentence}"
        f"  [source: {result.source_text}, line {result.offset}, score: {result.score}]"
    )


def handle_query(query: str) -> None:
    normalized_query = normalize_text(query)
    # קריאה לפונקציית החיפוש
    matches = search_engine.search(query, manager) if hasattr(search_engine, 'search') else []
    results = rank_candidates(normalized_query, matches, manager.get_sentence)

    if not results:
        print("No matching sentences found.")
        return

    for rank, result in enumerate(results, start=1):
        print(format_result(rank, result))


def run_cli(data_dir: str = "Archive") -> None:
    print("Loading archive and building index, please wait...")
    if os.path.exists(data_dir):
        manager.load_data(data_dir)
    else:
        print(f"Warning: Directory '{data_dir}' not found.")

    print("Sentence Autocomplete Engine. Type '#' to reset the session, Ctrl+C to exit.\n")
    
    current_query = ""

    while True:
        try:
            prompt = f"{current_query}" if current_query else "> "
            user_input = input(prompt)
        except (EOFError, KeyboardInterrupt):
            print("\nExiting...")
            break

        if RESET_TOKEN in user_input:
            print("Session reset.")
            current_query = ""
            continue

        current_query += user_input

        if not current_query.strip():
            continue

        handle_query(current_query)


if __name__ == "__main__":
    run_cli()