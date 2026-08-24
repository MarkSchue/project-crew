from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]  # .../project_crew
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
SCHEMA_DIR = REPO_ROOT / "project-template-repository" / "schemas"


@pytest.fixture(scope="session")
def schema_dir() -> Path:
    return SCHEMA_DIR


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    return FIXTURES_DIR
