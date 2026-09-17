import json
from typing import Any, Dict

FIBER_SEGMENTS = "/carriers/{id}/fiber-segments"
FIBER_SEGMENT = "/carriers/{id}/fiber-segments/{fiber_segment_id}"
DEN_ORD = {"id": 1, "a_municipality": "Denver", "a_state": "CO",
           "z_municipality": "Chicago", "z_state": "IL", "submarine": False}
NYC_AMS = {"id": 3, "a_municipality": "New York", "a_state": "NY",
           "z_municipality": "Amsterdam", "z_state": "", "submarine": True}
DEN_SLC = {"a_municipality": "Denver", "a_state": "CO",
           "z_municipality": "Salt Lake City", "z_state": "UT", "submarine": False}
LON_PAR = {"a_municipality": "London", "a_state": "",
           "z_municipality": "Paris", "z_state": "", "submarine": True}
FIBER_SEGMENT_BODY = (
    'The body must be exactly '
    '{"a_municipality", "a_state", "z_municipality", "z_state", "submarine"}'
)
UNSPANNED = [
    {},
    {**DEN_SLC, "id": 9},
    {**DEN_SLC, "submarine": "false"},
    {**DEN_SLC, "submarine": 0},
    {**DEN_SLC, "a_municipality": ""},
    {**DEN_SLC, "z_municipality": ""},
    {**DEN_SLC, "a_state": None},
    {**DEN_SLC, "z_state": 1},
    dict(list(DEN_SLC.items())[:4]),
    [DEN_SLC],
]


def get_fiber_segments(carrier: str = "1") -> Dict[str, Any]:
    event = {"resource": FIBER_SEGMENTS, "httpMethod": "GET"}
    return {**event, "pathParameters": {"id": carrier}}


def post_fiber_segment(body: Any, carrier: str = "1") -> Dict[str, Any]:
    event = {"resource": FIBER_SEGMENTS, "httpMethod": "POST", "body": json.dumps(body)}
    return {**event, "pathParameters": {"id": carrier}}


def get_fiber_segment(carrier: str = "1", fiber_segment: str = "3") -> Dict[str, Any]:
    event = {"resource": FIBER_SEGMENT, "httpMethod": "GET"}
    return {**event, "pathParameters": {"id": carrier, "fiber_segment_id": fiber_segment}}


def put_fiber_segment(body: Any, carrier: str = "1", fiber_segment: str = "3") -> Dict[str, Any]:
    event = {"resource": FIBER_SEGMENT, "httpMethod": "PUT", "body": json.dumps(body)}
    return {**event, "pathParameters": {"id": carrier, "fiber_segment_id": fiber_segment}}


def delete_fiber_segment(carrier: str = "1", fiber_segment: str = "3") -> Dict[str, Any]:
    return {**get_fiber_segment(carrier, fiber_segment), "httpMethod": "DELETE"}
