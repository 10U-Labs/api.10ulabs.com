from types import ModuleType
from typing import Any, Callable, Dict, List

import pytest


@pytest.fixture
def handler(endpoint: Callable[[str], ModuleType]) -> ModuleType:
    return endpoint("wan_syntheses")


@pytest.fixture
def syntheses() -> List[Dict[str, Any]]:
    return [
        {"PK": {"S": "wan-syntheses"}, "SK": {"S": "#"}, "next": {"N": "3"}},
        {"PK": {"S": "wan-syntheses"}, "SK": {"S": "2"}, "label": {"S": "daf"}},
        {"PK": {"S": "wan-syntheses"}, "SK": {"S": "1"}, "label": {"S": "minuteman"}},
    ]
