import re
from pathlib import Path
from typing import Any, Dict, List

import pytest

MAP = "https://www.10ulabs.com"
SYNTHESIS = "/wan-syntheses/{id}"
MAP_READS = [
    "/wan-syntheses",
    *(f"{SYNTHESIS}/{part}" for part in (
        "wan-pops", "sites", "hyperscale-cloud-service-provider-regions", "fiber-segments",
        "homing-circuits", "backbone-circuits",
    )),
]
ANSWERED = "method.response.header.Access-Control-Allow-"
POLICY = r'resource "aws_cloudfront_response_headers_policy" "map_reads" \{.*?\n\}'
BEHAVIOR = r"ordered_cache_behavior \{.*?\n  \}"
MAP_READS_POLICY = "aws_cloudfront_response_headers_policy.map_reads.id"


def _settings(block: str) -> Dict[str, str]:
    pairs = re.findall(r"^\s*(\w+)\s*=\s*(.+?)\s*$", block, re.MULTILINE)
    return {name: value.strip('"') for name, value in pairs}


def _items(block: str, holder: str) -> List[str]:
    match = re.search(rf"{holder} \{{\s*items\s*=\s*\[(.*?)\]", block, re.DOTALL)
    inside = "" if match is None else match.group(1)
    return [one.strip(' "') for one in inside.split(",") if one.strip()]


@pytest.fixture(name="map_preflight", params=MAP_READS)
def map_preflight_fixture(
    openapi: Dict[str, Any], request: pytest.FixtureRequest
) -> Dict[str, Any]:
    return dict(openapi["paths"][str(request.param)].get("options", {}))


@pytest.fixture(name="allowed")
def allowed_fixture(map_preflight: Dict[str, Any]) -> Dict[str, str]:
    integration = map_preflight.get("x-amazon-apigateway-integration", {})
    answer = integration.get("responses", {}).get("default", {})
    parameters = answer.get("responseParameters", {})
    return {
        name[len(ANSWERED):]: value
        for name, value in parameters.items() if name.startswith(ANSWERED)
    }


@pytest.fixture(scope="module", name="distribution_tf")
def distribution_tf_fixture(routing_dir: Path) -> str:
    return routing_dir.joinpath("cloudfront.tf").read_text(encoding="utf-8")


@pytest.fixture(scope="module", name="policy")
def policy_fixture(distribution_tf: str) -> str:
    found = re.search(POLICY, distribution_tf, re.DOTALL)
    return found.group(0) if found else ""


@pytest.fixture(scope="module", name="headed")
def headed_fixture(distribution_tf: str) -> Dict[str, str]:
    behaviors = map(_settings, re.findall(BEHAVIOR, distribution_tf, re.DOTALL))
    return {
        one.get("path_pattern", ""): one.get("response_headers_policy_id", "")
        for one in behaviors
    }


def test_a_preflight_to_a_route_the_map_reads_is_answered_by_a_mock(
    map_preflight: Dict[str, Any]
) -> None:
    assert map_preflight.get("x-amazon-apigateway-integration", {}).get("type") == "mock"


def test_a_preflight_to_a_route_the_map_reads_allows_the_map_alone(
    allowed: Dict[str, str]
) -> None:
    assert allowed.get("Origin") == f"'{MAP}'"


def test_a_preflight_to_a_route_the_map_reads_allows_a_read(allowed: Dict[str, str]) -> None:
    assert allowed.get("Methods") == "'GET,OPTIONS'"


def test_a_preflight_to_a_route_the_map_reads_allows_the_token_header(
    allowed: Dict[str, str]
) -> None:
    assert allowed.get("Headers") == "'Authorization'"


def test_a_preflight_to_a_route_the_map_reads_needs_no_token(
    map_preflight: Dict[str, Any]
) -> None:
    assert "security" not in map_preflight


def test_the_map_reads_policy_allows_the_map_alone(policy: str) -> None:
    assert _items(policy, "access_control_allow_origins") == [MAP]


def test_the_map_reads_policy_allows_a_read(policy: str) -> None:
    assert _items(policy, "access_control_allow_methods") == ["GET", "OPTIONS"]


def test_the_map_reads_policy_allows_the_token_header(policy: str) -> None:
    assert _items(policy, "access_control_allow_headers") == ["Authorization"]


def test_the_map_reads_policy_allows_no_credentials(policy: str) -> None:
    assert _settings(policy).get("access_control_allow_credentials") == "false"


def test_the_map_reads_policy_keeps_the_gateways_own_cors_answers(policy: str) -> None:
    assert _settings(policy).get("origin_override") == "false"


@pytest.mark.parametrize("pattern", ["/wan-syntheses", "/wan-syntheses/*"])
def test_every_behavior_the_map_reads_through_carries_the_map_reads_policy(
    headed: Dict[str, str], pattern: str
) -> None:
    assert headed.get(pattern) == MAP_READS_POLICY
