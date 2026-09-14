from types import ModuleType
from typing import Any, Callable, Dict, List

import pytest


@pytest.fixture(name="handler")
def handler_fixture(endpoint: Callable[[str], ModuleType]) -> ModuleType:
    return endpoint("carriers")


@pytest.fixture(name="carriers")
def carriers_fixture() -> List[Dict[str, Any]]:
    return [
        {"PK": {"S": "carriers"}, "SK": {"S": "#"}, "next": {"N": "3"}},
        {"PK": {"S": "carriers"}, "SK": {"S": "2"}, "name": {"S": "zayo"},
         "next_pop": {"N": "1"}, "next_fiber_segment": {"N": "1"}},
        {"PK": {"S": "carriers"}, "SK": {"S": "1"}, "name": {"S": "lumen"},
         "next_pop": {"N": "4"}, "next_fiber_segment": {"N": "4"}},
        {"PK": {"S": "carriers/1"}, "SK": {"S": "pops/3"}, "municipality": {"S": "Chicago"},
         "state": {"S": "IL"}, "country": {"S": "US"},
         "latitude": {"N": "41.8781"}, "longitude": {"N": "-87.6298"}},
        {"PK": {"S": "carriers/1"}, "SK": {"S": "pops/1"}, "municipality": {"S": "Denver"},
         "state": {"S": "CO"}, "country": {"S": "US"},
         "latitude": {"N": "39.7392"}, "longitude": {"N": "-104.9903"}},
        {"PK": {"S": "carriers/1"}, "SK": {"S": "fiber-segments/3"},
         "a_municipality": {"S": "New York"}, "a_state": {"S": "NY"},
         "z_municipality": {"S": "Amsterdam"}, "z_state": {"S": ""}, "submarine": {"BOOL": True}},
        {"PK": {"S": "carriers/1"}, "SK": {"S": "fiber-segments/1"},
         "a_municipality": {"S": "Denver"}, "a_state": {"S": "CO"},
         "z_municipality": {"S": "Chicago"}, "z_state": {"S": "IL"}, "submarine": {"BOOL": False}},
    ]


@pytest.fixture
def lumen(carriers: List[Dict[str, Any]]) -> Dict[str, Any]:
    return carriers[2]


@pytest.fixture
def zayo(carriers: List[Dict[str, Any]]) -> Dict[str, Any]:
    return carriers[1]
