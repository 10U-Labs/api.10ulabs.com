from pathlib import Path

import pytest


@pytest.fixture(scope="module", name="identity_dir")
def identity_dir_fixture(repo_root: Path) -> Path:
    return repo_root / "src" / "api" / "common" / "identity"


@pytest.fixture(scope="module")
def main_tf(identity_dir: Path) -> str:
    return (identity_dir / "main.tf").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def iam_tf(identity_dir: Path) -> str:
    return (identity_dir / "iam.tf").read_text(encoding="utf-8")
