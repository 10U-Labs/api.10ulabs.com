from types import SimpleNamespace
from typing import Any, Dict, List

import pytest

from lambda_http import Handler
from synthesis_events import Served, MISSING, NO_WAN, ASHBURN, CHEYENNE, get

HANDLER = "lambda/list_wan_pops"
WAN_POPS = "/wan-syntheses/{id}/wan-pops"


def _get_wan_pops(synthesis: str = "1") -> Dict[str, Any]:
    return {**get(WAN_POPS), "pathParameters": {"id": synthesis}}


def test_the_wan_pops_of_a_synthesis_answer_200(
    answer: Handler, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert answer(_get_wan_pops())["statusCode"] == 200


def test_the_wan_pops_answer_as_placed_carrier_pops_in_id_order(
    served: Served, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert served(_get_wan_pops()) == [ASHBURN, CHEYENNE]


@pytest.fixture(name="wan_pops_read")
def wan_pops_read_fixture(
    answer: Handler, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> SimpleNamespace:
    store.items.extend(syntheses)
    answer(_get_wan_pops())
    return store


def test_the_wan_pops_are_read_after_the_synthesis_s_record(wan_pops_read: SimpleNamespace) -> None:
    assert [one["Key"] for one in wan_pops_read.gets] == [
        {"PK": {"S": "wan-syntheses"}, "SK": {"S": "1"}},
    ]


def test_the_wan_pops_are_read_from_under_the_synthesis(wan_pops_read: SimpleNamespace) -> None:
    assert wan_pops_read.queries[-1]["ExpressionAttributeValues"] == {
        ":pk": {"S": "wan-syntheses/1"}, ":prefix": {"S": "wan-pops/"},
    }


def test_the_wan_pops_are_read_from_the_table_the_environment_names(
    wan_pops_read: SimpleNamespace
) -> None:
    assert wan_pops_read.queries[-1]["TableName"] == "store"


def test_a_synthesis_without_a_wan_has_no_wan_pops(
    answer: Handler, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert answer(_get_wan_pops("2"))["statusCode"] == 404


def test_a_synthesis_without_a_wan_names_the_error(
    served: Served, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert served(_get_wan_pops("2"))["error"] == NO_WAN


def test_a_synthesis_without_a_wan_is_not_queried(
    answer: Handler, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    answer(_get_wan_pops("2"))
    assert store.queries == []


def test_the_wan_pops_of_an_unknown_synthesis_answer_404(answer: Handler) -> None:
    assert answer(_get_wan_pops("3"))["statusCode"] == 404


def test_the_wan_pops_of_an_unknown_synthesis_name_the_synthesis(served: Served) -> None:
    assert served(_get_wan_pops("3"))["error"] == MISSING


@pytest.mark.parametrize("synthesis", ["#", "", "minuteman", "-1"])
def test_the_wan_pops_of_an_id_that_is_not_a_number_answer_404(
    answer: Handler, synthesis: str
) -> None:
    assert answer(_get_wan_pops(synthesis))["statusCode"] == 404


def test_a_store_that_refuses_the_wan_pops_answers_500(
    answer: Handler, store: SimpleNamespace
) -> None:
    store.failing = True
    assert answer(_get_wan_pops())["statusCode"] == 500


def test_a_store_that_refuses_the_wan_pops_names_the_error(
    served: Served, store: SimpleNamespace
) -> None:
    store.failing = True
    assert served(_get_wan_pops())["error"] == "Failed to read the wan pops"
