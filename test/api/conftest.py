import json
from typing import Any, Callable, Dict, Tuple
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import boto3
import pytest

API_NAME = "api.10ulabs.com"
REGION = "us-east-2"
STAGE = "prod"


@pytest.fixture(scope="session")
def iam_client() -> Any:
    return boto3.client("iam", region_name=REGION)


@pytest.fixture(scope="session", name="apigateway_client")
def apigateway_client_fixture() -> Any:
    return boto3.client("apigateway", region_name=REGION)


@pytest.fixture(scope="session")
def lambda_client() -> Any:
    return boto3.client("lambda", region_name=REGION)


@pytest.fixture(scope="session")
def dynamodb_client() -> Any:
    return boto3.client("dynamodb", region_name=REGION)


@pytest.fixture(scope="session", name="api_id")
def api_id_fixture(apigateway_client: Any) -> str:
    for api in apigateway_client.get_rest_apis(limit=500)["items"]:
        if api["name"] == API_NAME:
            return str(api["id"])
    raise LookupError(f"REST API '{API_NAME}' not found")


@pytest.fixture(scope="session")
def stage_url(api_id: str) -> str:
    return f"https://{api_id}.execute-api.{REGION}.amazonaws.com/{STAGE}"


def _answer(request: Request) -> Tuple[int, Dict[str, Any]]:
    try:
        with urlopen(request, timeout=10) as response:
            return int(response.status), dict(json.load(response))
    except HTTPError as error:
        return int(error.code), dict(json.load(error))


@pytest.fixture(scope="session")
def get_json() -> Callable[[str], Tuple[int, Dict[str, Any]]]:
    return lambda url: _answer(Request(url))


@pytest.fixture(scope="session")
def post_json() -> Callable[..., Tuple[int, Dict[str, Any]]]:
    def post(
        url: str, body: Any, headers: Dict[str, str] | None = None
    ) -> Tuple[int, Dict[str, Any]]:
        data = json.dumps(body).encode("utf-8")
        sent = {"Content-Type": "application/json", **(headers or {})}
        return _answer(Request(url, data=data, headers=sent, method="POST"))
    return post


@pytest.fixture(scope="session")
def preflight() -> Callable[[str], Dict[str, str]]:
    def options(url: str) -> Dict[str, str]:
        with urlopen(Request(url, method="OPTIONS"), timeout=10) as response:
            return {key.lower(): value for key, value in response.headers.items()}
    return options
