from types import ModuleType, SimpleNamespace
from typing import Any, Dict


def _run(exporter: ModuleType) -> Dict[str, Any]:
    return dict(exporter.lambda_handler({}, None))


def test_the_export_is_of_the_events_table(exporter: ModuleType, exports: SimpleNamespace) -> None:
    _run(exporter)
    assert exports.started[0]["TableArn"] == "arn:aws:dynamodb:us-east-2:1:table/events"


def test_the_export_lands_under_the_prefix_by_time(
    exporter: ModuleType, exports: SimpleNamespace
) -> None:
    _run(exporter)
    assert exports.started[0]["S3Prefix"].startswith("exports/events/20")


def test_the_export_is_dynamodb_json(exporter: ModuleType, exports: SimpleNamespace) -> None:
    _run(exporter)
    assert exports.started[0]["ExportFormat"] == "DYNAMODB_JSON"


def test_the_answer_names_the_export(exporter: ModuleType) -> None:
    assert _run(exporter)["body"]["export_arn"].endswith("export/1")


def test_the_answer_names_the_path(exporter: ModuleType) -> None:
    assert _run(exporter)["body"]["s3_path"].startswith("s3://analytics/exports/events/")
