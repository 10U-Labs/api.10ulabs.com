import json
from typing import Any, Dict

POPS = "/carriers/{id}/pops"
POP = "/carriers/{id}/pops/{pop_id}"
CHICAGO = {"id": 3, "municipality": "Chicago", "state": "IL", "country": "US",
           "latitude": 41.8781, "longitude": -87.6298}
DENVER = {"id": 1, "municipality": "Denver", "state": "CO", "country": "US",
          "latitude": 39.7392, "longitude": -104.9903}
BOISE = {"municipality": "Boise", "state": "ID", "country": "US",
         "latitude": 43.615, "longitude": -116.2023}
AMSTERDAM = {"municipality": "Amsterdam", "state": "", "country": "Netherlands",
             "latitude": 52.3731, "longitude": 4.8925}
POP_BODY = 'The body must be exactly {"municipality", "state", "country", "latitude", "longitude"}'
MISPLACED = [
    {},
    {**BOISE, "id": 9},
    {**BOISE, "latitude": "43.615"},
    {**BOISE, "longitude": True},
    {**BOISE, "municipality": ""},
    {**BOISE, "state": None},
    {**BOISE, "country": ""},
    dict(list(BOISE.items())[:4]),
    [BOISE],
]


def get_pops(carrier: str = "1") -> Dict[str, Any]:
    return {"resource": POPS, "httpMethod": "GET", "pathParameters": {"id": carrier}}


def post_pop(body: Any, carrier: str = "1") -> Dict[str, Any]:
    event = {"resource": POPS, "httpMethod": "POST", "body": json.dumps(body)}
    return {**event, "pathParameters": {"id": carrier}}


def get_pop(carrier: str = "1", pop: str = "3") -> Dict[str, Any]:
    event = {"resource": POP, "httpMethod": "GET"}
    return {**event, "pathParameters": {"id": carrier, "pop_id": pop}}


def put_pop(body: Any, carrier: str = "1", pop: str = "3") -> Dict[str, Any]:
    return {**get_pop(carrier, pop), "httpMethod": "PUT", "body": json.dumps(body)}


def delete_pop(carrier: str = "1", pop: str = "3") -> Dict[str, Any]:
    return {**get_pop(carrier, pop), "httpMethod": "DELETE"}
