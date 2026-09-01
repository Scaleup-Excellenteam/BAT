"""Gemini audio transcription, independent of search and Cloud Speech billing."""

import json
import math
import os
import re
import time

from services.speech import NoSpeechError, Transcription, VoiceInputError, load_wav

DEFAULT_GEMINI_MODEL = "gemini-3.6-flash"


def _extract_transcript(response) -> str:
    """Extract and validate text transcript from Gemini response."""
    try:
        if not response or not response.text:
            raise VoiceInputError("Gemini returned no transcript. Try another recording or type your query.")
        
        text = response.text.strip()
        # ניקוי פורמט JSON או Markdown במידה והוחזר
        if text.startswith("```json"):
            text = text.removeprefix("```json").removesuffix("```").strip()
        elif text.startswith("```"):
            text = text.removeprefix("```").removesuffix("```").strip()

        try:
            payload = json.loads(text)
            if isinstance(payload, dict) and "transcript" in payload:
                text = str(payload["transcript"]).strip()
        except Exception:
            pass

    except Exception as exc:
        raise VoiceInputError("Gemini returned an invalid transcript. Please try again or type your query.") from exc

    if not text:
        raise NoSpeechError("No speech was recognized. Try a clearer recording or type your query.")
    return text


class GeminiSpeechTranscriber:
    """Send short WAV audio to the Gemini API using GEMINI_API_KEY."""

    def __init__(self, client=None, *, model: str = DEFAULT_GEMINI_MODEL, timeout_seconds: float = 45.0):
        self._client = client
        self.model = model.strip()
        self.timeout_seconds = timeout_seconds

    def transcribe(self, path: str, language_code: str = "en-US") -> Transcription:
        clip = load_wav(path)
        language_code = language_code.strip() if language_code else "en-US"

        try:
            from google import genai
            from google.genai import errors, types
        except ImportError as exc:
            raise VoiceInputError("Gemini dependencies missing. Run: pip install google-genai") from exc

        api_key = os.environ.get("GEMINI_API_KEY", "").strip()
        if self._client is None and not api_key:
            raise VoiceInputError("Set GEMINI_API_KEY in your environment or .env file.")

        started = time.perf_counter()
        options = types.HttpOptions(
            timeout=max(1, math.ceil(self.timeout_seconds * 1000)),
        )

        prompt = (
            f"Transcribe only the intelligible speech in the supplied recording verbatim. "
            f"Expected spoken language: {language_code}. "
            f"Do not translate, summarize, or explain. Return only the raw transcribed text."
        )

        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text=prompt),
                    types.Part.from_bytes(data=clip.content, mime_type="audio/wav"),
                ],
            )
        ]

        try:
            if self._client is not None:
                response = self._client.models.generate_content(
                    model=self.model,
                    contents=contents,
                )
            else:
                with genai.Client(api_key=api_key, http_options=options) as client:
                    response = client.models.generate_content(
                        model=self.model,
                        contents=contents,
                    )
        except Exception as exc:
            raise VoiceInputError(f"Transcription request failed: {exc}") from exc

        text = _extract_transcript(response)
        return Transcription(
            text=text,
            language_code=language_code,
            duration_seconds=clip.duration_seconds,
            latency_seconds=time.perf_counter() - started,
            provider="Gemini (AI-generated)",
        )