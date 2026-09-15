from typing import Any, Dict, Tuple
from urllib.request import Request, urlopen

import pytest

API_NAME = "api.10ulabs.com"
ZONE_ID = "Z07722121TJUMGGCZYKBV"


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


@pytest.fixture(scope="module", name="record")
def record_fixture(route53_client: Any) -> Dict[str, Any]:
    listing = route53_client.list_resource_record_sets(
        HostedZoneId=ZONE_ID, StartRecordName=API_NAME, StartRecordType="A", MaxItems="1"
    )
    return dict(listing["ResourceRecordSets"][0])


@pytest.fixture(scope="module", name="named_status")
def named_status_fixture() -> int:
    with urlopen(Request(f"https://{API_NAME}/"), timeout=10) as response:
        return int(response.status)


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


def test_the_distribution_carries_the_name(distribution: Dict[str, Any]) -> None:
    assert distribution["Aliases"]["Items"] == [API_NAME]


def test_the_name_aliases_the_distribution(
    record: Dict[str, Any], distribution: Dict[str, Any]
) -> None:
    assert record["AliasTarget"]["DNSName"] == f"{distribution['DomainName']}."


def test_the_name_answers_200(named_status: int) -> None:
    assert named_status == 200
