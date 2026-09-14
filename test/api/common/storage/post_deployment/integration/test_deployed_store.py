from typing import Any, Dict


def test_the_store_is_keyed_by_pk_and_sk(store: Dict[str, Any]) -> None:
    keys = [(key["AttributeName"], key["KeyType"]) for key in store["KeySchema"]]
    assert keys == [("PK", "HASH"), ("SK", "RANGE")]


def test_the_store_keys_are_strings(store: Dict[str, Any]) -> None:
    attributes = {attribute["AttributeName"]: attribute["AttributeType"]
                  for attribute in store["AttributeDefinitions"]}
    assert attributes == {"PK": "S", "SK": "S"}


def test_the_store_is_provisioned_inside_the_free_allowance(store: Dict[str, Any]) -> None:
    throughput = store["ProvisionedThroughput"]
    assert (throughput["ReadCapacityUnits"], throughput["WriteCapacityUnits"]) == (15, 15)


def test_the_store_carries_no_index(store: Dict[str, Any]) -> None:
    assert "GlobalSecondaryIndexes" not in store


def test_the_store_is_sealed_with_the_aws_owned_key(store: Dict[str, Any]) -> None:
    assert "SSEDescription" not in store


def test_the_store_keeps_no_point_in_time_recovery(store_backups: Dict[str, Any]) -> None:
    recovery = store_backups["PointInTimeRecoveryDescription"]
    assert recovery["PointInTimeRecoveryStatus"] == "DISABLED"


def test_the_store_denies_every_principal_outside_the_account(
    store_policy: Dict[str, Any]
) -> None:
    statement = store_policy["Statement"][0]
    assert (statement["Effect"], statement["Condition"]["StringNotEquals"]) == (
        "Deny", {"aws:PrincipalAccount": "781581267945"}
    )


def test_the_store_policy_holds_that_one_statement(store_policy: Dict[str, Any]) -> None:
    assert len(store_policy["Statement"]) == 1
