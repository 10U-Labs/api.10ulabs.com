import json
from typing import Any, Callable, Dict, Tuple
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import boto3
import pytest

API_NAME = "api.10ulabs.com"
REGION = "us-east-2"
STAGE = "prod"
API_KEY_PARAMETER = "/api.10ulabs.com/api-key"


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


@pytest.fixture(scope="session")
def s3_client() -> Any:
    return boto3.client("s3", region_name=REGION)


@pytest.fixture(scope="session")
def scheduler_client() -> Any:
    return boto3.client("scheduler", region_name=REGION)


@pytest.fixture(scope="session", name="ssm_client")
def ssm_client_fixture() -> Any:
    return boto3.client("ssm", region_name=REGION)


@pytest.fixture(scope="session", name="api_key")
def api_key_fixture(ssm_client: Any) -> str:
    parameter = ssm_client.get_parameter(Name=API_KEY_PARAMETER, WithDecryption=True)
    return str(parameter["Parameter"]["Value"])


@pytest.fixture(scope="session", name="bearer")
def bearer_fixture(api_key: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {api_key}"}


@pytest.fixture(scope="session", name="api_id")
def api_id_fixture(apigateway_client: Any) -> str:
    for api in apigateway_client.get_rest_apis(limit=500)["items"]:
        if api["name"] == API_NAME:
            return str(api["id"])
    raise LookupError(f"REST API '{API_NAME}' not found")


@pytest.fixture(scope="session", name="stage_url")
def stage_url_fixture(api_id: str) -> str:
    return f"https://{api_id}.execute-api.{REGION}.amazonaws.com/{STAGE}"


def _decoded(response: Any) -> Any:
    raw = response.read()
    return json.loads(raw) if raw else None


def _answer(request: Request) -> Tuple[int, Any]:
    try:
        with urlopen(request, timeout=10) as response:
            return int(response.status), _decoded(response)
    except HTTPError as error:
        return int(error.code), _decoded(error)


def _bodiless(method: str) -> Callable[..., Tuple[int, Any]]:
    def send(url: str, headers: Dict[str, str] | None = None) -> Tuple[int, Any]:
        return _answer(Request(url, headers=headers or {}, method=method))
    return send


@pytest.fixture(scope="session", name="get_json")
def get_json_fixture() -> Callable[..., Tuple[int, Any]]:
    return _bodiless("GET")


@pytest.fixture(scope="session")
def read_json(
    stage_url: str, get_json: Callable[..., Tuple[int, Any]], bearer: Dict[str, str]
) -> Callable[[str], Any]:
    def read(path: str) -> Any:
        return get_json(f"{stage_url}{path}", bearer)[1]
    return read


@pytest.fixture(scope="session")
def delete_json() -> Callable[..., Tuple[int, Any]]:
    return _bodiless("DELETE")


def _sender(method: str) -> Callable[..., Tuple[int, Any]]:
    def send(url: str, body: Any, headers: Dict[str, str] | None = None) -> Tuple[int, Any]:
        data = json.dumps(body).encode("utf-8")
        sent = {"Content-Type": "application/json", **(headers or {})}
        return _answer(Request(url, data=data, headers=sent, method=method))
    return send


@pytest.fixture(scope="session")
def post_json() -> Callable[..., Tuple[int, Any]]:
    return _sender("POST")


@pytest.fixture(scope="session")
def put_json() -> Callable[..., Tuple[int, Any]]:
    return _sender("PUT")


@pytest.fixture(scope="session")
def preflight() -> Callable[[str], Dict[str, str]]:
    def options(url: str) -> Dict[str, str]:
        with urlopen(Request(url, method="OPTIONS"), timeout=10) as response:
            return {key.lower(): value for key, value in response.headers.items()}
    return options
