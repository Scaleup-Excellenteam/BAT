"""Edge-case coverage for core.normalizer, beyond tests/test_normalizer.py."""
from core.normalizer import normalize_text


def test_normalize_text_none_input_returns_empty_string():
    assert normalize_text(None) == ""


def test_normalize_text_preserves_digits():
    assert normalize_text("Room 237, second floor!") == "room 237 second floor"


def test_normalize_text_is_idempotent():
    text = "  Hello,   WORLD!!  "

    once = normalize_text(text)
    twice = normalize_text(once)

    assert once == twice
