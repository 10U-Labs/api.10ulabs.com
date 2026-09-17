from types import SimpleNamespace
from typing import Any, Dict, List

import pytest

from lambda_http import Handler
from synthesis_events import Served, MISSING, NO_WAN, CHEYENNE, get

HANDLER = "lambda/read_wan_pop"
WAN_POP = "/wan-syntheses/{id}/wan-pops/{wan_pop_id}"
MISSING_WAN_POP = "No such wan pop"


def _get_wan_pop(synthesis: str = "1", wan_pop: str = "2") -> Dict[str, Any]:
    return {**get(WAN_POP), "pathParameters": {"id": synthesis, "wan_pop_id": wan_pop}}


def test_a_stored_wan_pop_answers_200(
    answer: Handler, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert answer(_get_wan_pop())["statusCode"] == 200


def test_a_stored_wan_pop_answers_as_a_placed_carrier_pop_with_its_id(
    served: Served, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert served(_get_wan_pop()) == CHEYENNE


@pytest.fixture(name="wan_pop_gets")
def wan_pop_gets_fixture(
    answer: Handler, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    store.items.extend(syntheses)
    answer(_get_wan_pop())
    return [dict(one) for one in store.gets]


def test_a_wan_pop_is_read_after_the_synthesis_s_record(wan_pop_gets: List[Dict[str, Any]]) -> None:
    assert [one["Key"] for one in wan_pop_gets] == [
        {"PK": {"S": "wan-syntheses"}, "SK": {"S": "1"}},
        {"PK": {"S": "wan-syntheses/1"}, "SK": {"S": "wan-pops/2"}},
    ]


def test_a_wan_pop_is_read_from_the_table_the_environment_names(
    wan_pop_gets: List[Dict[str, Any]]
) -> None:
    assert [one["TableName"] for one in wan_pop_gets] == ["store", "store"]


def test_a_wan_pop_of_a_synthesis_without_a_wan_answers_404(
    answer: Handler, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert answer(_get_wan_pop("2", "1"))["statusCode"] == 404


def test_a_wan_pop_of_a_synthesis_without_a_wan_names_the_wan(
    served: Served, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert served(_get_wan_pop("2", "1"))["error"] == NO_WAN


def test_a_wan_pop_of_a_synthesis_without_a_wan_is_not_looked_for(
    answer: Handler, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    answer(_get_wan_pop("2", "1"))
    assert len(store.gets) == 1


def test_a_wan_pop_of_an_unknown_synthesis_answers_404(answer: Handler) -> None:
    assert answer(_get_wan_pop("3"))["statusCode"] == 404


def test_a_wan_pop_of_an_unknown_synthesis_names_the_synthesis(served: Served) -> None:
    assert served(_get_wan_pop("3"))["error"] == MISSING


def test_an_unknown_wan_pop_answers_404(
    answer: Handler, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert answer(_get_wan_pop("1", "3"))["statusCode"] == 404


def test_an_unknown_wan_pop_names_the_wan_pop(
    served: Served, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert served(_get_wan_pop("1", "3"))["error"] == MISSING_WAN_POP


@pytest.mark.parametrize("wan_pop", ["#", "", "2/", "-1"])
def test_a_wan_pop_id_that_is_not_a_number_answers_404(
    answer: Handler, store: SimpleNamespace, syntheses: List[Dict[str, Any]], wan_pop: str
) -> None:
    store.items.extend(syntheses)
    assert answer(_get_wan_pop("1", wan_pop))["statusCode"] == 404


@pytest.mark.parametrize("wan_pop", ["#", "", "2/", "-1"])
def test_a_wan_pop_id_that_is_not_a_number_asks_the_store_nothing(
    answer: Handler, store: SimpleNamespace, wan_pop: str
) -> None:
    answer(_get_wan_pop("1", wan_pop))
    assert store.gets == []


def test_a_store_that_refuses_the_wan_pop_answers_500(
    answer: Handler, store: SimpleNamespace
) -> None:
    store.failing = True
    assert answer(_get_wan_pop())["statusCode"] == 500


def test_a_store_that_refuses_the_wan_pop_names_the_error(
    served: Served, store: SimpleNamespace
) -> None:
    store.failing = True
    assert served(_get_wan_pop())["error"] == "Failed to read the wan pop"
