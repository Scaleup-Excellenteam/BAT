"""Offline service tests: real SDK request/response types, mocked network client."""

import builtins
import wave
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from google.api_core import exceptions as api_errors
from google.auth import exceptions as auth_errors
from google.cloud import speech_v1 as speech

from services.speech import GoogleSpeechTranscriber, InvalidAudioError, NoSpeechError, VoiceInputError, load_wav


def write_wav(path, *, seconds=0.05, rate=16000, channels=1, width=2):
    with wave.open(str(path), "wb") as recording:
        recording.setnchannels(channels)
        recording.setsampwidth(width)
        recording.setframerate(rate)
        recording.writeframes(b"\0" * (int(seconds * rate) * channels * width))
    return str(path)


@pytest.fixture
def wav_path(tmp_path):
    # Synthetic silence tests the WAV container only; it is never sent online.
    return write_wav(tmp_path / "recording.wav")


def response(*segments):
    return speech.RecognizeResponse(
        results=[speech.SpeechRecognitionResult(alternatives=[speech.SpeechRecognitionAlternative(transcript=s)]) for s in segments]
    )


def test_service_sends_actual_wav_metadata_and_combines_segments(wav_path):
    client = Mock()
    client.recognize.return_value = response("To be", "or not.")
    transcript = GoogleSpeechTranscriber(client, timeout_seconds=7).transcribe(wav_path)
    assert transcript.text == "To be or not."
    assert transcript.duration_seconds == pytest.approx(0.05)
    assert transcript.elapsed_seconds >= 0
    assert transcript.language_code == "en-US"
    kwargs = client.recognize.call_args.kwargs
    assert kwargs["config"].sample_rate_hertz == 16000
    assert kwargs["config"].encoding == speech.RecognitionConfig.AudioEncoding.LINEAR16
    assert kwargs["config"].audio_channel_count == 1
    assert kwargs["audio"].content.startswith(b"RIFF")
    assert kwargs["timeout"] == 7
    assert kwargs["retry"] is None
    request = speech.RecognizeRequest(config=kwargs["config"], audio=kwargs["audio"])
    assert speech.RecognizeRequest.deserialize(speech.RecognizeRequest.serialize(request)) == request


def test_selected_language_is_sent_without_translating_transcript(wav_path):
    client = Mock()
    client.recognize.return_value = response("שלום")
    result = GoogleSpeechTranscriber(client).transcribe(wav_path, "he-IL")
    assert result.text == "שלום"
    assert client.recognize.call_args.kwargs["config"].language_code == "he-IL"


@pytest.mark.parametrize("sdk_response", [response(), response("  "), speech.RecognizeResponse(results=[speech.SpeechRecognitionResult()])])
def test_no_transcript_is_reported_as_no_speech(wav_path, sdk_response):
    client = Mock()
    client.recognize.return_value = sdk_response
    with pytest.raises(NoSpeechError, match="No speech"):
        GoogleSpeechTranscriber(client).transcribe(wav_path)


@pytest.mark.parametrize("sdk_response", [None, SimpleNamespace(results=None), SimpleNamespace(results=[SimpleNamespace(alternatives=[SimpleNamespace(transcript=42)])])])
def test_malformed_response_is_rejected(wav_path, sdk_response):
    client = Mock()
    client.recognize.return_value = sdk_response
    with pytest.raises(VoiceInputError, match="invalid response"):
        GoogleSpeechTranscriber(client).transcribe(wav_path)


@pytest.mark.parametrize("failure, message", [
    (api_errors.DeadlineExceeded("private details"), "timed out"),
    (TimeoutError("private details"), "timed out"),
    (api_errors.ServiceUnavailable("private details"), "unavailable"),
    (api_errors.ResourceExhausted("private details"), "quota"),
    (api_errors.PermissionDenied("private details"), "denied access"),
    (api_errors.InvalidArgument("private details"), "rejected"),
    (api_errors.Unauthenticated("private details"), "credentials"),
    (auth_errors.RefreshError("private details"), "credentials"),
    (auth_errors.TransportError("private details"), "unavailable"),
])
def test_service_errors_have_actionable_messages(wav_path, failure, message):
    client = Mock()
    client.recognize.side_effect = failure
    with pytest.raises(VoiceInputError, match=message) as caught:
        GoogleSpeechTranscriber(client).transcribe(wav_path)
    assert "private details" not in str(caught.value)
    assert client.recognize.call_count == 1


def test_missing_credentials_are_handled_during_client_creation(wav_path, monkeypatch):
    monkeypatch.setattr(speech, "SpeechClient", Mock(side_effect=auth_errors.DefaultCredentialsError("missing")))
    with pytest.raises(VoiceInputError, match="credentials"):
        GoogleSpeechTranscriber().transcribe(wav_path)


def test_missing_optional_sdk_gives_install_instruction(wav_path, monkeypatch):
    real_import = builtins.__import__
    def import_without_google(name, *args, **kwargs):
        if name.startswith("google."):
            raise ImportError("not installed")
        return real_import(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", import_without_google)
    with pytest.raises(VoiceInputError, match="requirements-voice.txt"):
        GoogleSpeechTranscriber().transcribe(wav_path)


@pytest.mark.parametrize("options,message", [
    ({"seconds": 0}, "empty"),
    ({"seconds": 60.01, "rate": 8000}, "too long"),
    ({"channels": 2}, "mono"),
    ({"width": 1}, "16-bit"),
    ({"rate": 4000}, "sample rate"),
    ({"rate": 96000}, "sample rate"),
])
def test_unsupported_audio_is_rejected_before_upload(tmp_path, options, message):
    path = write_wav(tmp_path / "unsupported.wav", **options)
    client = Mock()
    with pytest.raises(InvalidAudioError, match=message):
        GoogleSpeechTranscriber(client).transcribe(path)
    client.recognize.assert_not_called()


def test_audio_duration_boundary_is_accepted(tmp_path):
    path = write_wav(tmp_path / "boundary.wav", seconds=60, rate=8000)
    assert load_wav(path).duration_seconds == 60


def test_large_file_is_rejected_before_upload(tmp_path):
    path = tmp_path / "large.wav"
    with path.open("wb") as f:
        f.truncate(10_000_001)
    with pytest.raises(InvalidAudioError, match="too large"):
        load_wav(str(path))


def test_missing_file_and_directory_are_rejected(tmp_path):
    for path in (tmp_path / "missing.wav", tmp_path):
        with pytest.raises(InvalidAudioError, match="not found"):
            load_wav(str(path))


def test_random_bytes_are_not_treated_as_audio(tmp_path):
    path = tmp_path / "invalid.wav"
    path.write_bytes(b"This is not a recording")
    with pytest.raises(InvalidAudioError, match="Invalid WAV"):
        load_wav(str(path))


def test_truncated_pcm_data_is_rejected(wav_path):
    path = Path(wav_path)
    path.write_bytes(path.read_bytes()[:-10])
    with pytest.raises(InvalidAudioError, match="incomplete"):
        load_wav(str(path))


def test_permission_error_is_actionable(wav_path, monkeypatch):
    monkeypatch.setattr(Path, "open", Mock(side_effect=PermissionError("private details")))
    with pytest.raises(InvalidAudioError, match="permissions"):
        load_wav(wav_path)
