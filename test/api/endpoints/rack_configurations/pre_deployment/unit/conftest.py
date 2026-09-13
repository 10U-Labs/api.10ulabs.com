from types import ModuleType, SimpleNamespace
from typing import Any, Callable, Dict, List

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

    table.put_item = put_item
    return table


@pytest.fixture
def rack_handler(
    load_handler: Callable[[str], ModuleType],
    monkeypatch: pytest.MonkeyPatch,
    table: SimpleNamespace,
) -> ModuleType:
    handler = load_handler("api/endpoints/rack_configurations")
    monkeypatch.setenv("RACK_CONFIGURATIONS_TABLE", "configurations")
    monkeypatch.setattr(handler, "aws_client", lambda service: {"dynamodb": table}[service])
    return handler


@pytest.fixture
def configuration() -> Dict[str, Any]:
    return {
        "rackHeight": 42,
        "rackCount": 2,
        "placedParts": [{"id": "p1", "type": "server", "size": 2, "rackId": 1, "startSlot": 3}],
    }
