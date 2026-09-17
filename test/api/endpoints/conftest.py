import json
import re
from types import ModuleType, SimpleNamespace
from typing import Any, Callable, Dict, List, Optional

import pytest
from botocore.exceptions import ClientError

import cache as caching
import store as library
from lambda_http import Handler

Served = Callable[[Dict[str, Any]], Any]


@pytest.fixture(name="store")
def store_fixture() -> SimpleNamespace:
    store = SimpleNamespace(
        items=[], failing=False, queries=[], gets=[], updates=[], deletes=[], puts=[], batches=[]
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

    def assign(request: Dict[str, Any], item: Dict[str, Any]) -> Dict[str, Any]:
        names = request["ExpressionAttributeNames"]
        values = request["ExpressionAttributeValues"]
        for clause in re.split(r", (?=#)", request["UpdateExpression"].removeprefix("SET ")):
            target, _, expression = clause.partition(" = ")
            if "+" in expression:
                held = int(item.get(names[target], {"N": "1"})["N"])
                item[names[target]] = {"N": str(held + 1)}
            else:
                item[names[target]] = values[expression]
        return {"Attributes": dict(item)}

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
        return assign(request, item)

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

    def batch_write_item(**request: Any) -> Dict[str, Any]:
        store.batches.append(request)
        refuse("BatchWriteItem")
        for one in [one for listed in request["RequestItems"].values() for one in listed]:
            item = held(one["DeleteRequest"]["Key"])
            if item is not None:
                store.items.remove(item)
        return {"UnprocessedItems": {}}

    store.query = query
    store.get_item = get_item
    store.update_item = update_item
    store.delete_item = delete_item
    store.put_item = put_item
    store.batch_write_item = batch_write_item
    return store


@pytest.fixture(name="distribution")
def distribution_fixture() -> SimpleNamespace:
    distribution = SimpleNamespace(invalidated=[], failing=False)

    def create_invalidation(**request: Any) -> Dict[str, Any]:
        if distribution.failing:
            raise ClientError({"Error": {"Code": "AccessDenied"}}, "CreateInvalidation")
        distribution.invalidated.append(request["InvalidationBatch"]["Paths"]["Items"])
        return {}

    distribution.create_invalidation = create_invalidation
    return distribution


@pytest.fixture(name="invoker")
def invoker_fixture() -> SimpleNamespace:
    invoker = SimpleNamespace(invocations=[])

    def invoke(**request: Any) -> Dict[str, Any]:
        invoker.invocations.append(request)
        return {"StatusCode": 202}

    invoker.invoke = invoke
    return invoker


@pytest.fixture
def endpoint(
    load_handler: Callable[..., ModuleType],
    monkeypatch: pytest.MonkeyPatch,
    store: SimpleNamespace,
    invoker: SimpleNamespace,
    distribution: SimpleNamespace,
) -> Callable[..., ModuleType]:
    def load(stack: str, handler_dir: str = "lambda") -> ModuleType:
        handler = load_handler(f"api/endpoints/{stack}", handler_dir)
        monkeypatch.setenv("STORE_TABLE", "store")
        monkeypatch.setenv("DISTRIBUTION_ID", "distribution")
        clients = {"dynamodb": store, "lambda": invoker, "cloudfront": distribution}
        for module in (handler, library, caching):
            monkeypatch.setattr(
                module, "aws_client", lambda service: clients[service], raising=False
            )
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
