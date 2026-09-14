from typing import Any, Callable, Dict, Tuple

TABLE_NAME = "api-10ulabs-com-session-events"
BUCKET_NAME = "api-10ulabs-com-sessions-analytics"
SCHEDULE_NAME = "api-10ulabs-com-sessions-export"
EVENTS = {
    "device_id": "post-deployment-tests",
    "events": [{"event_type": "test", "timestamp": "2026-09-13T00:00:00Z"}],
}


def test_events_are_recorded_through_the_deployed_api(
    stage_url: str, post_json: Callable[..., Tuple[int, Dict[str, Any]]]
) -> None:
    status, _ = post_json(f"{stage_url}/sessions/post-deployment-tests/events", EVENTS)
    assert status == 200


def test_the_deployed_api_counts_the_events(
    stage_url: str, post_json: Callable[..., Tuple[int, Dict[str, Any]]]
) -> None:
    _, body = post_json(f"{stage_url}/sessions/post-deployment-tests/events", EVENTS)
    assert body["events_saved"] == 1


def test_the_deployed_api_refuses_events_without_a_device(
    stage_url: str, post_json: Callable[..., Tuple[int, Dict[str, Any]]]
) -> None:
    status, _ = post_json(f"{stage_url}/sessions/post-deployment-tests/events", {"events": []})
    assert status == 400


def test_the_preflight_allows_any_origin_through_the_deployed_api(
    stage_url: str, preflight: Callable[[str], Dict[str, str]]
) -> None:
    headers = preflight(f"{stage_url}/sessions/post-deployment-tests/events")
    assert headers["access-control-allow-origin"] == "*"


def test_the_table_and_its_indexes_are_provisioned_inside_the_free_allowance(
    dynamodb_client: Any
) -> None:
    table = dynamodb_client.describe_table(TableName=TABLE_NAME)["Table"]
    throughputs = [table["ProvisionedThroughput"]] + [
        index["ProvisionedThroughput"] for index in table["GlobalSecondaryIndexes"]
    ]
    assert [(t["ReadCapacityUnits"], t["WriteCapacityUnits"]) for t in throughputs] == [(2, 2)] * 3


def test_the_analytics_bucket_blocks_public_access(s3_client: Any) -> None:
    block = s3_client.get_public_access_block(Bucket=BUCKET_NAME)["PublicAccessBlockConfiguration"]
    assert all(block.values())


def test_the_export_runs_daily(scheduler_client: Any) -> None:
    schedule = scheduler_client.get_schedule(Name=SCHEDULE_NAME)
    assert schedule["ScheduleExpression"] == "cron(0 5 * * ? *)"
