"""BAT wiring for the implementation-independent bounded system tests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from core.indexer import DataManager
from core.models import AutoCompleteData
from tests.system.adapter import configure_adapter
from tests.system.oracle import CorpusLine, OracleResult, read_bounded_corpus


DATA_DIR = Path(__file__).resolve().parent / "data"
CORPUS_DIR = DATA_DIR / "corpus"
MANIFEST_PATH = DATA_DIR / "sample_manifest.json"
METADATA_PATH = DATA_DIR / "sample_cache_metadata.json"


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register the source-line convention not fixed by the specification."""
    parser.addoption(
        "--offset-base",
        action="store",
        choices=("0", "1"),
        default="1",
        help="Expected source-line offset base: 0 or 1 (BAT default: 1).",
    )


def _sha256(path: Path) -> str:
    """Return the SHA-256 digest for one committed source fixture."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@pytest.fixture(scope="session")
def sample_manifest() -> dict[str, object]:
    """Load the bounded source selection."""
    with MANIFEST_PATH.open(encoding="utf-8") as stream:
        return json.load(stream)


@pytest.fixture(scope="session")
def offset_base(pytestconfig: pytest.Config) -> int:
    """Return the configured physical source-line numbering convention."""
    return int(pytestconfig.getoption("offset_base"))


@pytest.fixture(scope="session")
def bounded_corpus(
    sample_manifest: dict[str, object],
    offset_base: int,
) -> list[CorpusLine]:
    """Load the exact committed corpus records used by the oracle."""
    return read_bounded_corpus(
        CORPUS_DIR,
        list(sample_manifest["files"]),
        int(sample_manifest["max_non_empty_lines_per_file"]),
        offset_base=offset_base,
    )


@pytest.fixture(scope="session")
def prepared_corpus(
    sample_manifest: dict[str, object],
    tmp_path_factory: pytest.TempPathFactory,
) -> Path:
    """Prepare BAT's bounded offline input without mutating committed fixtures."""
    with METADATA_PATH.open(encoding="utf-8") as stream:
        metadata = json.load(stream)
    for relative_file, expected_hash in metadata["source_sha256"].items():
        assert _sha256(CORPUS_DIR / relative_file) == expected_hash, (
            f"copied sample source changed: {relative_file}"
        )

    destination_root = tmp_path_factory.mktemp("bat-bounded-corpus")
    maximum = int(sample_manifest["max_non_empty_lines_per_file"])
    for relative_file in sample_manifest["files"]:
        source = CORPUS_DIR / str(relative_file)
        destination = destination_root / str(relative_file)
        destination.parent.mkdir(parents=True, exist_ok=True)
        selected = 0
        with source.open(encoding="utf-8", errors="replace") as input_stream:
            with destination.open("w", encoding="utf-8") as output_stream:
                for raw_line in input_stream:
                    output_stream.write(raw_line)
                    if raw_line.strip():
                        selected += 1
                        if selected == maximum:
                            break
    return destination_root


@pytest.fixture(scope="session")
def bat_bounded_system(
    prepared_corpus: Path,
    tmp_path_factory: pytest.TempPathFactory,
) -> DataManager:
    """Build an isolated BAT index for only the bounded corpus."""
    cache_dir = tmp_path_factory.mktemp("bat-bounded-cache")
    manager = DataManager(cache_file=str(cache_dir / "lexical_index.pkl"))
    manager.load_data(str(prepared_corpus))
    return manager


@pytest.fixture()
def configured_sample_system(bat_bounded_system: DataManager) -> DataManager:
    """Configure the test-only completion adapter for one test."""
    configure_adapter(bat_bounded_system)
    return bat_bounded_system


def canonicalize_sample_results(
    results: list[AutoCompleteData],
) -> list[OracleResult]:
    """Map BAT's temporary source paths to stable Archive-relative paths."""
    canonical = []
    for result in results:
        source = Path(result.source_text).resolve()
        corpus_marker = "bat-bounded-corpus"
        root = next(
            parent for parent in source.parents if parent.name.startswith(corpus_marker)
        )
        relative_path = source.relative_to(root)
        canonical.append(
            OracleResult(
                completed_sentence=result.completed_sentence,
                source_text=f"Archive/{relative_path.as_posix()}",
                offset=result.offset,
                score=result.score,
            )
        )
    return canonical
