import json
from typing import Any, Callable, Dict, Tuple
from urllib.error import HTTPError
from urllib.request import urlopen

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


@pytest.fixture(scope="session")
def get_json() -> Callable[[str], Tuple[int, Dict[str, Any]]]:
    def get(url: str) -> Tuple[int, Dict[str, Any]]:
        try:
            with urlopen(url, timeout=10) as response:
                return int(response.status), dict(json.load(response))
        except HTTPError as error:
            return int(error.code), dict(json.load(error))
    return get
