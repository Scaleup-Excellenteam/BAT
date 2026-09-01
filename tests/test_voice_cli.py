"""Transcript review, recovery, and real search integration without cloud calls."""

from unittest.mock import Mock

import pytest

import cli.main as cli
from cli.voice import review_voice_query
from services.speech import Transcription, VoiceInputError


@pytest.fixture
def transcriber():
    service = Mock()
    service.transcribe.return_value = Transcription("to pe", "en-US", 1.0, 0.2)
    return service


def feed_input(monkeypatch, *values):
    inputs = iter(values)
    def next_input(prompt):
        try:
            value = next(inputs)
        except StopIteration:
            raise EOFError
        if isinstance(value, BaseException):
            raise value
        return value
    monkeypatch.setattr("builtins.input", next_input)


def test_enter_accepts_transcript(transcriber, monkeypatch, capsys):
    feed_input(monkeypatch, "")
    assert review_voice_query(transcriber, path="recording.wav") == "to pe"
    assert "Transcript: to pe" in capsys.readouterr().out


def test_edit_replaces_transcript_before_search(transcriber, monkeypatch):
    feed_input(monkeypatch, "to be")
    assert review_voice_query(transcriber, path="recording.wav") == "to be"


def test_cancel_after_transcription(transcriber, monkeypatch):
    feed_input(monkeypatch, "/cancel")
    assert review_voice_query(transcriber, path="recording.wav") is None


def test_empty_path_cancels_without_contacting_service(transcriber, monkeypatch):
    feed_input(monkeypatch, "")
    assert review_voice_query(transcriber) is None
    transcriber.transcribe.assert_not_called()


def test_quoted_windows_path_preserves_spaces_and_backslashes(transcriber, monkeypatch):
    feed_input(monkeypatch, '"C:\\Users\\Aws\\My recordings\\query.wav"', "")
    review_voice_query(transcriber)
    transcriber.transcribe.assert_called_once_with(r"C:\Users\Aws\My recordings\query.wav", "en-US")


def test_punctuation_only_transcript_requires_correction(transcriber, monkeypatch, capsys):
    transcriber.transcribe.return_value = Transcription("!!!", "en-US", 1, 0.2)
    feed_input(monkeypatch, "", "to be")
    assert review_voice_query(transcriber, path="recording.wav") == "to be"
    assert "searchable characters" in capsys.readouterr().out


@pytest.mark.parametrize("interruption", [KeyboardInterrupt(), EOFError()])
def test_interruption_cancels_review(transcriber, monkeypatch, interruption):
    feed_input(monkeypatch, interruption)
    assert review_voice_query(transcriber, path="recording.wav") is None


def test_failure_returns_to_typed_input(transcriber, capsys):
    transcriber.transcribe.side_effect = VoiceInputError("Transcription timed out.")
    assert review_voice_query(transcriber, path="recording.wav") is None
    assert "timed out" in capsys.readouterr().out


@pytest.fixture
def corpus(tmp_path):
    (tmp_path / "hamlet.txt").write_text("To be or not to be, that is the question.\n", encoding="utf-8")
    return str(tmp_path)


def test_confirmed_voice_query_uses_real_search_and_source(corpus, transcriber, monkeypatch, capsys):
    feed_input(monkeypatch, "/voice recording.wav", "")
    cli.run_cli(corpus, transcriber=transcriber)
    output = capsys.readouterr().out
    assert "Transcript: to pe" in output
    assert "To be or not to be, that is the question." in output
    assert "hamlet.txt, line 1, score: 6" in output


def test_corrected_voice_and_typed_queries_have_same_results(corpus, transcriber, monkeypatch, capsys):
    feed_input(monkeypatch, "/voice recording.wav", "to be", "#", "to be")
    cli.run_cli(corpus, transcriber=transcriber)
    output = capsys.readouterr().out
    result_lines = [line for line in output.splitlines() if line.startswith("1. ")]
    assert len(result_lines) == 2
    assert result_lines[0] == result_lines[1]
    assert "score: 10" in result_lines[0]


def test_successful_voice_starts_new_query_and_typed_input_can_extend_it(corpus, transcriber, monkeypatch):
    handle = Mock()
    monkeypatch.setattr(cli, "handle_query", handle)
    feed_input(monkeypatch, "old query", "/voice recording.wav", "to be", " or not")
    cli.run_cli(corpus, transcriber=transcriber)
    assert [c.args[0] for c in handle.call_args_list] == ["old query", "to be", "to be or not"]


@pytest.mark.parametrize("failure", [False, True])
def test_cancel_or_failure_keeps_current_query(corpus, transcriber, monkeypatch, failure):
    handle = Mock()
    monkeypatch.setattr(cli, "handle_query", handle)
    if failure:
        transcriber.transcribe.side_effect = VoiceInputError("Service unavailable")
        inputs = ("to ", "/voice recording.wav", "be")
    else:
        inputs = ("to ", "/voice recording.wav", "/cancel", "be")
    feed_input(monkeypatch, *inputs)
    cli.run_cli(corpus, transcriber=transcriber)
    assert [c.args[0] for c in handle.call_args_list] == ["to ", "to be"]


def test_typed_flow_reset_and_help_do_not_call_speech(corpus, transcriber, monkeypatch):
    handle = Mock()
    monkeypatch.setattr(cli, "handle_query", handle)
    feed_input(monkeypatch, "to ", "be", "/help", "#", "or not")
    cli.run_cli(corpus, transcriber=transcriber)
    assert [c.args[0] for c in handle.call_args_list] == ["to ", "to be", "or not"]
    transcriber.transcribe.assert_not_called()


def test_hash_in_recording_filename_is_not_treated_as_session_reset(corpus, transcriber, monkeypatch):
    feed_input(monkeypatch, '/voice "take #1.wav"', "")
    cli.run_cli(corpus, transcriber=transcriber)
    transcriber.transcribe.assert_called_once_with("take #1.wav", "en-US")


def test_gemini_transcript_is_labeled_and_corrected_before_search(corpus, transcriber, monkeypatch, capsys):
    transcriber.transcribe.return_value = Transcription("to pe", "en-US", 1, 0.2, provider="Gemini (AI-generated)")
    gemini_factory = Mock(return_value=transcriber)
    cloud_factory = Mock()
    monkeypatch.setattr(cli, "GeminiSpeechTranscriber", gemini_factory)
    monkeypatch.setattr(cli, "GoogleSpeechTranscriber", cloud_factory)
    feed_input(monkeypatch, "/voice recording.wav", "to be")
    cli.run_cli(corpus)
    output = capsys.readouterr().out
    assert "Gemini (AI-generated)" in output
    assert "Searching: to be" in output
    assert "hamlet.txt, line 1, score: 10" in output
    gemini_factory.assert_called_once_with(model="gemini-2.5-flash")
    cloud_factory.assert_not_called()


def test_cloud_provider_still_available_without_gemini(corpus, transcriber, monkeypatch):
    gemini_factory = Mock()
    cloud_factory = Mock(return_value=transcriber)
    monkeypatch.setattr(cli, "GeminiSpeechTranscriber", gemini_factory)
    monkeypatch.setattr(cli, "GoogleSpeechTranscriber", cloud_factory)
    feed_input(monkeypatch, "/voice recording.wav", "")
    cli.run_cli(corpus, voice_provider="cloud-speech")
    cloud_factory.assert_called_once_with()
    gemini_factory.assert_not_called()
    transcriber.transcribe.assert_called_once_with("recording.wav", "en-US")
