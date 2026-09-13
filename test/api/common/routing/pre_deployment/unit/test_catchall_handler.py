import json
from types import ModuleType
from typing import Any, Dict


def _answer(catchall_handler: ModuleType, event: Dict[str, Any]) -> Dict[str, Any]:
    return dict(catchall_handler.lambda_handler(event, None))


def test_catchall_answers_404(catchall_handler: ModuleType) -> None:
    assert _answer(catchall_handler, {"path": "/nothing"})["statusCode"] == 404


def test_catchall_answers_json(catchall_handler: ModuleType) -> None:
    response = _answer(catchall_handler, {"path": "/nothing"})
    assert response["headers"]["Content-Type"] == "application/json"


def test_catchall_names_the_path_it_refused(catchall_handler: ModuleType) -> None:
    response = _answer(catchall_handler, {"path": "/nothing", "httpMethod": "PUT"})
    assert json.loads(response["body"])["path"] == "/nothing"


def test_catchall_names_the_error(catchall_handler: ModuleType) -> None:
    response = _answer(catchall_handler, {})
    assert json.loads(response["body"])["error"] == "Not Found"
