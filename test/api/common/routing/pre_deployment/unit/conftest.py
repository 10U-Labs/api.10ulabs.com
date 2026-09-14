import io
import json
from email.message import Message
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any, Callable, Dict

import pytest

GOOGLE_CLIENT_ID = "client.apps.googleusercontent.com"
API_KEY = "the-workflows-key"
AUTHORIZED = "someone@10ulabs.com, Another@10ulabs.com"


@pytest.fixture(scope="module")
def routing_dir(repo_root: Path) -> Path:
    return repo_root / "src" / "api" / "common" / "routing"


@pytest.fixture(scope="module")
def openapi(repo_root: Path) -> Dict[str, Any]:
    path = repo_root / "src" / "www" / "api" / "openapi.json"
    return dict(json.loads(path.read_text(encoding="utf-8")))


@pytest.fixture(scope="module")
def catchall_handler(load_handler: Callable[..., ModuleType]) -> ModuleType:
    return load_handler("api/common/routing", "lambda/catchall")


@pytest.fixture(name="parameters")
def parameters_fixture() -> SimpleNamespace:
    parameters = SimpleNamespace(read=[], values={
        "/api.10ulabs.com/api-key": API_KEY,
        "/api.10ulabs.com/authorized-accounts": AUTHORIZED,
    })

    def get_parameter(**request: Any) -> Dict[str, Any]:
        parameters.read.append(request["Name"])
        return {"Parameter": {"Value": parameters.values[request["Name"]]}}

    parameters.get_parameter = get_parameter
    return parameters


@pytest.fixture(name="google")
def google_fixture() -> SimpleNamespace:
    return SimpleNamespace(asked=[], claims={
        "iss": "https://accounts.google.com",
        "aud": GOOGLE_CLIENT_ID,
        "hd": "10ulabs.com",
        "email": "someone@10ulabs.com",
        "email_verified": "true",
    }, refusing=False)


@pytest.fixture
def authorizer(
    load_handler: Callable[..., ModuleType],
    monkeypatch: pytest.MonkeyPatch,
    parameters: SimpleNamespace,
    google: SimpleNamespace,
) -> ModuleType:
    handler = load_handler("api/common/routing", "lambda/authorizer")
    monkeypatch.setenv("GOOGLE_CLIENT_ID", GOOGLE_CLIENT_ID)
    monkeypatch.setenv("HOSTED_DOMAIN", "10ulabs.com")
    monkeypatch.setenv("API_KEY_PARAMETER", "/api.10ulabs.com/api-key")
    monkeypatch.setenv("AUTHORIZED_ACCOUNTS_PARAMETER", "/api.10ulabs.com/authorized-accounts")
    monkeypatch.setattr(handler, "aws_client", lambda service: {"ssm": parameters}[service])

    def urlopen(request: Any, timeout: float) -> Any:
        google.asked.append((request.full_url, timeout))
        if google.refusing:
            raise handler.urllib.error.HTTPError(
                request.full_url, 400, "Bad Request", Message(), None
            )
        return io.BytesIO(json.dumps(google.claims).encode("utf-8"))

    monkeypatch.setattr(handler.urllib.request, "urlopen", urlopen)
    return handler
