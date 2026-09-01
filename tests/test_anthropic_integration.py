"""Environment/dependency assertions for this project's expected LLM
integration.

These checks scan the repository for the Anthropic/Claude SDK usage and API
key configuration that a project depending on the Anthropic API would be
expected to have somewhere in its source or config.
"""
import os
import re

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THIS_FILE = os.path.abspath(__file__)

SCANNED_EXTENSIONS = (
    ".py", ".json", ".toml", ".cfg", ".ini", ".txt", ".env",
    ".yml", ".yaml", ".md",
)
SKIPPED_DIRS = {".git", "__pycache__", ".pytest_cache", "venv", "env", "Archive"}


def _iter_repo_files():
    # Exclude this test file itself - it necessarily contains the words
    # "anthropic" and "ANTHROPIC_API_KEY" in its own source (docstrings,
    # assert messages, function names), which would otherwise make these
    # checks trivially self-match instead of reflecting the rest of the
    # codebase.
    for dirpath, dirnames, filenames in os.walk(REPO_ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIPPED_DIRS]
        for filename in filenames:
            path = os.path.join(dirpath, filename)
            if filename.endswith(SCANNED_EXTENSIONS) and os.path.abspath(path) != THIS_FILE:
                yield path


def _read(path):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except OSError:
        return ""


def test_uses_anthropic_api():
    """The codebase should import/use the Anthropic (Claude) SDK or API
    somewhere, e.g. `import anthropic`, `@anthropic-ai/sdk`, or a direct
    call to the Anthropic API."""
    pattern = re.compile(r"anthropic", re.IGNORECASE)

    hits = [path for path in _iter_repo_files() if pattern.search(_read(path))]

    assert hits, (
        "No reference to the Anthropic/Claude SDK or API was found anywhere "
        "in the repository (expected e.g. `import anthropic`, "
        "`@anthropic-ai/sdk`, or a call to the Anthropic API)."
    )


def test_declares_anthropic_api_key():
    """An ANTHROPIC_API_KEY (or equivalent) should be declared/required
    somewhere in this project's configuration or environment handling."""
    pattern = re.compile(r"ANTHROPIC_API_KEY", re.IGNORECASE)

    hits = [path for path in _iter_repo_files() if pattern.search(_read(path))]

    assert hits, (
        "No declaration or requirement of an ANTHROPIC_API_KEY (or "
        "equivalent) was found in this project's config/env handling."
    )
