import json
from typing import Any, Callable, Dict, Tuple
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

API_NAME = "api.10ulabs.com"
STAGE = "prod"


@pytest.fixture(scope="session", name="api_id")
def api_id_fixture(apigateway_client: Any) -> str:
    for api in apigateway_client.get_rest_apis(limit=500)["items"]:
        if api["name"] == API_NAME:
            return str(api["id"])
    raise LookupError(f"REST API '{API_NAME}' not found")


@pytest.fixture(scope="session")
def stage_url(api_id: str) -> str:
    return f"https://{api_id}.execute-api.us-east-2.amazonaws.com/{STAGE}"


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
def post_json() -> Callable[[str, Any], Tuple[int, Dict[str, Any]]]:
    def post(url: str, body: Any) -> Tuple[int, Dict[str, Any]]:
        data = json.dumps(body).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        return _answer(Request(url, data=data, headers=headers, method="POST"))
    return post
