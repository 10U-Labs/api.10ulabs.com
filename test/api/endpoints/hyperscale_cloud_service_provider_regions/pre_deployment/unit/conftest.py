from types import ModuleType
from typing import Any, Callable, Dict, List

import pytest


@pytest.fixture
def handler(endpoint: Callable[[str], ModuleType]) -> ModuleType:
    return endpoint("hyperscale_cloud_service_provider_regions")


@pytest.fixture
def regions() -> List[Dict[str, Any]]:
    return [
        {"PK": {"S": "hyperscale-cloud-service-provider-regions"}, "SK": {"S": "#"},
         "next": {"N": "3"}},
        {"PK": {"S": "hyperscale-cloud-service-provider-regions"}, "SK": {"S": "2"},
         "name": {"S": "eu-west-1"}, "municipality": {"S": "Dublin"}, "state": {"S": ""},
         "country": {"S": "Ireland"}, "latitude": {"N": "53.3498"}, "longitude": {"N": "-6.2603"}},
        {"PK": {"S": "hyperscale-cloud-service-provider-regions"}, "SK": {"S": "1"},
         "name": {"S": "us-east-2"}, "municipality": {"S": "Columbus"}, "state": {"S": "OH"},
         "country": {"S": "US"}, "latitude": {"N": "39.9612"}, "longitude": {"N": "-82.9988"}},
    ]
