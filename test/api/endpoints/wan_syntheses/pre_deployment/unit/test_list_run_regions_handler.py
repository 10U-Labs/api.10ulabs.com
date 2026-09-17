from types import SimpleNamespace
from typing import Any, Dict, List

import pytest

from lambda_http import Handler
from synthesis_events import Served, MISSING, PROVIDER_A, PROVIDER_B, under

HANDLER = "lambda/list_run_regions"
RUN_REGIONS = "/wan-syntheses/{id}/hyperscale-cloud-service-provider-regions"


def _get_run_regions(synthesis: str = "1") -> Dict[str, Any]:
    return under(RUN_REGIONS, synthesis)


def test_the_regions_of_a_synthesis_answer_200(
    answer: Handler, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert answer(_get_run_regions())["statusCode"] == 200


def test_the_regions_of_a_synthesis_answer_as_the_catalog_serves_them_in_id_order(
    served: Served, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert served(_get_run_regions()) == [PROVIDER_A, PROVIDER_B]


def test_a_synthesis_without_a_wan_still_answers_the_regions_it_was_given(
    served: Served, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert [region["name"] for region in served(_get_run_regions("2"))] == ["Provider D"]


def test_the_regions_of_a_synthesis_are_read_from_under_it_after_its_record(
    answer: Handler, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    answer(_get_run_regions())
    assert (len(store.gets), store.queries[-1]["ExpressionAttributeValues"]) == (1, {
        ":pk": {"S": "wan-syntheses/1"},
        ":prefix": {"S": "hyperscale-cloud-service-provider-regions/"},
    })


def test_the_regions_of_an_unknown_synthesis_name_the_synthesis(served: Served) -> None:
    assert served(_get_run_regions("3"))["error"] == MISSING


@pytest.mark.parametrize("synthesis", ["#", "", "minuteman", "-1"])
def test_the_regions_of_an_id_that_is_not_a_number_answer_404(
    answer: Handler, synthesis: str
) -> None:
    assert answer(_get_run_regions(synthesis))["statusCode"] == 404


def test_a_store_that_refuses_a_synthesis_s_regions_names_the_error(
    served: Served, store: SimpleNamespace
) -> None:
    store.failing = True
    error = served(_get_run_regions())["error"]
    assert error == "Failed to read the hyperscale cloud service provider regions"
