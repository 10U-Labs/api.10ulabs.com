import logging
from types import SimpleNamespace
from typing import Any, Dict, List

import pytest
from botocore.exceptions import ClientError

import cache
from cache import invalidate

DISTRIBUTION_ID = "E2EXAMPLE"
PATHS = ["/carriers", "/carriers/1"]


@pytest.fixture(name="cloudfront")
def cloudfront_fixture(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    cloudfront = SimpleNamespace(invalidations=[], refusing=False)

    def create_invalidation(**request: Any) -> Dict[str, Any]:
        cloudfront.invalidations.append(request)
        if cloudfront.refusing:
            raise ClientError({"Error": {"Code": "AccessDenied"}}, "CreateInvalidation")
        return {"Invalidation": {"Id": "I1"}}

    cloudfront.create_invalidation = create_invalidation
    monkeypatch.setenv("DISTRIBUTION_ID", DISTRIBUTION_ID)
    monkeypatch.setattr(cache, "aws_client", lambda service: {"cloudfront": cloudfront}[service])
    return cloudfront


def _request(cloudfront: SimpleNamespace, index: int = 0) -> Dict[str, Any]:
    invalidations: List[Dict[str, Any]] = cloudfront.invalidations
    return invalidations[index]


def _batch(cloudfront: SimpleNamespace, index: int = 0) -> Dict[str, Any]:
    return dict(_request(cloudfront, index)["InvalidationBatch"])


def test_the_paths_are_invalidated(cloudfront: SimpleNamespace) -> None:
    invalidate(PATHS)
    assert _batch(cloudfront)["Paths"] == {"Quantity": 2, "Items": PATHS}


def test_the_paths_may_arrive_as_any_iterable(cloudfront: SimpleNamespace) -> None:
    invalidate(path for path in PATHS)
    assert _batch(cloudfront)["Paths"]["Items"] == PATHS


def test_the_distribution_is_the_one_the_environment_names(cloudfront: SimpleNamespace) -> None:
    invalidate(PATHS)
    assert _request(cloudfront)["DistributionId"] == DISTRIBUTION_ID


def test_each_call_carries_its_own_caller_reference(cloudfront: SimpleNamespace) -> None:
    invalidate(PATHS)
    invalidate(PATHS)
    assert _batch(cloudfront, 0)["CallerReference"] != _batch(cloudfront, 1)["CallerReference"]


def test_a_refusal_is_not_raised(cloudfront: SimpleNamespace) -> None:
    cloudfront.refusing = True
    assert invalidate(PATHS) is None


def test_a_refusal_is_logged(cloudfront: SimpleNamespace, caplog: pytest.LogCaptureFixture) -> None:
    cloudfront.refusing = True
    with caplog.at_level(logging.ERROR):
        invalidate(PATHS)
    assert f"Error invalidating {PATHS}" in caplog.text
