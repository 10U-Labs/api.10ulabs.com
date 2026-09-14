import json
from types import ModuleType, SimpleNamespace
from typing import Any, Callable, Dict, List, Optional

import pytest
from botocore.exceptions import ClientError

import store as library
from lambda_http import Handler

Served = Callable[[Dict[str, Any]], Any]


@pytest.fixture(name="store")
def store_fixture() -> SimpleNamespace:
    store = SimpleNamespace(
        items=[], failing=False, queries=[], gets=[], updates=[], deletes=[], puts=[]
    )

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
            item = dict(key)
            store.items.append(item)
        return item

    def required(key: Dict[str, Any], operation: str) -> Dict[str, Any]:
        item = held(key)
        if item is None:
            raise ClientError({"Error": {"Code": "ConditionalCheckFailedException"}}, operation)
        return item

    def rename(request: Dict[str, Any], item: Dict[str, Any]) -> Dict[str, Any]:
        item["name"] = request["ExpressionAttributeValues"][":name"]
        return {"Attributes": item}

    def advance(request: Dict[str, Any], item: Dict[str, Any]) -> Dict[str, Any]:
        field = request["ExpressionAttributeNames"]["#next"]
        item[field] = {"N": str(int(item.get(field, {"N": "1"})["N"]) + 1)}
        return {"Attributes": {field: item[field]}}

    def query(**request: Any) -> Dict[str, Any]:
        store.queries.append(request)
        refuse("Query")
        values = request["ExpressionAttributeValues"]
        prefix = values.get(":prefix", {"S": ""})["S"]
        found: List[Dict[str, Any]] = [
            item for item in store.items
            if item["PK"] == values[":pk"] and item["SK"]["S"].startswith(prefix)
        ]
        return {"Items": found, "Count": len(found)}

    def get_item(**request: Any) -> Dict[str, Any]:
        store.gets.append(request)
        refuse("GetItem")
        item = held(request["Key"])
        return {} if item is None else {"Item": item}

    def update_item(**request: Any) -> Dict[str, Any]:
        store.updates.append(request)
        refuse("UpdateItem")
        conditional = "ConditionExpression" in request
        item = required(request["Key"], "UpdateItem") if conditional else counter(request["Key"])
        renaming = ":name" in request["ExpressionAttributeValues"]
        return rename(request, item) if renaming else advance(request, item)

    def delete_item(**request: Any) -> Dict[str, Any]:
        store.deletes.append(request)
        refuse("DeleteItem")
        conditional = "ConditionExpression" in request
        item = required(request["Key"], "DeleteItem") if conditional else held(request["Key"])
        if item is None:
            return {}
        store.items.remove(item)
        return {"Attributes": item}

    def put_item(**request: Any) -> Dict[str, Any]:
        store.puts.append(request)
        refuse("PutItem")
        item = request["Item"]
        if "ConditionExpression" in request:
            store.items.remove(required({"PK": item["PK"], "SK": item["SK"]}, "PutItem"))
        store.items.append(item)
        return {}

    store.query = query
    store.get_item = get_item
    store.update_item = update_item
    store.delete_item = delete_item
    store.put_item = put_item
    return store




@pytest.fixture(name="endpoint")
def endpoint_fixture(
    load_handler: Callable[..., ModuleType],
    monkeypatch: pytest.MonkeyPatch,
    store: SimpleNamespace,
) -> Callable[[str], ModuleType]:
    def load(stack: str) -> ModuleType:
        handler = load_handler(f"api/endpoints/{stack}")
        monkeypatch.setenv("STORE_TABLE", "store")
        for module in (handler, library):
            monkeypatch.setattr(module, "aws_client", lambda service: {"dynamodb": store}[service])
        return handler
    return load


@pytest.fixture(name="answer")
def answer_fixture(handler: ModuleType) -> Handler:
    def answer(event: Dict[str, Any]) -> Dict[str, Any]:
        return dict(handler.lambda_handler(event, None))
    return answer


@pytest.fixture(name="served")
def served_fixture(answer: Handler) -> Served:
    def served(event: Dict[str, Any]) -> Any:
        return json.loads(answer(event)["body"])
    return served
