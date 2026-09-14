from types import ModuleType, SimpleNamespace
from typing import Any, Callable, Dict, List

import pytest
from botocore.exceptions import ClientError


@pytest.fixture(name="store")
def store_fixture() -> SimpleNamespace:
    store = SimpleNamespace(items=[], failing=False, queries=[], updates=[])

    def refuse(operation: str) -> None:
        if store.failing:
            raise ClientError({"Error": {"Code": "InternalServerError"}}, operation)

    def counter(key: Dict[str, Any]) -> Dict[str, Any]:
        items: List[Dict[str, Any]] = store.items
        for item in items:
            if item["PK"] == key["PK"] and item["SK"] == key["SK"]:
                return item
        item = {**key, "next": {"N": "1"}}
        store.items.append(item)
        return item

    def query(**request: Any) -> Dict[str, Any]:
        store.queries.append(request)
        refuse("Query")
        partition = request["ExpressionAttributeValues"][":pk"]["S"]
        found: List[Dict[str, Any]] = [item for item in store.items if item["PK"]["S"] == partition]
        return {"Items": found, "Count": len(found)}

    def update_item(**request: Any) -> Dict[str, Any]:
        store.updates.append(request)
        refuse("UpdateItem")
        item = counter(request["Key"])
        item["next"] = {"N": str(int(item["next"]["N"]) + 1)}
        return {"Attributes": {"next": item["next"]}}

    def put_item(**request: Any) -> Dict[str, Any]:
        refuse("PutItem")
        store.items.append(request["Item"])
        return {}

    store.query = query
    store.update_item = update_item
    store.put_item = put_item
    return store


@pytest.fixture
def carriers_handler(
    load_handler: Callable[..., ModuleType],
    monkeypatch: pytest.MonkeyPatch,
    store: SimpleNamespace,
) -> ModuleType:
    handler = load_handler("api/endpoints/carriers")
    monkeypatch.setenv("STORE_TABLE", "store")
    monkeypatch.setattr(handler, "aws_client", lambda service: {"dynamodb": store}[service])
    return handler


@pytest.fixture
def carriers() -> List[Dict[str, Any]]:
    return [
        {"PK": {"S": "carriers"}, "SK": {"S": "#"}, "next": {"N": "3"}},
        {"PK": {"S": "carriers"}, "SK": {"S": "2"}, "name": {"S": "zayo"},
         "next_pop": {"N": "1"}, "next_fiber_segment": {"N": "1"}},
        {"PK": {"S": "carriers"}, "SK": {"S": "1"}, "name": {"S": "lumen"},
         "next_pop": {"N": "4"}, "next_fiber_segment": {"N": "2"}},
        {"PK": {"S": "carriers/1"}, "SK": {"S": "pops/3"}, "name": {"S": "ord1"}},
    ]
