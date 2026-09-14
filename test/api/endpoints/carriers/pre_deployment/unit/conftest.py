from types import ModuleType, SimpleNamespace
from typing import Any, Callable, Dict, List, Optional

import pytest
from botocore.exceptions import ClientError


@pytest.fixture(name="store")
def store_fixture() -> SimpleNamespace:
    store = SimpleNamespace(items=[], failing=False, queries=[], gets=[], updates=[])

    def refuse(operation: str) -> None:
        if store.failing:
            raise ClientError({"Error": {"Code": "InternalServerError"}}, operation)

    def held(key: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        items: List[Dict[str, Any]] = store.items
        for item in items:
            if item["PK"] == key["PK"] and item["SK"] == key["SK"]:
                return item
        return None

    def counter(key: Dict[str, Any]) -> Dict[str, Any]:
        item = held(key)
        if item is None:
            item = {**key, "next": {"N": "1"}}
            store.items.append(item)
        return item

    def rename(request: Dict[str, Any]) -> Dict[str, Any]:
        item = held(request["Key"])
        if item is None:
            raise ClientError({"Error": {"Code": "ConditionalCheckFailedException"}}, "UpdateItem")
        item["name"] = request["ExpressionAttributeValues"][":name"]
        return {"Attributes": item}

    def query(**request: Any) -> Dict[str, Any]:
        store.queries.append(request)
        refuse("Query")
        partition = request["ExpressionAttributeValues"][":pk"]["S"]
        found: List[Dict[str, Any]] = [item for item in store.items if item["PK"]["S"] == partition]
        return {"Items": found, "Count": len(found)}

    def get_item(**request: Any) -> Dict[str, Any]:
        store.gets.append(request)
        refuse("GetItem")
        item = held(request["Key"])
        return {} if item is None else {"Item": item}

    def update_item(**request: Any) -> Dict[str, Any]:
        store.updates.append(request)
        refuse("UpdateItem")
        if "ConditionExpression" in request:
            return rename(request)
        item = counter(request["Key"])
        item["next"] = {"N": str(int(item["next"]["N"]) + 1)}
        return {"Attributes": {"next": item["next"]}}

    def put_item(**request: Any) -> Dict[str, Any]:
        refuse("PutItem")
        store.items.append(request["Item"])
        return {}

    store.query = query
    store.get_item = get_item
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
