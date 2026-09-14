import json
from typing import Any, Dict

import pytest

TABLE_NAME = "api-10ulabs-com-store"


@pytest.fixture(scope="module", name="store")
def store_fixture(dynamodb_client: Any) -> Dict[str, Any]:
    return dict(dynamodb_client.describe_table(TableName=TABLE_NAME)["Table"])


@pytest.fixture(scope="module")
def store_policy(dynamodb_client: Any, store: Dict[str, Any]) -> Dict[str, Any]:
    response = dynamodb_client.get_resource_policy(ResourceArn=store["TableArn"])
    return dict(json.loads(response["Policy"]))


@pytest.fixture(scope="module")
def store_backups(dynamodb_client: Any) -> Dict[str, Any]:
    response = dynamodb_client.describe_continuous_backups(TableName=TABLE_NAME)
    return dict(response["ContinuousBackupsDescription"])
