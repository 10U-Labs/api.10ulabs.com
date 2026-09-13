import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Callable

import pytest


@pytest.fixture(scope="session", name="repo_root")
def repo_root_fixture() -> Path:
    return Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def load_handler(repo_root: Path) -> Callable[..., ModuleType]:
    def load(stack: str, handler: str = "lambda") -> ModuleType:
        path = repo_root / "src" / stack / handler / "handler.py"
        name = f"{stack}/{handler}".replace("/", "_")
        spec = importlib.util.spec_from_file_location(name, path)
        if spec is None or spec.loader is None:
            raise ImportError(f"no handler at {path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    return load
