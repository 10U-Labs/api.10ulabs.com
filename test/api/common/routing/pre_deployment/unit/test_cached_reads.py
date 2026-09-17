import re
from fnmatch import fnmatchcase
from pathlib import Path
from typing import Dict, List

import pytest

POLICY = r'resource "aws_cloudfront_cache_policy" "reads" \{.*?\n\}'
DEFAULT = r"default_cache_behavior \{.*?\n  \}"
BEHAVIOR = r"ordered_cache_behavior \{.*?\n  \}"
READS_POLICY = "aws_cloudfront_cache_policy.reads.id"
DISABLED_POLICY = "data.aws_cloudfront_cache_policy.disabled.id"
A_DAY = "86400"
REGIONS = "/hyperscale-cloud-service-provider-regions"
SYNTHESIS = "/wan-syntheses/1"
PARTS = [
    "wan-pops", "wan-pops/1", "backbone-circuits", "homing-circuits", "fiber-segments", "sites",
    "sites/1", "hyperscale-cloud-service-provider-regions",
    "hyperscale-cloud-service-provider-regions/1", "off-net", "forced-wan-pops",
    "forced-circuits", "forced-homes", "prohibited-wan-pops", "prohibited-circuits",
    "degree-exempt-wan-pops",
]
CACHED_READS = [
    "/carriers", "/carriers/1", "/carriers/1/pops", "/carriers/1/pops/1",
    "/carriers/1/fiber-segments", "/carriers/1/fiber-segments/1",
    REGIONS, f"{REGIONS}/1",
    "/rack-configurations/abcdefghi",
    "/wan-syntheses", SYNTHESIS, *(f"{SYNTHESIS}/{part}" for part in PARTS),
]
EVERY_METHOD = ("DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT")


def _setting(block: str, name: str) -> str:
    match = re.search(rf"\b{name}\s*=\s*(.+)", block)
    return "" if match is None else match.group(1).strip()


def _listed(block: str, name: str) -> List[str]:
    inside = _setting(block, name).strip("[]")
    return [one.strip(' "') for one in inside.split(",") if one.strip()]


@pytest.fixture(scope="module", name="cloudfront_tf")
def cloudfront_tf_fixture(routing_dir: Path) -> str:
    return (routing_dir / "cloudfront.tf").read_text(encoding="utf-8")


@pytest.fixture(scope="module", name="reads_policy")
def reads_policy_fixture(cloudfront_tf: str) -> str:
    match = re.search(POLICY, cloudfront_tf, re.DOTALL)
    return "" if match is None else match.group(0)


@pytest.fixture(scope="module", name="cached")
def cached_fixture(cloudfront_tf: str) -> Dict[str, str]:
    behaviors = re.findall(BEHAVIOR, cloudfront_tf, re.DOTALL)
    return {
        _setting(one, "path_pattern").strip('"'): one
        for one in behaviors if _setting(one, "cache_policy_id") == READS_POLICY
    }


@pytest.fixture(scope="module", name="default_behavior")
def default_behavior_fixture(cloudfront_tf: str) -> str:
    match = re.search(DEFAULT, cloudfront_tf, re.DOTALL)
    return "" if match is None else match.group(0)


def test_the_stack_declares_a_cache_policy_for_the_reads(reads_policy: str) -> None:
    assert reads_policy.startswith('resource "aws_cloudfront_cache_policy" "reads"')


def test_the_reads_policy_keys_on_the_authorization_header_alone(reads_policy: str) -> None:
    keyed = (_setting(reads_policy, "header_behavior"), _listed(reads_policy, "items"))
    assert keyed == ('"whitelist"', ["Authorization"])


def test_the_reads_policy_keys_on_no_query_string(reads_policy: str) -> None:
    assert _setting(reads_policy, "query_string_behavior") == '"none"'


def test_the_reads_policy_keys_on_no_cookie(reads_policy: str) -> None:
    assert _setting(reads_policy, "cookie_behavior") == '"none"'


def test_a_read_is_held_for_as_little_as_it_asks(reads_policy: str) -> None:
    assert _setting(reads_policy, "min_ttl") == "0"


def test_a_read_is_held_a_day_when_it_does_not_say(reads_policy: str) -> None:
    assert _setting(reads_policy, "default_ttl") == A_DAY


def test_a_read_is_held_a_day_at_most(reads_policy: str) -> None:
    assert _setting(reads_policy, "max_ttl") == A_DAY


@pytest.mark.parametrize("path", CACHED_READS)
def test_every_read_that_is_cached_is_cached_under_the_reads_policy(
    cached: Dict[str, str], path: str
) -> None:
    assert any(fnmatchcase(path, pattern) for pattern in cached)


def test_a_cached_read_is_served_by_the_gateway(cached: Dict[str, str]) -> None:
    assert {_setting(one, "target_origin_id") for one in cached.values()} == {'"gateway"'}


def test_a_cached_read_caches_get_and_head_alone(cached: Dict[str, str]) -> None:
    assert {tuple(_listed(one, "cached_methods")) for one in cached.values()} == {("GET", "HEAD")}


def test_a_cached_read_lets_every_method_through_to_the_gateway(cached: Dict[str, str]) -> None:
    assert {tuple(_listed(one, "allowed_methods")) for one in cached.values()} == {EVERY_METHOD}


def test_the_default_behavior_stays_caching_disabled(default_behavior: str) -> None:
    assert _setting(default_behavior, "cache_policy_id") == DISABLED_POLICY
