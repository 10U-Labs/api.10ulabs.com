from typing import Any, Dict, Tuple
from urllib.request import Request, urlopen

import pytest

API_NAME = "api.10ulabs.com"


@pytest.fixture(scope="module", name="distribution")
def distribution_fixture(cloudfront_client: Any) -> Dict[str, Any]:
    for item in cloudfront_client.list_distributions()["DistributionList"]["Items"]:
        if item["Comment"] == API_NAME:
            return dict(item)
    raise LookupError(f"no distribution is commented {API_NAME}")


@pytest.fixture(scope="module", name="root_page")
def root_page_fixture(distribution: Dict[str, Any]) -> Tuple[int, str, str]:
    with urlopen(Request(f"https://{distribution['DomainName']}/"), timeout=10) as response:
        content_type = str(response.headers.get("Content-Type"))
        return int(response.status), content_type, response.read().decode("utf-8")


def test_the_distribution_fronts_the_gateway(distribution: Dict[str, Any], api_id: str) -> None:
    origins = [origin["DomainName"] for origin in distribution["Origins"]["Items"]]
    assert f"{api_id}.execute-api.us-east-2.amazonaws.com" in origins


def test_the_root_of_the_distribution_answers_200(root_page: Tuple[int, str, str]) -> None:
    assert root_page[0] == 200


def test_the_root_of_the_distribution_is_html(root_page: Tuple[int, str, str]) -> None:
    assert root_page[1].startswith("text/html")


def test_the_root_of_the_distribution_renders_the_spec_beside_it(
    root_page: Tuple[int, str, str]
) -> None:
    assert "Redoc.init('openapi.json'" in root_page[2]
