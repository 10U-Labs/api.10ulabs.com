import json
from types import ModuleType, SimpleNamespace
from typing import Any, Dict

CARRIERS = "/carriers"


def get(resource: str = CARRIERS) -> Dict[str, Any]:
    return {"resource": resource, "httpMethod": "GET"}


def post(body: Any, resource: str = CARRIERS) -> Dict[str, Any]:
    return {"resource": resource, "httpMethod": "POST", "body": json.dumps(body)}


def answer(carriers_handler: ModuleType, event: Dict[str, Any]) -> Dict[str, Any]:
    return dict(carriers_handler.lambda_handler(event, None))


def served(carriers_handler: ModuleType, event: Dict[str, Any]) -> Any:
    return json.loads(answer(carriers_handler, event)["body"])


def stored(store: SimpleNamespace, carrier: str) -> Dict[str, Any]:
    return next(item for item in store.items if item["SK"] == {"S": carrier})
