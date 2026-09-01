"""Google Speech-to-Text adapter; importing BAT never requires Google packages.

Only transcribe() contacts Google. Keep this adapter independent of search so
the confirmed transcript can later feed translation or other query modes.
"""

import io
import math
import time
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


MAX_AUDIO_BYTES = 10_000_000
MAX_DURATION_SECONDS = 60


class VoiceInputError(Exception):
    """An actionable error that the CLI can display without an API traceback."""


class InvalidAudioError(VoiceInputError):
    """The local recording cannot be sent to the short-audio recognizer."""


class NoSpeechError(VoiceInputError):
    """The service returned no usable transcript."""


@dataclass(frozen=True)
class AudioClip:
    content: bytes
    sample_rate_hertz: int
    duration_seconds: float


@dataclass(frozen=True)
class Transcription:
    text: str
    language_code: str
    duration_seconds: float
    elapsed_seconds: float
    provider: str = "Google Cloud Speech-to-Text"


class Transcriber(Protocol):
    def transcribe(self, path: str, language_code: str = "en-US") -> Transcription:
        ...


def load_wav(path: str) -> AudioClip:
    """Validate a bounded, mono, 16-bit PCM WAV before making any API call."""
    try:
        audio_path = Path(path).expanduser()
        if not audio_path.is_file():
            raise InvalidAudioError("Recording not found. Choose an existing WAV file.")
        with audio_path.open("rb") as recording:
            content = recording.read(MAX_AUDIO_BYTES + 1)
    except (OSError, ValueError) as exc:
        raise InvalidAudioError("Cannot read this recording. Check the path and file permissions.") from exc

    if len(content) > MAX_AUDIO_BYTES:
        raise InvalidAudioError("Recording is too large. Choose a WAV file smaller than 10 MB.")

    try:
        with wave.open(io.BytesIO(content), "rb") as recording:
            if (
                recording.getnchannels() != 1
                or recording.getsampwidth() != 2
                or recording.getcomptype() != "NONE"
            ):
                raise InvalidAudioError("Use a mono WAV recording with 16-bit PCM audio.")
            sample_rate = recording.getframerate()
            if not 8000 <= sample_rate <= 48000:
                raise InvalidAudioError("Use a WAV sample rate between 8,000 and 48,000 Hz.")
            frame_count = recording.getnframes()
            if frame_count == 0:
                raise InvalidAudioError("The recording is empty. Record some speech first.")
            if frame_count > MAX_DURATION_SECONDS * sample_rate:
                raise InvalidAudioError("Recording is too long. Use at most 60 seconds of audio.")
            frames = recording.readframes(frame_count)
            if len(frames) != frame_count * 2:
                raise InvalidAudioError("The WAV recording is incomplete. Export or record it again.")
    except (wave.Error, EOFError, OSError) as exc:
        raise InvalidAudioError("Invalid WAV file. Export the recording as mono, 16-bit PCM WAV.") from exc

    return AudioClip(content, sample_rate, frame_count / sample_rate)


def _extract_transcript(response) -> str:
    """Join the best alternative from each consecutive recognition segment."""
    try:
        parts = []
        for result in response.results:
            if not result.alternatives:
                continue
            text = result.alternatives[0].transcript
            if not isinstance(text, str):
                raise TypeError("Transcript must be text")
            if text.strip():
                parts.append(text.strip())
    except (AttributeError, TypeError, ValueError) as exc:
        raise VoiceInputError("The speech service returned an invalid response. Please try again.") from exc

    transcript = " ".join(parts)
    if not transcript:
        raise NoSpeechError("No speech was recognized. Try a clearer recording or type your query.")
    return transcript


class GoogleSpeechTranscriber:
    """Transcribe short WAV files with Google Cloud Speech-to-Text V1.

    The SDK and ADC credentials are loaded on the first voice request. A client
    can be supplied for tests. Automatic request retries are disabled to avoid
    repeated uploads and keep interactive failures predictable.
    """

    def __init__(self, client=None, timeout_seconds: float = 20.0):
        if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be a positive, finite number")
        self._client = client
        self.timeout_seconds = timeout_seconds

    def transcribe(self, path: str, language_code: str = "en-US") -> Transcription:
        clip = load_wav(path)
        language_code = language_code.strip()
        if not language_code:
            raise VoiceInputError("Choose a speech language code, for example en-US.")

        try:
            from google.api_core import exceptions as api_errors
            from google.auth import exceptions as auth_errors
            from google.cloud import speech_v1 as speech
        except ImportError as exc:
            raise VoiceInputError(
                "Voice dependencies are missing. Run: python -m pip install -r requirements-voice.txt"
            ) from exc

        started = time.perf_counter()
        try:
            if self._client is None:
                self._client = speech.SpeechClient()
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=clip.sample_rate_hertz,
                audio_channel_count=1,
                language_code=language_code,
                max_alternatives=1,
                enable_automatic_punctuation=True,
            )
            response = self._client.recognize(
                config=config,
                audio=speech.RecognitionAudio(content=clip.content),
                timeout=self.timeout_seconds,
                retry=None,
            )
        except (auth_errors.DefaultCredentialsError, auth_errors.RefreshError, api_errors.Unauthenticated) as exc:
            raise VoiceInputError(
                "Google credentials are missing or expired. Follow docs/VOICE_SETUP.md to sign in."
            ) from exc
        except api_errors.PermissionDenied as exc:
            raise VoiceInputError(
                "Google denied access. Check Speech-to-Text API access, project permissions, and billing."
            ) from exc
        except (api_errors.DeadlineExceeded, TimeoutError) as exc:
            raise VoiceInputError("Transcription timed out. Try again or type your query.") from exc
        except api_errors.ResourceExhausted as exc:
            raise VoiceInputError("Speech quota is exhausted. Check the project quota or use typed search.") from exc
        except api_errors.InvalidArgument as exc:
            raise VoiceInputError("Google rejected the request. Check the speech language and audio format.") from exc
        except (api_errors.GoogleAPICallError, api_errors.RetryError, auth_errors.TransportError, OSError) as exc:
            raise VoiceInputError("The speech service is unavailable. Try again or type your query.") from exc

        text = _extract_transcript(response)
        return Transcription(text, language_code, clip.duration_seconds, time.perf_counter() - started)
