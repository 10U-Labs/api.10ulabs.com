import os
import re

STATE_PREFIX = '"${local.state_bucket}/api.10ulabs.com/*"'
ON_EVERY_RESOURCE = r'sid\s*=\s*"(\w+)"\s*actions\s*=\s*\[[^\]]*\]\s*resources = \["\*"\]'
ATTACH_STATEMENT = (
    r'"iam:AttachRolePolicy"\]\s*resources = \[local\.backup_roles\]\s*condition \{\s*'
    r'test\s*=\s*"ForAnyValue:StringEquals"\s*variable = ("iam:PolicyARN")'
)
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


def _statements_on_every_resource(iam_tf: str) -> set[str]:
    return set(re.findall(ON_EVERY_RESOURCE, iam_tf))


def test_only_the_actions_that_take_no_resource_are_granted_on_every_resource(iam_tf: str) -> None:
    assert _statements_on_every_resource(iam_tf) == {
        "ListEveryFunctionToFindALeftover",
        "DescribeParametersToReadATier",
        "ReadIdentityVerificationOnTheArnSesEvaluatesItAgainst",
        "MountTheVaultCapsuleThatTakesNoResource",
        "ListAndRequestWhatTakesNoResource",
    }


def test_every_statement_on_every_resource_is_counted(iam_tf: str) -> None:
    assert iam_tf.count('resources = ["*"]') == len(_statements_on_every_resource(iam_tf))


def test_the_solver_layer_is_declared_under_the_product_prefix_alone(iam_tf: str) -> None:
    assert re.search(
        r'sid\s*=\s*"DeclareTheSolverLayer"\s*actions\s*=\s*\[[^\]]*"lambda:PublishLayerVersion"'
        r'[^\]]*\]\s*resources = \[local\.layers\]',
        iam_tf,
    )


def test_layers_are_named_under_the_product_with_every_version(iam_tf: str) -> None:
    arn = "arn:aws:lambda:${local.region}:${local.account}:layer:${local.product}-*"
    assert f'layers       = "{arn}"' in iam_tf


def test_the_handlers_take_a_failure_destination(iam_tf: str) -> None:
    assert '"lambda:PutFunctionEventInvokeConfig",' in iam_tf


def test_state_grant_stops_at_this_repository_prefix(iam_tf: str) -> None:
    assert STATE_PREFIX in iam_tf


def test_a_managed_policy_attaches_only_under_a_policy_arn_condition(iam_tf: str) -> None:
    assert re.findall(ATTACH_STATEMENT, iam_tf) == ['"iam:PolicyARN"']


def test_the_role_may_rewrite_its_own_description(iam_tf: str) -> None:
    assert '"iam:UpdateRoleDescription"' in iam_tf


def test_the_role_may_read_the_managed_origin_request_policies(iam_tf: str) -> None:
    assert '"cloudfront:GetOriginRequestPolicy",' in iam_tf
