import io
import json
from types import ModuleType, SimpleNamespace
from typing import Any, Callable, Dict

import pytest
from botocore.exceptions import ClientError


@pytest.fixture(name="ses")
def ses_fixture() -> SimpleNamespace:
    ses = SimpleNamespace(sent=[], failing=False)

    def send_email(**message: Any) -> None:
        if ses.failing:
            raise ClientError({"Error": {"Code": "MessageRejected", "Message": "no"}}, "SendEmail")
        ses.sent.append(message)

    ses.send_email = send_email
    return ses


@pytest.fixture(name="ssm")
def ssm_fixture() -> SimpleNamespace:
    ssm = SimpleNamespace(secret="the-secret", read=[])

    def get_parameter(**request: Any) -> Dict[str, Any]:
        ssm.read.append(request["Name"])
        return {"Parameter": {"Value": ssm.secret}}

    ssm.get_parameter = get_parameter
    return ssm


@pytest.fixture(name="recaptcha")
def recaptcha_fixture(request: pytest.FixtureRequest) -> Dict[str, Any]:
    return dict(getattr(request, "param", {"success": True, "score": 0.9}))


@pytest.fixture
def contact_handler(
    load_handler: Callable[[str], ModuleType],
    monkeypatch: pytest.MonkeyPatch,
    ssm: SimpleNamespace,
    ses: SimpleNamespace,
    recaptcha: Dict[str, Any],
) -> ModuleType:
    handler = load_handler("api/endpoints/contact_submissions")
    clients = {"ssm": ssm, "ses": ses}
    monkeypatch.setenv("CONTACT_EMAIL", "contact@example.com")
    monkeypatch.setenv("RECAPTCHA_SECRET_PARAMETER_NAME", "/example/recaptcha")
    monkeypatch.setattr(handler, "aws_client", lambda service: clients[service])
    monkeypatch.setattr(
        handler, "urlopen", lambda *_, **__: io.BytesIO(json.dumps(recaptcha).encode("utf-8"))
    )
    return handler


@pytest.fixture
def submission() -> Dict[str, str]:
    return {
        "name": "Ada Lovelace",
        "email": "ada@example.com",
        "message": "Hello from the contact form.",
        "recaptcha_token": "a-token",
    }
