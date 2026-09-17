from types import SimpleNamespace
from typing import Any, Dict, List

import pytest

from lambda_http import Handler
from synthesis_events import Served, MISSING, under

HANDLER = "lambda/list_forced_homes"
FORCED_HOMES = "/wan-syntheses/{id}/forced-homes"


def _get_forced_homes(synthesis: str = "1") -> Dict[str, Any]:
    return under(FORCED_HOMES, synthesis)


def test_the_forced_homes_of_a_synthesis_answer_200(
    answer: Handler, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert answer(_get_forced_homes())["statusCode"] == 200


def test_the_forced_homes_answer_from_a_named_site_to_a_named_pop_in_id_order(
    served: Served, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert served(_get_forced_homes()) == [
        {"id": 1, "source": "F.E. Warren AFB", "target": "Cheyenne, WY"},
        {"id": 2, "source": "Hill AFB", "target": "Salt Lake City, UT"},
    ]


def test_a_synthesis_without_a_wan_still_answers_the_forced_homes_it_was_given(
    served: Served, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert [one["source"] for one in served(_get_forced_homes("2"))] == ["Wright-Patterson AFB"]


def test_the_forced_homes_are_read_from_under_the_synthesis_after_its_record(
    answer: Handler, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    answer(_get_forced_homes())
    assert (len(store.gets), store.queries[-1]["ExpressionAttributeValues"]) == (1, {
        ":pk": {"S": "wan-syntheses/1"}, ":prefix": {"S": "forced-homes/"},
    })


def test_the_forced_homes_of_an_unknown_synthesis_name_the_synthesis(served: Served) -> None:
    assert served(_get_forced_homes("3"))["error"] == MISSING


@pytest.mark.parametrize("synthesis", ["#", "", "homes", "-1"])
def test_the_forced_homes_of_an_id_that_is_not_a_number_answer_404(
    answer: Handler, synthesis: str
) -> None:
    assert answer(_get_forced_homes(synthesis))["statusCode"] == 404


def test_a_store_that_refuses_the_forced_homes_names_the_error(
    served: Served, store: SimpleNamespace
) -> None:
    store.failing = True
    assert served(_get_forced_homes())["error"] == "Failed to read the forced homes"
