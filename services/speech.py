"""Base speech models and audio utilities."""

from dataclasses import dataclass
import wave
import io


class VoiceInputError(Exception):
    """Base exception for voice transcription issues."""
    pass


class NoSpeechError(VoiceInputError):
    """Raised when audio contains no intelligible speech."""
    pass


@dataclass(frozen=True)
class AudioClip:
    content: bytes
    duration_seconds: float


@dataclass(frozen=True)
class Transcription:
    text: str
    language_code: str
    duration_seconds: float
    latency_seconds: float
    provider: str


def load_wav(path_or_bytes) -> AudioClip:
    """Loads and validates a WAV file from file path or bytes."""
    try:
        if isinstance(path_or_bytes, bytes):
            wav_file = io.BytesIO(path_or_bytes)
            raw_bytes = path_or_bytes
        else:
            with open(path_or_bytes, "rb") as f:
                raw_bytes = f.read()
            wav_file = io.BytesIO(raw_bytes)

        with wave.open(wav_file, "rb") as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            duration = frames / float(rate) if rate > 0 else 0.0

        return AudioClip(content=raw_bytes, duration_seconds=duration)
    except Exception as e:
        # אם זה לא wav תקין, מעבירים כ-clip גולמי
        if isinstance(path_or_bytes, bytes):
            return AudioClip(content=path_or_bytes, duration_seconds=0.0)
        raise VoiceInputError(f"Failed to read audio file: {e}")