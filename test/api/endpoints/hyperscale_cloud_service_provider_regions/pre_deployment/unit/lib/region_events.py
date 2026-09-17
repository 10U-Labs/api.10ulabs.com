import json
from typing import Any, Dict

REGIONS = "/hyperscale-cloud-service-provider-regions"
REGION = "/hyperscale-cloud-service-provider-regions/{id}"
MISSING = "No such hyperscale cloud service provider region"
COLUMBUS = {"id": 1, "name": "Provider A", "municipality": "Columbus", "state": "OH",
            "country": "US", "latitude": 39.9612, "longitude": -82.9988}
DUBLIN = {"id": 2, "name": "Provider B", "municipality": "Dublin", "state": "",
          "country": "Ireland", "latitude": 53.3498, "longitude": -6.2603}
PHOENIX = {"name": "Provider C", "municipality": "Phoenix", "state": "AZ", "country": "US",
           "latitude": 33.4484, "longitude": -112.074}
FRANKFURT = {"name": "Provider D", "municipality": "Frankfurt", "state": "", "country": "Germany",
             "latitude": 50.1109, "longitude": 8.6821}
REGION_BODY = (
    'The body must be exactly '
    '{"name", "municipality", "state", "country", "latitude", "longitude"}'
)
MISPLACED = [
    {},
    {**PHOENIX, "id": 9},
    {**PHOENIX, "latitude": "33.4484"},
    {**PHOENIX, "longitude": True},
    {**PHOENIX, "name": ""},
    {**PHOENIX, "municipality": ""},
    {**PHOENIX, "country": ""},
    {**PHOENIX, "state": None},
    dict(list(PHOENIX.items())[:4]),
    [PHOENIX],
]


def get(resource: str = REGIONS) -> Dict[str, Any]:
    return {"resource": resource, "httpMethod": "GET"}


def post(body: Any) -> Dict[str, Any]:
    return {"resource": REGIONS, "httpMethod": "POST", "body": json.dumps(body)}


def get_one(region: str) -> Dict[str, Any]:
    return {**get(REGION), "pathParameters": {"id": region}}


def put(body: Any, region: str = "2") -> Dict[str, Any]:
    correction = {**post(body), "resource": REGION, "httpMethod": "PUT"}
    return {**correction, "pathParameters": {"id": region}}


def delete(region: str = "2") -> Dict[str, Any]:
    return {**get_one(region), "httpMethod": "DELETE"}
