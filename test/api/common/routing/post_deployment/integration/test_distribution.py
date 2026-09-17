import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

API_NAME = "api.10ulabs.com"
ZONE_ID = "Z07722121TJUMGGCZYKBV"
BUCKET_HOST = f"{API_NAME.replace('.', '-')}.s3.us-east-2.amazonaws.com"
UNSERVED = f"https://{API_NAME}/nothing-serves-this"
BROWSING = {"Accept": "text/html,application/xhtml+xml"}
A_MONTH = 30 * 24 * 60 * 60
A_YEAR = 365 * 24 * 60 * 60


@pytest.fixture(scope="module", name="distribution")
def distribution_fixture(cloudfront_client: Any) -> Dict[str, Any]:
    for item in cloudfront_client.list_distributions()["DistributionList"]["Items"]:
        if item["Comment"] == API_NAME:
            return dict(item)
    raise LookupError(f"no distribution is commented {API_NAME}")


@pytest.fixture(scope="module", name="cache_policy")
def cache_policy_fixture(cloudfront_client: Any, distribution: Dict[str, Any]) -> Dict[str, Any]:
    behaviors = distribution["CacheBehaviors"]["Items"]
    root = next(behavior for behavior in behaviors if behavior["PathPattern"] == "/")
    policy = cloudfront_client.get_cache_policy(Id=root["CachePolicyId"])
    return dict(policy["CachePolicy"]["CachePolicyConfig"])


def _answer(url: str, headers: Optional[Dict[str, str]] = None) -> Tuple[int, str, str]:
    try:
        with urlopen(Request(url, headers=headers or {}), timeout=10) as response:
            content_type = str(response.headers.get("Content-Type"))
            return int(response.status), content_type, response.read().decode("utf-8")
    except HTTPError as error:
        return error.code, str(error.headers.get("Content-Type")), error.read().decode("utf-8")


@pytest.fixture(scope="module", name="root_page")
def root_page_fixture(distribution: Dict[str, Any]) -> Tuple[int, str, str]:
    return _answer(f"https://{distribution['DomainName']}/")


@pytest.fixture(scope="module", name="record")
def record_fixture(route53_client: Any) -> Dict[str, Any]:
    listing = route53_client.list_resource_record_sets(
        HostedZoneId=ZONE_ID, StartRecordName=API_NAME, StartRecordType="A", MaxItems="1"
    )
    return dict(listing["ResourceRecordSets"][0])


@pytest.fixture(scope="module", name="named_status")
def named_status_fixture() -> int:
    return _answer(f"https://{API_NAME}/")[0]


@pytest.fixture(scope="module", name="served_spec")
def served_spec_fixture() -> Tuple[int, str, str]:
    return _answer(f"https://{API_NAME}/openapi.json")


@pytest.fixture(scope="module", name="not_found_page")
def not_found_page_fixture() -> Tuple[int, str, str]:
    return _answer(f"https://{API_NAME}/404.html")


@pytest.fixture(scope="module", name="browsed_answer")
def browsed_answer_fixture() -> Tuple[int, str, str]:
    return _answer(UNSERVED, BROWSING)


@pytest.fixture(scope="module", name="unserved_answer")
def unserved_answer_fixture() -> Tuple[int, str, str]:
    return _answer(UNSERVED)


@pytest.fixture(scope="module", name="missing_carrier")
def missing_carrier_fixture(bearer: Dict[str, str]) -> Tuple[int, str, str]:
    return _answer(f"https://{API_NAME}/carriers/999999999", bearer)


def test_the_distribution_fronts_the_gateway(distribution: Dict[str, Any], api_id: str) -> None:
    origins = [origin["DomainName"] for origin in distribution["Origins"]["Items"]]
    assert f"{api_id}.execute-api.us-east-2.amazonaws.com" in origins


def test_the_distribution_fronts_the_bucket_named_for_the_host(
    distribution: Dict[str, Any],
) -> None:
    origins = [origin["DomainName"] for origin in distribution["Origins"]["Items"]]
    assert BUCKET_HOST in origins


def test_the_pages_are_held_for_as_little_as_they_ask(cache_policy: Dict[str, Any]) -> None:
    assert cache_policy["MinTTL"] == 0


def test_the_pages_are_held_a_month_when_they_do_not_say(cache_policy: Dict[str, Any]) -> None:
    assert cache_policy["DefaultTTL"] == A_MONTH


def test_the_pages_are_held_a_year_at_most(cache_policy: Dict[str, Any]) -> None:
    assert cache_policy["MaxTTL"] == A_YEAR


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


def test_the_served_spec_is_json(served_spec: Tuple[int, str, str]) -> None:
    assert served_spec[1].startswith("application/json")


def test_the_served_spec_is_the_one_the_gateway_is_built_from(
    served_spec: Tuple[int, str, str], repo_root: Path
) -> None:
    spec = repo_root / "src" / "www" / "openapi.json"
    assert served_spec[2] == spec.read_text(encoding="utf-8")


def test_the_not_found_page_answers_200(not_found_page: Tuple[int, str, str]) -> None:
    assert not_found_page[0] == 200


def test_the_not_found_page_is_html(not_found_page: Tuple[int, str, str]) -> None:
    assert not_found_page[1].startswith("text/html")


def test_a_path_nothing_serves_answers_404(unserved_answer: Tuple[int, str, str]) -> None:
    assert unserved_answer[0] == 404


def test_a_path_nothing_serves_answers_json(unserved_answer: Tuple[int, str, str]) -> None:
    assert unserved_answer[1].startswith("application/json")


def test_a_path_nothing_serves_names_the_error(unserved_answer: Tuple[int, str, str]) -> None:
    assert json.loads(unserved_answer[2])["error"] == "Not Found"


def test_a_browser_is_answered_404(browsed_answer: Tuple[int, str, str]) -> None:
    assert browsed_answer[0] == 404


def test_a_browser_is_answered_html(browsed_answer: Tuple[int, str, str]) -> None:
    assert browsed_answer[1].startswith("text/html")


def test_a_browser_is_answered_with_the_not_found_page(
    browsed_answer: Tuple[int, str, str], not_found_page: Tuple[int, str, str]
) -> None:
    assert browsed_answer[2] == not_found_page[2]


def test_a_missing_carrier_answers_404(missing_carrier: Tuple[int, str, str]) -> None:
    assert missing_carrier[0] == 404


def test_a_missing_carrier_keeps_its_own_json(missing_carrier: Tuple[int, str, str]) -> None:
    assert json.loads(missing_carrier[2])["error"] == "No such carrier"
