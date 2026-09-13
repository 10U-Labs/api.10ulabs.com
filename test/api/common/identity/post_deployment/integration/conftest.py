from typing import Any, Dict

import pytest

ROLE_NAME = "TenULabsApiRole"


@pytest.fixture(scope="module")
def deploy_role_trust(iam_client: Any) -> Dict[str, Any]:
    response = iam_client.get_role(RoleName=ROLE_NAME)
    return dict(response["Role"]["AssumeRolePolicyDocument"])


@pytest.fixture(scope="module")
def attached_policies(iam_client: Any) -> list[Any]:
    return list(iam_client.list_attached_role_policies(RoleName=ROLE_NAME)["AttachedPolicies"])


@pytest.fixture(scope="module")
def inline_policy_names(iam_client: Any) -> list[str]:
    return sorted(iam_client.list_role_policies(RoleName=ROLE_NAME)["PolicyNames"])
