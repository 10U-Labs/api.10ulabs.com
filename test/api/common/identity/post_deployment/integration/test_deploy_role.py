from typing import Any, Dict

SUBJECT = "repo:10U-Labs@240548037/api.10ulabs.com@1368777392:ref:refs/heads/main"


def test_deploy_role_trusts_this_repository_on_main_alone(
    deploy_role_trust: Dict[str, Any]
) -> None:
    condition = deploy_role_trust["Statement"][0]["Condition"]["StringEquals"]
    assert condition["token.actions.githubusercontent.com:sub"] == SUBJECT


def test_deploy_role_trust_holds_one_statement(deploy_role_trust: Dict[str, Any]) -> None:
    assert len(deploy_role_trust["Statement"]) == 1


def test_deploy_role_carries_no_managed_policy(attached_policies: list[Any]) -> None:
    assert attached_policies == []


def test_deploy_role_holds_the_five_declared_policies(inline_policy_names: list[str]) -> None:
    assert inline_policy_names == ["Functions", "Roles", "Routing", "Self", "State"]
