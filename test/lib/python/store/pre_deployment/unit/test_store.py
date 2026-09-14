from types import SimpleNamespace
from typing import Any, Dict, List

import pytest
from botocore.exceptions import ClientError

import store
from store import advance, conditional, member, members, next_id, partition, put

COUNTER = {"PK": {"S": "carriers"}, "SK": {"S": "#"}, "next": {"N": "3"}}
LUMEN = {"PK": {"S": "carriers"}, "SK": {"S": "1"}, "name": {"S": "lumen"}}
ZAYO = {"PK": {"S": "carriers"}, "SK": {"S": "2"}, "name": {"S": "zayo"}}


@pytest.fixture(name="dynamodb")
def dynamodb_fixture(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    dynamodb = SimpleNamespace(
        queries=[], gets=[], updates=[], puts=[], items=[COUNTER, ZAYO, LUMEN]
    )

    def query(**request: Any) -> Dict[str, Any]:
        dynamodb.queries.append(request)
        return {"Items": list(dynamodb.items), "Count": len(dynamodb.items)}

    def get_item(**request: Any) -> Dict[str, Any]:
        dynamodb.gets.append(request)
        found = [item for item in dynamodb.items if item["SK"] == request["Key"]["SK"]]
        return {"Item": found[0]} if found else {}

    def update_item(**request: Any) -> Dict[str, Any]:
        dynamodb.updates.append(request)
        field = request["ExpressionAttributeNames"]["#next"]
        return {"Attributes": {field: {"N": "7"}}}

    def put_item(**request: Any) -> Dict[str, Any]:
        dynamodb.puts.append(request)
        return {}

    dynamodb.query = query
    dynamodb.get_item = get_item
    dynamodb.update_item = update_item
    dynamodb.put_item = put_item
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


@pytest.mark.usefixtures("dynamodb")
def test_a_member_answers_the_item_the_store_holds() -> None:
    assert member("the-table", "carriers", "2") == ZAYO


@pytest.mark.usefixtures("dynamodb")
def test_a_member_the_store_does_not_hold_answers_none() -> None:
    assert member("the-table", "carriers", "3") is None


def test_a_member_is_read_from_the_table_it_names(dynamodb: SimpleNamespace) -> None:
    member("the-table", "carriers", "2")
    assert dynamodb.gets[0]["TableName"] == "the-table"


def test_a_member_is_read_by_its_collection_and_its_id(dynamodb: SimpleNamespace) -> None:
    member("the-table", "carriers", "2")
    assert dynamodb.gets[0]["Key"] == {"PK": {"S": "carriers"}, "SK": {"S": "2"}}


KEY = {"PK": {"S": "carriers"}, "SK": {"S": "1"}}


@pytest.mark.usefixtures("dynamodb")
def test_an_advance_answers_the_value_the_field_held_before() -> None:
    assert advance("the-table", KEY, "next_pop", UpdateExpression="SET #next = #next + :one") == 6


def _update(dynamodb: SimpleNamespace) -> Dict[str, Any]:
    updates: List[Dict[str, Any]] = dynamodb.updates
    return updates[0]


def test_an_advance_goes_to_the_table_it_names(dynamodb: SimpleNamespace) -> None:
    advance("the-table", KEY, "next_pop", UpdateExpression="SET #next = #next + :one")
    assert _update(dynamodb)["TableName"] == "the-table"


def test_an_advance_is_of_the_key_it_names(dynamodb: SimpleNamespace) -> None:
    advance("the-table", KEY, "next_pop", UpdateExpression="SET #next = #next + :one")
    assert _update(dynamodb)["Key"] == KEY


def test_an_advance_names_the_field_it_moves(dynamodb: SimpleNamespace) -> None:
    advance("the-table", KEY, "next_pop", UpdateExpression="SET #next = #next + :one")
    assert _update(dynamodb)["ExpressionAttributeNames"] == {"#next": "next_pop"}


def test_an_advance_moves_the_field_by_one(dynamodb: SimpleNamespace) -> None:
    advance("the-table", KEY, "next_pop", UpdateExpression="SET #next = #next + :one")
    assert _update(dynamodb)["ExpressionAttributeValues"] == {":one": {"N": "1"}}


def test_an_advance_asks_for_the_new_value(dynamodb: SimpleNamespace) -> None:
    advance("the-table", KEY, "next_pop", UpdateExpression="SET #next = #next + :one")
    assert _update(dynamodb)["ReturnValues"] == "UPDATED_NEW"


def test_an_advance_passes_the_rest_of_the_request_through(dynamodb: SimpleNamespace) -> None:
    advance("the-table", KEY, "next_pop", ConditionExpression="attribute_exists(PK)")
    assert _update(dynamodb)["ConditionExpression"] == "attribute_exists(PK)"


@pytest.mark.usefixtures("dynamodb")
def test_the_next_id_is_the_one_the_counter_held() -> None:
    assert next_id("the-table", "carriers") == 6


def test_the_next_id_comes_from_the_collection_s_counter_item(dynamodb: SimpleNamespace) -> None:
    next_id("the-table", "carriers")
    assert _update(dynamodb)["Key"] == {"PK": {"S": "carriers"}, "SK": {"S": "#"}}


def test_the_next_id_starts_a_counter_that_is_not_there_at_one(dynamodb: SimpleNamespace) -> None:
    next_id("the-table", "carriers")
    assert _update(dynamodb)["UpdateExpression"] == "SET #next = if_not_exists(#next, :one) + :one"


def test_the_next_id_moves_the_counter_s_next_field(dynamodb: SimpleNamespace) -> None:
    next_id("the-table", "carriers")
    assert _update(dynamodb)["ExpressionAttributeNames"] == {"#next": "next"}


@pytest.mark.usefixtures("dynamodb")
def test_a_put_answers_the_item_it_wrote() -> None:
    item = put("the-table", "carriers/1", "pops/2", {"municipality": {"S": "Boise"}})
    assert item == {
        "PK": {"S": "carriers/1"}, "SK": {"S": "pops/2"}, "municipality": {"S": "Boise"},
    }


def test_a_put_writes_the_item_to_the_table_it_names(dynamodb: SimpleNamespace) -> None:
    item = put("the-table", "carriers/1", "pops/2", {"municipality": {"S": "Boise"}})
    assert dynamodb.puts[0] == {"TableName": "the-table", "Item": item}


def test_a_put_passes_the_rest_of_the_request_through(dynamodb: SimpleNamespace) -> None:
    put("the-table", "carriers/1", "pops/2", {}, ConditionExpression="attribute_exists(PK)")
    assert dynamodb.puts[0]["ConditionExpression"] == "attribute_exists(PK)"


def test_a_conditional_check_that_failed_is_conditional() -> None:
    error = ClientError({"Error": {"Code": "ConditionalCheckFailedException"}}, "PutItem")
    assert conditional(error)


def test_any_other_refusal_is_not_conditional() -> None:
    assert not conditional(ClientError({"Error": {"Code": "InternalServerError"}}, "PutItem"))
