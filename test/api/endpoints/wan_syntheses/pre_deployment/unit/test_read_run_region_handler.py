from types import SimpleNamespace
from typing import Any, Dict, List

import pytest

from lambda_http import Handler
from synthesis_events import Served, MISSING, PROVIDER_B, under

HANDLER = "lambda/read_run_region"
RUN_REGION = "/wan-syntheses/{id}/hyperscale-cloud-service-provider-regions/{region_id}"
MISSING_REGION = "No such hyperscale cloud service provider region"


def _get_run_region(synthesis: str = "1", region: str = "2") -> Dict[str, Any]:
    return under(RUN_REGION, synthesis, region_id=region)


def test_a_stored_region_of_a_synthesis_answers_200(
    answer: Handler, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert answer(_get_run_region())["statusCode"] == 200


def test_a_region_of_a_synthesis_answers_as_the_catalog_serves_it_with_its_id(
    served: Served, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert served(_get_run_region()) == PROVIDER_B


def test_a_region_of_a_synthesis_is_read_by_its_key_after_the_synthesis_s_record(
    answer: Handler, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    answer(_get_run_region())
    assert [one["Key"]["SK"]["S"] for one in store.gets] == [
        "1", "hyperscale-cloud-service-provider-regions/2"
    ]


def test_a_synthesis_without_a_wan_still_serves_a_region_it_was_given(
    served: Served, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert served(_get_run_region("2", "1"))["name"] == "Provider D"


def test_a_region_of_an_unknown_synthesis_names_the_synthesis(served: Served) -> None:
    assert served(_get_run_region("3"))["error"] == MISSING


def test_an_unknown_region_of_a_synthesis_answers_404(
    answer: Handler, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert answer(_get_run_region("1", "3"))["statusCode"] == 404


def test_an_unknown_region_of_a_synthesis_names_the_region(
    served: Served, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert served(_get_run_region("1", "3"))["error"] == MISSING_REGION


@pytest.mark.parametrize("region", ["#", "", "2/", "Provider A"])
def test_a_region_id_that_is_not_a_number_asks_the_store_nothing(
    answer: Handler, store: SimpleNamespace, region: str
) -> None:
    assert (answer(_get_run_region("1", region))["statusCode"], store.gets) == (404, [])


def test_a_store_that_refuses_a_synthesis_s_region_names_the_error(
    served: Served, store: SimpleNamespace
) -> None:
    store.failing = True
    error = served(_get_run_region())["error"]
    assert error == "Failed to read the hyperscale cloud service provider region"
