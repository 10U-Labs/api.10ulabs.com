import json
from types import ModuleType, SimpleNamespace
from typing import Any, Dict, List

import pytest

EVENTS = "/sessions/{session_id}/events"


def _post(body: Any, session_id: str = "session-1") -> Dict[str, Any]:
    raw = body if isinstance(body, str) else json.dumps(body)
    return {"resource": EVENTS, "httpMethod": "POST", "body": raw,
            "pathParameters": {"session_id": session_id}}


def _request(events: Any, **extra: Any) -> Dict[str, Any]:
    return {"device_id": "device-1", "events": events, **extra}


def _answer(tracker: ModuleType, event: Dict[str, Any]) -> Dict[str, Any]:
    return dict(tracker.lambda_handler(event, None))


def _body(tracker: ModuleType, event: Dict[str, Any]) -> Dict[str, Any]:
    return dict(json.loads(_answer(tracker, event)["body"]))


def test_events_are_recorded(
    tracker: ModuleType, events: List[Dict[str, Any]], events_table: SimpleNamespace
) -> None:
    _answer(tracker, _post(_request(events)))
    assert [item["event_type"]["S"] for item in events_table.items] == ["page_view", "click"]


def test_recorded_events_answer_200(tracker: ModuleType, events: List[Dict[str, Any]]) -> None:
    assert _answer(tracker, _post(_request(events)))["statusCode"] == 200


def test_the_answer_counts_the_events(tracker: ModuleType, events: List[Dict[str, Any]]) -> None:
    assert _body(tracker, _post(_request(events)))["events_saved"] == 2


def test_an_event_is_recorded_under_its_session(
    tracker: ModuleType, events: List[Dict[str, Any]], events_table: SimpleNamespace
) -> None:
    _answer(tracker, _post(_request(events), session_id="session-9"))
    assert events_table.items[0]["session_id"]["S"] == "session-9"


def test_an_event_keeps_its_whole_payload(
    tracker: ModuleType, events: List[Dict[str, Any]], events_table: SimpleNamespace
) -> None:
    _answer(tracker, _post(_request(events)))
    assert json.loads(events_table.items[1]["event_data"]["S"]) == events[1]


def test_the_session_context_is_recorded_with_each_event(
    tracker: ModuleType, events: List[Dict[str, Any]], events_table: SimpleNamespace
) -> None:
    _answer(tracker, _post(_request(events, session_context={"referrer": "x"})))
    assert json.loads(events_table.items[0]["session_context"]["S"]) == {"referrer": "x"}


def test_unprocessed_events_are_written_again(
    tracker: ModuleType, events: List[Dict[str, Any]], events_table: SimpleNamespace
) -> None:
    events_table.refusals = 2
    _answer(tracker, _post(_request(events)))
    assert len(events_table.items) == 2


def test_events_still_unprocessed_after_every_attempt_answer_500(
    tracker: ModuleType, events: List[Dict[str, Any]], events_table: SimpleNamespace
) -> None:
    events_table.refusals = 99
    assert _answer(tracker, _post(_request(events)))["statusCode"] == 500


def test_a_table_that_refuses_the_write_answers_500(
    tracker: ModuleType, events: List[Dict[str, Any]], events_table: SimpleNamespace
) -> None:
    events_table.failing = True
    assert _answer(tracker, _post(_request(events)))["statusCode"] == 500


def test_a_missing_session_is_refused(tracker: ModuleType, events: List[Dict[str, Any]]) -> None:
    event = {**_post(_request(events)), "pathParameters": None}
    assert _body(tracker, event)["error"] == "Invalid path: missing session_id"


@pytest.mark.parametrize("request_body, error", [
    ({"events": []}, "Missing required field: device_id"),
    ({"device_id": "d"}, "Missing required field: events"),
    ({"device_id": 1, "events": []}, "device_id must be a string"),
    ({"device_id": "d", "events": {}}, "events must be an array"),
    ({"device_id": "d", "events": []}, "events array cannot be empty"),
    ({"device_id": "d", "events": [{}] * 26}, "events array cannot exceed 25 items"),
])
def test_an_invalid_request_is_refused(
    tracker: ModuleType, request_body: Dict[str, Any], error: str
) -> None:
    assert _body(tracker, _post(request_body))["error"] == error


@pytest.mark.parametrize("event, details", [
    ("text", "Event 0: event must be an object"),
    ({"timestamp": "2026-09-13T10:00:00Z"}, "Event 0: Missing required field: event_type"),
    ({"event_type": "click"}, "Event 0: Missing required field: timestamp"),
    ({"event_type": 1, "timestamp": "2026-09-13T10:00:00"}, "Event 0: event_type must be a string"),
    ({"event_type": "click", "timestamp": 1}, "Event 0: timestamp must be a string"),
    ({"event_type": "a", "timestamp": "yesterday"}, "Event 0: timestamp must be in ISO8601 format"),
])
def test_an_invalid_event_is_named(tracker: ModuleType, event: Any, details: str) -> None:
    assert _body(tracker, _post(_request([event])))["details"] == details


def test_every_invalid_event_is_named(tracker: ModuleType) -> None:
    body = _body(tracker, _post(_request([{"event_type": "a"}, {"timestamp": "b"}])))
    assert body["details"].count("Event ") == 2


def test_an_invalid_event_answers_400(tracker: ModuleType) -> None:
    assert _answer(tracker, _post(_request([{}])))["statusCode"] == 400


def test_a_body_that_is_not_json_is_refused(tracker: ModuleType) -> None:
    assert _body(tracker, _post("not json"))["error"] == "Invalid JSON"


def test_every_answer_allows_any_origin(tracker: ModuleType) -> None:
    response = _answer(tracker, {"resource": "/other", "httpMethod": "GET"})
    assert response["headers"]["Access-Control-Allow-Origin"] == "*"


def test_another_resource_answers_404(tracker: ModuleType) -> None:
    assert _answer(tracker, {"resource": "/other", "httpMethod": "GET"})["statusCode"] == 404
