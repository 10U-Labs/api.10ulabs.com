import json
from types import ModuleType, SimpleNamespace
from typing import Any, Callable, Dict, Iterable, List

import pytest
from botocore.exceptions import ClientError

from rack_events import post, submission


@pytest.fixture(name="table")
def table_fixture() -> SimpleNamespace:
    table = SimpleNamespace(items=[], failing=False)

    def put_item(**request: Any) -> None:
        if table.failing:
            raise ClientError({"Error": {"Code": "InternalServerError"}}, "PutItem")
        hashes: List[str] = [item["config_hash"]["S"] for item in table.items]
        if request["Item"]["config_hash"]["S"] in hashes:
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


@pytest.fixture(name="rack")
def rack_fixture(
    load_handler: Callable[..., ModuleType],
    monkeypatch: pytest.MonkeyPatch,
    table: SimpleNamespace,
    distribution: SimpleNamespace,
) -> Callable[[str], ModuleType]:
    def load(verb: str) -> ModuleType:
        module = load_handler("api/endpoints/rack_configurations", f"lambda/{verb}")
        monkeypatch.setenv("RACK_CONFIGURATIONS_TABLE", "configurations")
        monkeypatch.setattr(module, "aws_client", lambda service: {"dynamodb": table}[service])
        monkeypatch.setattr(module, "invalidate", distribution.invalidate, raising=False)
        return module
    return load


@pytest.fixture
def handler(request: pytest.FixtureRequest, rack: Callable[[str], ModuleType]) -> ModuleType:
    return rack(request.module.HANDLER)


@pytest.fixture
def stored(rack: Callable[[str], ModuleType]) -> Callable[[Dict[str, Any]], str]:
    storer = rack("store_rack_configuration")

    def storing(submitted: Dict[str, Any]) -> str:
        answer = storer.lambda_handler(post(submission(submitted)), None)
        return str(json.loads(answer["body"])["config_hash"])
    return storing


@pytest.fixture
def configuration() -> Dict[str, Any]:
    return {
        "rackHeight": 42,
        "rackCount": 2,
        "placedParts": [{"id": "p1", "type": "server", "size": 2, "rackId": 1, "startSlot": 3}],
    }
