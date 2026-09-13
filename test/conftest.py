import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any, Callable

import boto3
import pytest

REGION = "us-east-2"


@pytest.fixture(scope="session", name="repo_root")
def repo_root_fixture() -> Path:
    return Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def load_handler(repo_root: Path) -> Callable[[str], ModuleType]:
    def load(stack: str) -> ModuleType:
        path = repo_root / "src" / stack / "lambda" / "handler.py"
        spec = importlib.util.spec_from_file_location(stack.replace("/", "_"), path)
        if spec is None or spec.loader is None:
            raise ImportError(f"no handler at {path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    return load


@pytest.fixture(scope="session")
def iam_client() -> Any:
    return boto3.client("iam", region_name=REGION)


@pytest.fixture(scope="session")
def apigateway_client() -> Any:
    return boto3.client("apigateway", region_name=REGION)


@pytest.fixture(scope="session")
def lambda_client() -> Any:
    return boto3.client("lambda", region_name=REGION)
