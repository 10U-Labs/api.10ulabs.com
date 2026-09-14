from types import ModuleType, SimpleNamespace
from typing import Any, Callable, Dict, List

import pytest
from botocore.exceptions import ClientError


@pytest.fixture(name="store")
def store_fixture() -> SimpleNamespace:
    store = SimpleNamespace(items=[], failing=False, queries=[])

    def query(**request: Any) -> Dict[str, Any]:
        store.queries.append(request)
        if store.failing:
            raise ClientError({"Error": {"Code": "InternalServerError"}}, "Query")
        partition = request["ExpressionAttributeValues"][":pk"]["S"]
        found: List[Dict[str, Any]] = [item for item in store.items if item["PK"]["S"] == partition]
        return {"Items": found, "Count": len(found)}

    store.query = query
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
