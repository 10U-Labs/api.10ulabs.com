from typing import Any, Callable, Dict, Tuple

FUNCTION_NAME = "api-10ulabs-com-contact"
PARAMETER_NAME = "/api-10ulabs-com/contact/recaptcha-secret-key"
TEST_MODE = {"x-test-mode": "true"}
SUBMISSION = {
    "name": "Post-deployment test",
    "email": "test@example.com",
    "message": "Sent by the post-deployment integration tests in test mode.",
    "recaptcha_token": "a-token",
}


def test_a_test_mode_submission_answers_200_through_the_deployed_api(
    stage_url: str, post_json: Callable[..., Tuple[int, Dict[str, Any]]]
) -> None:
    status, _ = post_json(f"{stage_url}/contact-submissions", SUBMISSION, TEST_MODE)
    assert status == 200


def test_a_test_mode_submission_is_not_sent_through_the_deployed_api(
    stage_url: str, post_json: Callable[..., Tuple[int, Dict[str, Any]]]
) -> None:
    _, body = post_json(f"{stage_url}/contact-submissions", SUBMISSION, TEST_MODE)
    assert body["test_mode"] is True


def test_a_submission_missing_its_name_answers_400_through_the_deployed_api(
    stage_url: str, post_json: Callable[..., Tuple[int, Dict[str, Any]]]
) -> None:
    status, _ = post_json(f"{stage_url}/contact-submissions", {**SUBMISSION, "name": ""})
    assert status == 400


def test_the_preflight_allows_any_origin_through_the_deployed_api(
    stage_url: str, preflight: Callable[[str], Dict[str, str]]
) -> None:
    headers = preflight(f"{stage_url}/contact-submissions")
    assert headers["access-control-allow-origin"] == "*"


def test_contact_function_reads_its_secret_from_the_products_parameter(lambda_client: Any) -> None:
    function = lambda_client.get_function(FunctionName=FUNCTION_NAME)
    environment = function["Configuration"]["Environment"]["Variables"]
    assert environment["RECAPTCHA_SECRET_PARAMETER_NAME"] == PARAMETER_NAME
