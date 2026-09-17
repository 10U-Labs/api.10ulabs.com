from types import SimpleNamespace
from typing import Any, Dict, List

import pytest

from lambda_http import Handler
from synthesis_events import Served, MISSING, WARREN, HILL, under

HANDLER = "lambda/list_sites"
SITES = "/wan-syntheses/{id}/sites"


def _get_sites(synthesis: str = "1") -> Dict[str, Any]:
    return under(SITES, synthesis)


def test_the_sites_of_a_synthesis_answer_200(
    answer: Handler, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert answer(_get_sites())["statusCode"] == 200


def test_the_sites_answer_as_named_and_placed_in_id_order(
    served: Served, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert served(_get_sites()) == [WARREN, HILL]


def test_a_synthesis_without_a_wan_still_answers_the_sites_it_was_given(
    served: Served, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert [site["name"] for site in served(_get_sites("2"))] == ["Wright-Patterson AFB"]


def test_the_sites_are_read_from_under_the_synthesis_after_its_record(
    answer: Handler, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    answer(_get_sites())
    assert (len(store.gets), store.queries[-1]["ExpressionAttributeValues"]) == (1, {
        ":pk": {"S": "wan-syntheses/1"}, ":prefix": {"S": "sites/"},
    })


def test_the_sites_of_an_unknown_synthesis_name_the_synthesis(served: Served) -> None:
    assert served(_get_sites("3"))["error"] == MISSING


@pytest.mark.parametrize("synthesis", ["#", "", "minuteman", "-1"])
def test_the_sites_of_an_id_that_is_not_a_number_answer_404(
    answer: Handler, synthesis: str
) -> None:
    assert answer(_get_sites(synthesis))["statusCode"] == 404


def test_a_store_that_refuses_the_sites_names_the_error(
    served: Served, store: SimpleNamespace
) -> None:
    store.failing = True
    assert served(_get_sites())["error"] == "Failed to read the sites"
