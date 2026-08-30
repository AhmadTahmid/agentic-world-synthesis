from pathlib import Path

import pytest

from worldsynth.schemas.loader import ContentBundle, load_bundle


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def bundle(repo_root: Path) -> ContentBundle:
    return load_bundle(repo_root)
