"""Review voice input before it can reach the search engine."""

from typing import Optional

from core.normalizer import normalize_text
from services.speech import Transcriber, VoiceInputError


def review_voice_query(
    transcriber: Transcriber,
    language_code: str = "en-US",
    path: Optional[str] = None,
) -> Optional[str]:
    """Return a confirmed full query, or None on cancellation/failure.

    No search is performed here. Translation can be inserted by the caller
    after confirmation without coupling transcription to translation.
    """
    try:
        print("Voice input: the selected recording will be sent to Google for transcription.")
        if path is None:
            path = input("WAV file path (Enter to cancel): ").strip()
        else:
            path = path.strip()
        if not path or path == "/cancel":
            print("Voice input cancelled.")
            return None
        # Windows 'Copy as path' includes quotes; keep backslashes and spaces.
        if len(path) >= 2 and path[0] == path[-1] and path[0] in ("'", '"'):
            path = path[1:-1]

        print(f"Transcribing ({language_code})...")
        result = transcriber.transcribe(path, language_code)
        print(f"Transcription provider: {result.provider}")
        print(f"Transcript: {result.text}")
        print(f"Transcription time: {result.elapsed_seconds:.2f}s")

        while True:
            replacement = input("Enter to search, type corrected text, or /cancel: ")
            if replacement.strip() == "/cancel":
                print("Voice input cancelled.")
                return None
            query = replacement.strip() if replacement.strip() else result.text.strip()
            if not normalize_text(query):
                print("Enter text containing searchable characters, or /cancel.")
                continue
            return query
    except VoiceInputError as exc:
        print(f"Voice input failed: {exc}")
        return None
    except (EOFError, KeyboardInterrupt):
        print("\nVoice input cancelled.")
        return None
