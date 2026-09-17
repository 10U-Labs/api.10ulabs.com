from types import ModuleType, SimpleNamespace
from typing import Any, Callable, Dict, Iterable, List

import pytest
from botocore.exceptions import ClientError


@pytest.fixture(name="table")
def table_fixture() -> SimpleNamespace:
    table = SimpleNamespace(items=[], failing=False)

    def put_item(**request: Any) -> None:
        if table.failing:
            raise ClientError({"Error": {"Code": "InternalServerError"}}, "PutItem")
        stored: List[str] = [item["config_hash"]["S"] for item in table.items]
        if request["Item"]["config_hash"]["S"] in stored:
            raise ClientError({"Error": {"Code": "ConditionalCheckFailedException"}}, "PutItem")
        table.items.append(request["Item"])

    def get_item(**request: Any) -> Dict[str, Any]:
        wanted = request["Key"]["config_hash"]["S"]
        found = [item for item in table.items if item["config_hash"]["S"] == wanted]
        return {"Item": found[0]} if found else {}

    table.put_item = put_item
    table.get_item = get_item
    return table


@pytest.fixture(name="distribution")
def distribution_fixture() -> SimpleNamespace:
    distribution = SimpleNamespace(invalidated=[])

    def invalidate(paths: Iterable[str]) -> None:
        distribution.invalidated.append(list(paths))

    distribution.invalidate = invalidate
    return distribution


@pytest.fixture
def rack_handler(
    load_handler: Callable[..., ModuleType],
    monkeypatch: pytest.MonkeyPatch,
    table: SimpleNamespace,
    distribution: SimpleNamespace,
) -> ModuleType:
    handler = load_handler("api/endpoints/rack_configurations")
    monkeypatch.setenv("RACK_CONFIGURATIONS_TABLE", "configurations")
    monkeypatch.setattr(handler, "aws_client", lambda service: {"dynamodb": table}[service])
    monkeypatch.setattr(handler, "invalidate", distribution.invalidate, raising=False)
    return handler


@pytest.fixture
def configuration() -> Dict[str, Any]:
    return {
        "rackHeight": 42,
        "rackCount": 2,
        "placedParts": [{"id": "p1", "type": "server", "size": 2, "rackId": 1, "startSlot": 3}],
    }
