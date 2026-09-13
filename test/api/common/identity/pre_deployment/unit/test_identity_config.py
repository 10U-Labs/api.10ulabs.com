import os
import re

STATE_PREFIX = '"${local.state_bucket}/api.10ulabs.com/*"'
SUB_CONDITION = r'test\s*=\s*"StringEquals"\s*variable\s*=\s*"\$\{local\.issuer\}:sub"'


def _declared_policies(iam_tf: str) -> set[str]:
    return set(re.findall(r'^resource "aws_iam_role_policy" "(\w+)"', iam_tf, re.MULTILINE))


def _exclusive_policies(main_tf: str) -> set[str]:
    return set(re.findall(r'aws_iam_role_policy\.(\w+)\.name', main_tf))


def test_trust_names_this_repository_by_its_immutable_ids(main_tf: str) -> None:
    owner = os.environ["GITHUB_REPOSITORY_OWNER_ID"]
    repository = os.environ["GITHUB_REPOSITORY_ID"]
    assert f'repository = "10U-Labs@{owner}/api.10ulabs.com@{repository}"' in main_tf


def test_trust_admits_main_alone(main_tf: str) -> None:
    assert 'ref        = "refs/heads/main"' in main_tf


def test_trust_matches_the_subject_exactly(main_tf: str) -> None:
    assert re.search(SUB_CONDITION, main_tf)


def test_role_carries_no_managed_policy(main_tf: str) -> None:
    assert "policy_arns = []" in main_tf


def test_exclusive_policies_name_every_declared_policy(main_tf: str, iam_tf: str) -> None:
    assert _exclusive_policies(main_tf) == _declared_policies(iam_tf)


def test_only_listing_functions_is_granted_on_every_resource(iam_tf: str) -> None:
    assert iam_tf.count('resources = ["*"]') == 1


def test_state_grant_stops_at_this_repository_prefix(iam_tf: str) -> None:
    assert STATE_PREFIX in iam_tf


def test_no_stack_may_attach_a_managed_policy_to_a_handler_role(iam_tf: str) -> None:
    assert '"iam:AttachRolePolicy"' not in iam_tf
