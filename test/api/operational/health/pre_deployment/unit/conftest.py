from types import ModuleType
from typing import Callable

import pytest


@pytest.fixture(scope="module")
def health_handler(load_handler: Callable[[str], ModuleType]) -> ModuleType:
    return load_handler("api/operational/health")
