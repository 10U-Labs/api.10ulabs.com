import json
from types import ModuleType, SimpleNamespace
from typing import Any, Dict

import pytest

CONTACT = "/contact-submissions"
TEST_MODE = {"x-test-mode": "true"}


def _post(body: Any, headers: Dict[str, str] | None = None) -> Dict[str, Any]:
    raw = body if isinstance(body, str) else json.dumps(body)
    return {"resource": CONTACT, "httpMethod": "POST", "body": raw, "headers": headers or {}}


def _raise_os_error(*_: Any, **__: Any) -> None:
    raise OSError("no route to the verifier")


def _answer(contact_handler: ModuleType, event: Dict[str, Any]) -> Dict[str, Any]:
    return dict(contact_handler.lambda_handler(event, None))


def _body(contact_handler: ModuleType, event: Dict[str, Any]) -> Dict[str, Any]:
    return dict(json.loads(_answer(contact_handler, event)["body"]))


def test_a_valid_submission_is_sent(
    contact_handler: ModuleType, submission: Dict[str, str]
) -> None:
    assert _answer(contact_handler, _post(submission))["statusCode"] == 200


def test_a_sent_submission_says_so(contact_handler: ModuleType, submission: Dict[str, str]) -> None:
    assert _body(contact_handler, _post(submission)) == {
        "success": True, "message": "Message sent successfully"
    }


def test_the_email_goes_to_the_contact_address(
    contact_handler: ModuleType, submission: Dict[str, str], ses: SimpleNamespace
) -> None:
    _answer(contact_handler, _post(submission))
    assert ses.sent[0]["Destination"] == {"ToAddresses": ["contact@example.com"]}


def test_the_email_replies_to_the_sender(
    contact_handler: ModuleType, submission: Dict[str, str], ses: SimpleNamespace
) -> None:
    _answer(contact_handler, _post(submission))
    assert ses.sent[0]["ReplyToAddresses"] == ["ada@example.com"]


def test_the_email_carries_the_message(
    contact_handler: ModuleType, submission: Dict[str, str], ses: SimpleNamespace
) -> None:
    _answer(contact_handler, _post(submission))
    assert "Hello from the contact form." in ses.sent[0]["Message"]["Body"]["Text"]["Data"]


def test_the_secret_is_read_from_the_named_parameter(
    contact_handler: ModuleType, submission: Dict[str, str], ssm: SimpleNamespace
) -> None:
    _answer(contact_handler, _post(submission))
    assert ssm.read == ["/example/recaptcha"]


def test_every_answer_allows_any_origin(contact_handler: ModuleType) -> None:
    response = _answer(contact_handler, {"resource": "/other", "httpMethod": "GET"})
    assert response["headers"]["Access-Control-Allow-Origin"] == "*"


def test_another_resource_answers_404(contact_handler: ModuleType) -> None:
    response = _answer(contact_handler, {"resource": "/other", "httpMethod": "GET"})
    assert response["statusCode"] == 404


def test_test_mode_answers_without_sending(
    contact_handler: ModuleType, submission: Dict[str, str], ses: SimpleNamespace
) -> None:
    _answer(contact_handler, _post(submission, {"X-Test-Mode": "true"}))
    assert ses.sent == []


def test_test_mode_says_it_did_not_submit(
    contact_handler: ModuleType, submission: Dict[str, str]
) -> None:
    body = _body(contact_handler, _post(submission, TEST_MODE))
    assert body["test_mode"] is True


def test_test_mode_still_validates(
    contact_handler: ModuleType, submission: Dict[str, str]
) -> None:
    event = _post({**submission, "email": "not-an-address"}, TEST_MODE)
    assert _answer(contact_handler, event)["statusCode"] == 400


@pytest.mark.parametrize("field", ["name", "email", "message", "recaptcha_token"])
def test_a_missing_field_is_named(
    contact_handler: ModuleType, submission: Dict[str, str], field: str
) -> None:
    body = _body(contact_handler, _post({**submission, field: "  "}))
    assert body["error"] == f"Missing required field: {field}"


@pytest.mark.parametrize("field, limit", [("name", 100), ("email", 255), ("message", 1000)])
def test_a_field_over_its_limit_is_refused(
    contact_handler: ModuleType, submission: Dict[str, str], field: str, limit: int
) -> None:
    body = _body(contact_handler, _post({**submission, field: "x" * (limit + 1)}))
    assert body["error"] == f"{field.capitalize()} must be less than {limit} characters"


def test_an_invalid_email_is_refused(
    contact_handler: ModuleType, submission: Dict[str, str]
) -> None:
    body = _body(contact_handler, _post({**submission, "email": "ada-at-example"}))
    assert body["error"] == "Invalid email address"


def test_a_body_that_is_not_json_is_refused(contact_handler: ModuleType) -> None:
    assert _body(contact_handler, _post("not json"))["error"] == "Invalid JSON"


def test_a_body_that_is_not_an_object_is_refused(contact_handler: ModuleType) -> None:
    assert _body(contact_handler, _post([1, 2]))["error"] == "Invalid JSON"


@pytest.mark.parametrize(
    "recaptcha", [{"success": False}, {"success": True, "score": 0.1}], indirect=True
)
def test_a_failed_recaptcha_is_refused(
    contact_handler: ModuleType, submission: Dict[str, str]
) -> None:
    body = _body(contact_handler, _post(submission))
    assert body["error"] == "reCAPTCHA verification failed"


def test_an_unreachable_verifier_answers_400(
    contact_handler: ModuleType, submission: Dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(contact_handler, "urlopen", _raise_os_error)
    assert _answer(contact_handler, _post(submission))["statusCode"] == 400


def test_a_refused_email_answers_500(
    contact_handler: ModuleType, submission: Dict[str, str], ses: SimpleNamespace
) -> None:
    ses.failing = True
    assert _body(contact_handler, _post(submission))["error"] == "Failed to send message"
