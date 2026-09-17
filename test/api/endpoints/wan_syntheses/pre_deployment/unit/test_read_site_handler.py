from types import SimpleNamespace
from typing import Any, Dict, List

import pytest

from lambda_http import Handler
from synthesis_events import Served, MISSING, HILL, under

HANDLER = "lambda/read_site"
SITE = "/wan-syntheses/{id}/sites/{site_id}"
MISSING_SITE = "No such site"


def _get_site(synthesis: str = "1", site: str = "2") -> Dict[str, Any]:
    return under(SITE, synthesis, site_id=site)


def test_a_stored_site_answers_200(
    answer: Handler, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert answer(_get_site())["statusCode"] == 200


def test_a_stored_site_answers_as_named_and_placed_with_its_id(
    served: Served, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert served(_get_site()) == HILL


def test_a_site_is_read_by_its_key_after_the_synthesis_s_record(
    answer: Handler, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    answer(_get_site())
    assert [one["Key"] for one in store.gets] == [
        {"PK": {"S": "wan-syntheses"}, "SK": {"S": "1"}},
        {"PK": {"S": "wan-syntheses/1"}, "SK": {"S": "sites/2"}},
    ]


def test_a_synthesis_without_a_wan_still_serves_a_site_it_was_given(
    served: Served, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert served(_get_site("2", "1"))["name"] == "Wright-Patterson AFB"


def test_a_site_of_an_unknown_synthesis_names_the_synthesis(served: Served) -> None:
    assert served(_get_site("3"))["error"] == MISSING


def test_an_unknown_site_answers_404(
    answer: Handler, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert answer(_get_site("1", "3"))["statusCode"] == 404


def test_an_unknown_site_names_the_site(
    served: Served, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert served(_get_site("1", "3"))["error"] == MISSING_SITE


@pytest.mark.parametrize("site", ["#", "", "2/", "-1"])
def test_a_site_id_that_is_not_a_number_asks_the_store_nothing(
    answer: Handler, store: SimpleNamespace, site: str
) -> None:
    assert (answer(_get_site("1", site))["statusCode"], store.gets) == (404, [])


def test_a_store_that_refuses_the_site_names_the_error(
    served: Served, store: SimpleNamespace
) -> None:
    store.failing = True
    assert served(_get_site())["error"] == "Failed to read the site"
