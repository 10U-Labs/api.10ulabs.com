import json
from pathlib import Path
from types import ModuleType
from typing import Any, Dict

import pytest

BROWSED = {"path": "/nothing", "headers": {"Accept": "text/html,application/xhtml+xml"}}
ASKED_FOR_JSON = {"path": "/nothing", "headers": {"accept": "application/json"}}


def _answer(catchall_handler: ModuleType, event: Dict[str, Any]) -> Dict[str, Any]:
    return dict(catchall_handler.lambda_handler(event, None))


@pytest.fixture(name="page")
def page_fixture(repo_root: Path) -> str:
    return (repo_root / "src" / "www" / "404.html").read_text(encoding="utf-8")


@pytest.fixture(name="browsed")
def browsed_fixture(
    catchall_handler: ModuleType, page: str, monkeypatch: pytest.MonkeyPatch
) -> Dict[str, Any]:
    monkeypatch.setenv("NOT_FOUND_PAGE", page)
    return _answer(catchall_handler, BROWSED)


def test_catchall_answers_404(catchall_handler: ModuleType) -> None:
    assert _answer(catchall_handler, {"path": "/nothing"})["statusCode"] == 404


def test_catchall_answers_json(catchall_handler: ModuleType) -> None:
    response = _answer(catchall_handler, {"path": "/nothing"})
    assert response["headers"]["Content-Type"] == "application/json"


def test_catchall_answers_json_to_a_client_that_asks_for_it(catchall_handler: ModuleType) -> None:
    response = _answer(catchall_handler, ASKED_FOR_JSON)
    assert response["headers"]["Content-Type"] == "application/json"


def test_catchall_names_the_path_it_refused(catchall_handler: ModuleType) -> None:
    response = _answer(catchall_handler, {"path": "/nothing", "httpMethod": "PUT"})
    assert json.loads(response["body"])["path"] == "/nothing"


def test_catchall_names_the_error(catchall_handler: ModuleType) -> None:
    response = _answer(catchall_handler, {})
    assert json.loads(response["body"])["error"] == "Not Found"


def test_catchall_answers_a_browser_404(browsed: Dict[str, Any]) -> None:
    assert browsed["statusCode"] == 404


def test_catchall_answers_a_browser_html(browsed: Dict[str, Any]) -> None:
    assert browsed["headers"]["Content-Type"] == "text/html"


def test_catchall_answers_a_browser_the_not_found_page(
    browsed: Dict[str, Any], page: str
) -> None:
    assert browsed["body"] == page
