from typing import Any, Callable, Dict, Tuple

TABLE_NAME = "api-10ulabs-com-rack-configurations"


def test_the_deployed_api_refuses_a_configuration_without_a_device(
    stage_url: str, post_json: Callable[..., Tuple[int, Dict[str, Any]]]
) -> None:
    status, _ = post_json(f"{stage_url}/rack-configurations", {"configuration": {}})
    assert status == 400


def test_the_preflight_allows_any_origin_through_the_deployed_api(
    stage_url: str, preflight: Callable[[str], Dict[str, str]]
) -> None:
    headers = preflight(f"{stage_url}/rack-configurations")
    assert headers["access-control-allow-origin"] == "*"


def test_an_unknown_hash_answers_404_through_the_deployed_api(
    stage_url: str, get_json: Callable[[str], Tuple[int, Dict[str, Any]]]
) -> None:
    status, _ = get_json(f"{stage_url}/rack-configurations/ZZZZZZZZZ")
    assert status == 404


def test_the_read_preflight_allows_any_origin_through_the_deployed_api(
    stage_url: str, preflight: Callable[[str], Dict[str, str]]
) -> None:
    headers = preflight(f"{stage_url}/rack-configurations/ZZZZZZZZZ")
    assert headers["access-control-allow-origin"] == "*"


def test_the_table_is_provisioned_inside_the_free_allowance(dynamodb_client: Any) -> None:
    table = dynamodb_client.describe_table(TableName=TABLE_NAME)["Table"]
    throughput = table["ProvisionedThroughput"]
    assert (throughput["ReadCapacityUnits"], throughput["WriteCapacityUnits"]) == (2, 2)


def test_the_table_keeps_point_in_time_recovery(dynamodb_client: Any) -> None:
    backups = dynamodb_client.describe_continuous_backups(TableName=TABLE_NAME)
    description = backups["ContinuousBackupsDescription"]["PointInTimeRecoveryDescription"]
    assert description["PointInTimeRecoveryStatus"] == "ENABLED"
