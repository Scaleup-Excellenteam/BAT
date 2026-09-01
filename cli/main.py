"""Interactive CLI loop for the Sentence Autocomplete Engine."""

import os
from typing import Optional

from core.models import AutoCompleteData
from core.normalizer import normalize_text
from core.indexer import DataManager
from core.scoring import rank_candidates
import core.search_engine as search_engine
from cli.voice import review_voice_query
from services.speech import GoogleSpeechTranscriber, Transcriber
from services.gemini_speech import DEFAULT_GEMINI_MODEL, GeminiSpeechTranscriber

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


def run_cli(
    data_dir: str = "Archive",
    *,
    voice_language: str = "en-US",
    voice_provider: str = "gemini",
    voice_model: str = DEFAULT_GEMINI_MODEL,
    transcriber: Optional[Transcriber] = None,
) -> None:
    if voice_provider not in ("gemini", "cloud-speech"):
        raise ValueError("voice_provider must be gemini or cloud-speech")
    global manager
    manager = DataManager()
    print("Loading archive and building index, please wait...")
    if os.path.isdir(data_dir):
        manager.load_data(data_dir)
    else:
        print(f"Warning: Directory '{data_dir}' not found.")

    print("Sentence Autocomplete Engine. Type '#' to reset the session, Ctrl+C to exit.\n")
    print("Type /voice to search a recording, or /help for voice commands.")
    if transcriber is not None:
        voice_service = transcriber
    elif voice_provider == "gemini":
        voice_service = GeminiSpeechTranscriber(model=voice_model)
    else:
        voice_service = GoogleSpeechTranscriber()
    
    current_query = ""

    while True:
        try:
            prompt = f"{current_query}" if current_query else "> "
            user_input = input(prompt)
        except (EOFError, KeyboardInterrupt):
            print("\nExiting...")
            break

        command = user_input.strip()
        if command == "/help":
            print("/voice [WAV path] - transcribe, review, then start a new search query.")
            print("Voice accepts mono, 16-bit PCM WAV, up to 60 seconds and 10 MB.")
            print("Voice cancellation or failure keeps your current query. '#' resets typed input.")
            continue

        if command == "/voice" or command.startswith("/voice "):
            path = command[len("/voice"):].strip() or None
            confirmed_query = review_voice_query(voice_service, voice_language, path)
            if confirmed_query is not None:
                current_query = confirmed_query
                print(f"Searching: {current_query}")
                handle_query(current_query)
            continue

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
