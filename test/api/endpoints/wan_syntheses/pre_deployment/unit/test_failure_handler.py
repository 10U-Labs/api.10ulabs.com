from importlib import import_module
from types import ModuleType, SimpleNamespace
from typing import Any, Callable, Dict, List

import pytest

from store import plain


@pytest.fixture(name="failure_handler")
def failure_handler_fixture(
    endpoint: Callable[..., ModuleType], store: SimpleNamespace, run: List[Dict[str, Any]]
) -> ModuleType:
    endpoint("wan_syntheses", "synthesizer")
    store.items.extend(run)
    return import_module("synthesizer.failure_handler")


def _killed(condition: str = "") -> Dict[str, Any]:
    context = {"condition": condition} if condition else {}
    return {"requestPayload": {"synthesis": 1}, "requestContext": context}


def _assigned(store: SimpleNamespace) -> Dict[str, Any]:
    update = store.updates[0]
    names = update["ExpressionAttributeNames"]
    return {
        names[f"#{index}"]: plain(value)
        for index, value in enumerate(update["ExpressionAttributeValues"].values())
    }


def test_a_killed_run_answers_timeout(failure_handler: ModuleType) -> None:
    assert failure_handler.lambda_handler(_killed(), None) == {"status": "timeout", "synthesis": 1}


def test_a_killed_run_is_marked_timeout(
    failure_handler: ModuleType, store: SimpleNamespace
) -> None:
    failure_handler.lambda_handler(_killed(), None)
    assert _assigned(store)["status"] == "timeout"


def test_the_status_is_assigned_to_the_run_s_record(
    failure_handler: ModuleType, store: SimpleNamespace
) -> None:
    failure_handler.lambda_handler(_killed(), None)
    assert store.updates[0]["Key"] == {"PK": {"S": "wan-syntheses"}, "SK": {"S": "1"}}


def test_a_run_killed_without_a_condition_is_reasoned_as_terminated(
    failure_handler: ModuleType, store: SimpleNamespace
) -> None:
    failure_handler.lambda_handler(_killed(), None)
    assert _assigned(store)["reason"] == (
        "synthesizer terminated before completing (timed out or crashed)"
    )


def test_a_run_killed_under_a_condition_is_reasoned_with_it(
    failure_handler: ModuleType, store: SimpleNamespace
) -> None:
    failure_handler.lambda_handler(_killed("RetriesExhausted"), None)
    assert _assigned(store)["reason"] == "synthesizer invocation failed (RetriesExhausted)"


def test_a_killed_run_is_invalidated(
    failure_handler: ModuleType, distribution: SimpleNamespace
) -> None:
    failure_handler.lambda_handler(_killed(), None)
    assert distribution.invalidated == [["/wan-syntheses/1"]]
