import json
from types import ModuleType
from typing import Any, Callable, Dict, List

import pytest

from region_events import get, get_one


@pytest.fixture
def handler(request: pytest.FixtureRequest, endpoint: Callable[..., ModuleType]) -> ModuleType:
    return endpoint("hyperscale_cloud_service_provider_regions", request.module.HANDLER)


@pytest.fixture
def listed(endpoint: Callable[..., ModuleType]) -> Callable[[], Any]:
    lister = endpoint("hyperscale_cloud_service_provider_regions", "lambda/list_regions")

    def listing() -> Any:
        return json.loads(lister.lambda_handler(get(), None)["body"])
    return listing


@pytest.fixture
def region_read(endpoint: Callable[..., ModuleType]) -> Callable[[], Dict[str, Any]]:
    reader = endpoint("hyperscale_cloud_service_provider_regions", "lambda/read_region")

    def reading() -> Dict[str, Any]:
        return dict(reader.lambda_handler(get_one("2"), None))
    return reading


@pytest.fixture
def regions() -> List[Dict[str, Any]]:
    return [
        {"PK": {"S": "hyperscale-cloud-service-provider-regions"}, "SK": {"S": "#"},
         "next": {"N": "3"}},
        {"PK": {"S": "hyperscale-cloud-service-provider-regions"}, "SK": {"S": "2"},
         "name": {"S": "Provider B"}, "municipality": {"S": "Dublin"}, "state": {"S": ""},
         "country": {"S": "Ireland"}, "latitude": {"N": "53.3498"}, "longitude": {"N": "-6.2603"}},
        {"PK": {"S": "hyperscale-cloud-service-provider-regions"}, "SK": {"S": "1"},
         "name": {"S": "Provider A"}, "municipality": {"S": "Columbus"}, "state": {"S": "OH"},
         "country": {"S": "US"}, "latitude": {"N": "39.9612"}, "longitude": {"N": "-82.9988"}},
    ]
