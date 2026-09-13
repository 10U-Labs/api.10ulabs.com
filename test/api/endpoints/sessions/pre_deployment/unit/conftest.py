from types import ModuleType, SimpleNamespace
from typing import Any, Callable, Dict, List

import pytest
from botocore.exceptions import ClientError


@pytest.fixture(name="events_table")
def events_table_fixture() -> SimpleNamespace:
    table = SimpleNamespace(items=[], failing=False, refusals=0)

    def batch_write_item(**request: Any) -> Dict[str, Any]:
        if table.failing:
            raise ClientError({"Error": {"Code": "InternalServerError"}}, "BatchWriteItem")
        writes: List[Dict[str, Any]] = request["RequestItems"]["events"]
        unprocessed: List[Dict[str, Any]] = []
        if table.refusals:
            table.refusals -= 1
            writes, unprocessed = writes[:-1], writes[-1:]
        table.items.extend(write["PutRequest"]["Item"] for write in writes)
        return {"UnprocessedItems": {"events": unprocessed} if unprocessed else {}}

    table.batch_write_item = batch_write_item
    return table


@pytest.fixture
def tracker(
    load_handler: Callable[..., ModuleType],
    monkeypatch: pytest.MonkeyPatch,
    events_table: SimpleNamespace,
) -> ModuleType:
    handler = load_handler("api/endpoints/sessions", "lambda/tracker")
    monkeypatch.setenv("SESSION_EVENTS_TABLE", "events")
    monkeypatch.setattr(handler, "aws_client", lambda service: {"dynamodb": events_table}[service])
    monkeypatch.setattr(handler, "time", SimpleNamespace(sleep=lambda _: None))
    return handler


@pytest.fixture(name="exports")
def exports_fixture() -> SimpleNamespace:
    exports = SimpleNamespace(started=[])

    def export_table_to_point_in_time(**request: Any) -> Dict[str, Any]:
        exports.started.append(request)
        return {"ExportDescription": {"ExportArn": "arn:aws:dynamodb:us-east-2:1:export/1"}}

    exports.export_table_to_point_in_time = export_table_to_point_in_time
    return exports


@pytest.fixture
def exporter(
    load_handler: Callable[..., ModuleType],
    monkeypatch: pytest.MonkeyPatch,
    exports: SimpleNamespace,
) -> ModuleType:
    handler = load_handler("api/endpoints/sessions", "lambda/exporter")
    monkeypatch.setenv("DYNAMODB_TABLE_ARN", "arn:aws:dynamodb:us-east-2:1:table/events")
    monkeypatch.setenv("S3_BUCKET", "analytics")
    monkeypatch.setenv("S3_PREFIX", "exports/events")
    monkeypatch.setattr(handler, "boto3", SimpleNamespace(client=lambda _: exports))
    return handler


@pytest.fixture
def events() -> List[Dict[str, Any]]:
    return [
        {"event_type": "page_view", "timestamp": "2026-09-13T10:00:00Z", "page": "/"},
        {"event_type": "click", "timestamp": "2026-09-13T10:00:05Z", "target": "cta"},
    ]
