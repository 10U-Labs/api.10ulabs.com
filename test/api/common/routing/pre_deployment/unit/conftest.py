import json
from pathlib import Path
from types import ModuleType
from typing import Any, Callable, Dict

import pytest


@pytest.fixture(scope="module")
def routing_dir(repo_root: Path) -> Path:
    return repo_root / "src" / "api" / "common" / "routing"


@pytest.fixture(scope="module")
def openapi(repo_root: Path) -> Dict[str, Any]:
    path = repo_root / "src" / "www" / "api" / "openapi.json"
    return dict(json.loads(path.read_text(encoding="utf-8")))


@pytest.fixture(scope="module")
def catchall_handler(load_handler: Callable[[str], ModuleType]) -> ModuleType:
    return load_handler("api/common/routing")
