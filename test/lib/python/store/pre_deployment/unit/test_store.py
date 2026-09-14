from types import SimpleNamespace
from typing import Any, Dict, List

import pytest

import store
from store import members, partition

COUNTER = {"PK": {"S": "carriers"}, "SK": {"S": "#"}, "next": {"N": "3"}}
LUMEN = {"PK": {"S": "carriers"}, "SK": {"S": "1"}, "name": {"S": "lumen"}}
ZAYO = {"PK": {"S": "carriers"}, "SK": {"S": "2"}, "name": {"S": "zayo"}}


@pytest.fixture(name="dynamodb")
def dynamodb_fixture(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    dynamodb = SimpleNamespace(queries=[], items=[COUNTER, ZAYO, LUMEN])

    def query(**request: Any) -> Dict[str, Any]:
        dynamodb.queries.append(request)
        return {"Items": list(dynamodb.items), "Count": len(dynamodb.items)}

    dynamodb.query = query
    monkeypatch.setattr(store, "aws_client", lambda service: {"dynamodb": dynamodb}[service])
    return dynamodb


def _query(dynamodb: SimpleNamespace) -> Dict[str, Any]:
    queries: List[Dict[str, Any]] = dynamodb.queries
    return queries[0]


@pytest.mark.usefixtures("dynamodb")
def test_a_partition_answers_the_items_the_store_holds() -> None:
    assert partition("the-table", "carriers") == [COUNTER, ZAYO, LUMEN]


def test_a_partition_is_read_from_the_table_it_names(dynamodb: SimpleNamespace) -> None:
    partition("the-table", "carriers")
    assert _query(dynamodb)["TableName"] == "the-table"


def test_a_partition_is_read_by_its_key(dynamodb: SimpleNamespace) -> None:
    partition("the-table", "carriers")
    assert _query(dynamodb)["KeyConditionExpression"] == "PK = :pk"


def test_a_partition_names_its_key_as_a_string(dynamodb: SimpleNamespace) -> None:
    partition("the-table", "carriers")
    assert _query(dynamodb)["ExpressionAttributeValues"] == {":pk": {"S": "carriers"}}


def test_a_prefix_narrows_the_partition_to_the_sort_keys_that_begin_with_it(
    dynamodb: SimpleNamespace
) -> None:
    partition("the-table", "carriers/1", "pops/")
    assert _query(dynamodb)["KeyConditionExpression"] == "PK = :pk AND begins_with(SK, :prefix)"


def test_a_prefix_is_named_as_a_string(dynamodb: SimpleNamespace) -> None:
    partition("the-table", "carriers/1", "pops/")
    assert _query(dynamodb)["ExpressionAttributeValues"] == {
        ":pk": {"S": "carriers/1"}, ":prefix": {"S": "pops/"},
    }


@pytest.mark.usefixtures("dynamodb")
def test_the_members_of_a_collection_leave_out_its_counter() -> None:
    assert members("the-table", "carriers") == [ZAYO, LUMEN]


def test_the_members_are_read_from_the_collection_s_own_partition(
    dynamodb: SimpleNamespace
) -> None:
    members("the-table", "carriers")
    assert _query(dynamodb)["ExpressionAttributeValues"] == {":pk": {"S": "carriers"}}
