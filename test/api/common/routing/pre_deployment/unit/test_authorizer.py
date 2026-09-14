from fnmatch import fnmatchcase
from types import ModuleType, SimpleNamespace
from typing import Any, Dict, List

import pytest

STAGE = "arn:aws:execute-api:us-east-2:781581267945:abc123/prod"


def _event(token: str) -> Dict[str, Any]:
    return {"type": "TOKEN", "authorizationToken": token, "methodArn": f"{STAGE}/GET/carriers"}


def _decide(authorizer: ModuleType, token: str) -> Dict[str, Any]:
    return dict(authorizer.lambda_handler(_event(token), None))


def _effect(authorizer: ModuleType, token: str) -> str:
    return str(_decide(authorizer, token)["policyDocument"]["Statement"][0]["Effect"])


def _granted(authorizer: ModuleType, token: str, method: str, path: str) -> bool:
    resource = _decide(authorizer, token)["policyDocument"]["Statement"][0]["Resource"]
    patterns: List[str] = [resource] if isinstance(resource, str) else list(resource)
    return any(fnmatchcase(f"{STAGE}/{method}/{path}", pattern) for pattern in patterns)


def test_the_api_key_is_allowed(authorizer: ModuleType) -> None:
    assert _effect(authorizer, "Bearer the-workflows-key") == "Allow"


def test_the_api_key_is_named_api_key(authorizer: ModuleType) -> None:
    assert _decide(authorizer, "Bearer the-workflows-key")["principalId"] == "api-key"


def test_the_api_key_reads_every_route(authorizer: ModuleType) -> None:
    assert _granted(authorizer, "Bearer the-workflows-key", "GET", "carriers/3/pops")


def test_the_api_key_creates_a_carrier(authorizer: ModuleType) -> None:
    assert _granted(authorizer, "Bearer the-workflows-key", "POST", "carriers")


def test_the_api_key_deletes_a_carrier(authorizer: ModuleType) -> None:
    assert _granted(authorizer, "Bearer the-workflows-key", "DELETE", "carriers/3")


def test_the_api_key_adds_a_pop_to_a_carrier(authorizer: ModuleType) -> None:
    assert _granted(authorizer, "Bearer the-workflows-key", "POST", "carriers/3/pops")


def test_the_api_key_removes_a_pop_of_a_carrier(authorizer: ModuleType) -> None:
    assert _granted(authorizer, "Bearer the-workflows-key", "DELETE", "carriers/3/pops/4")


def test_the_api_key_adds_a_fiber_segment_to_a_carrier(authorizer: ModuleType) -> None:
    assert _granted(authorizer, "Bearer the-workflows-key", "POST", "carriers/3/fiber-segments")


def test_the_api_key_removes_a_fiber_segment_of_a_carrier(authorizer: ModuleType) -> None:
    assert _granted(authorizer, "Bearer the-workflows-key", "DELETE", "carriers/3/fiber-segments/4")


def test_the_api_key_creates_a_region(authorizer: ModuleType) -> None:
    key = "Bearer the-workflows-key"
    assert _granted(authorizer, key, "POST", "hyperscale-cloud-service-provider-regions")


def test_the_api_key_deletes_a_region(authorizer: ModuleType) -> None:
    key = "Bearer the-workflows-key"
    assert _granted(authorizer, key, "DELETE", "hyperscale-cloud-service-provider-regions/3")


def test_the_api_key_creates_a_wan_synthesis(authorizer: ModuleType) -> None:
    assert _granted(authorizer, "Bearer the-workflows-key", "POST", "wan-syntheses")


def test_the_api_key_deletes_a_wan_synthesis(authorizer: ModuleType) -> None:
    assert _granted(authorizer, "Bearer the-workflows-key", "DELETE", "wan-syntheses/3")


@pytest.mark.parametrize("method, path", [
    ("PUT", "wan-syntheses/3"),
    ("PUT", "carriers/3/pops/4"),
    ("PUT", "carriers/3/fiber-segments/4"),
    ("PUT", "carriers/3"),
    ("PUT", "hyperscale-cloud-service-provider-regions/3"),
    ("DELETE", "carriers"),
])
def test_the_api_key_writes_nothing_else_yet(
    authorizer: ModuleType, method: str, path: str
) -> None:
    assert not _granted(authorizer, "Bearer the-workflows-key", method, path)


def test_the_api_key_is_settled_without_asking_google(
    authorizer: ModuleType, google: SimpleNamespace
) -> None:
    _decide(authorizer, "Bearer the-workflows-key")
    assert google.asked == []


def test_the_api_key_is_read_from_the_parameter_the_environment_names(
    authorizer: ModuleType, parameters: SimpleNamespace
) -> None:
    _decide(authorizer, "Bearer the-workflows-key")
    assert parameters.read == ["/api.10ulabs.com/api-key"]


def test_an_authorized_account_is_allowed(authorizer: ModuleType) -> None:
    assert _effect(authorizer, "Bearer an-id-token") == "Allow"


def test_an_authorized_account_is_named_by_its_address(authorizer: ModuleType) -> None:
    assert _decide(authorizer, "Bearer an-id-token")["principalId"] == "someone@10ulabs.com"


def test_an_authorized_account_reaches_every_operation(authorizer: ModuleType) -> None:
    assert _granted(authorizer, "Bearer an-id-token", "DELETE", "carriers/3")


def test_an_authorized_account_is_matched_without_regard_to_case(
    authorizer: ModuleType, google: SimpleNamespace
) -> None:
    google.claims["email"] = "another@10ulabs.com"
    assert _effect(authorizer, "Bearer an-id-token") == "Allow"


def test_the_token_is_sent_to_google_for_its_claims(
    authorizer: ModuleType, google: SimpleNamespace
) -> None:
    _decide(authorizer, "Bearer an-id-token")
    assert google.asked == [("https://oauth2.googleapis.com/tokeninfo?id_token=an-id-token", 5)]


@pytest.mark.parametrize("claim, value", [
    ("email", "stranger@10ulabs.com"),
    ("hd", "example.com"),
    ("email_verified", "false"),
])
def test_an_account_outside_the_list_or_the_domain_or_unverified_is_denied(
    authorizer: ModuleType, google: SimpleNamespace, claim: str, value: str
) -> None:
    google.claims[claim] = value
    assert _effect(authorizer, "Bearer an-id-token") == "Deny"


@pytest.mark.parametrize("claim, value", [
    ("aud", "someone-else.apps.googleusercontent.com"),
    ("iss", "https://example.com"),
])
def test_a_token_for_another_audience_or_issuer_is_unauthorized(
    authorizer: ModuleType, google: SimpleNamespace, claim: str, value: str
) -> None:
    google.claims[claim] = value
    with pytest.raises(authorizer.Unauthorized):
        _decide(authorizer, "Bearer an-id-token")


def test_a_token_google_refuses_is_unauthorized(
    authorizer: ModuleType, google: SimpleNamespace
) -> None:
    google.refusing = True
    with pytest.raises(authorizer.Unauthorized):
        _decide(authorizer, "Bearer an-id-token")


@pytest.mark.parametrize("token", ["", "Bearer", "Basic abc", "an-id-token"])
def test_anything_but_a_bearer_token_is_unauthorized(authorizer: ModuleType, token: str) -> None:
    with pytest.raises(authorizer.Unauthorized):
        _decide(authorizer, token)
