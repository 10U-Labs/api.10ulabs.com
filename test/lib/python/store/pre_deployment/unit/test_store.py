from types import SimpleNamespace
from typing import Any, Dict, List

import pytest
from botocore.exceptions import ClientError

import store
from store import (
    ATTEMPTS, BATCH, PAUSE, assign, batch_write, conditional, conditioned, delete, member,
    members, next_id, partition, plain, put, remove, reserve, sort_id, typed,
)

COUNTER = {"PK": {"S": "carriers"}, "SK": {"S": "#"}, "next": {"N": "3"}}
LUMEN = {"PK": {"S": "carriers"}, "SK": {"S": "1"}, "name": {"S": "lumen"}}
ZAYO = {"PK": {"S": "carriers"}, "SK": {"S": "2"}, "name": {"S": "zayo"}}


@pytest.fixture(name="dynamodb")
def dynamodb_fixture(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    dynamodb = SimpleNamespace(
        queries=[], gets=[], updates=[], puts=[], deletes=[], batches=[], unprocessed=[],
        sleeps=[], items=[COUNTER, ZAYO, LUMEN],
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
        field = next(iter(request["ExpressionAttributeNames"].values()))
        return {"Attributes": {field: {"N": "7"}}}

    def put_item(**request: Any) -> Dict[str, Any]:
        dynamodb.puts.append(request)
        return {}

    def delete_item(**request: Any) -> Dict[str, Any]:
        dynamodb.deletes.append(request)
        held = [item for item in dynamodb.items if item["SK"] == request["Key"]["SK"]]
        if not held:
            raise ClientError({"Error": {"Code": "ConditionalCheckFailedException"}}, "DeleteItem")
        return {"Attributes": held[0]}

    def batch_write_item(**request: Any) -> Dict[str, Any]:
        dynamodb.batches.append(request)
        sent = [one for listed in request["RequestItems"].values() for one in listed]
        deleted = [one["DeleteRequest"]["Key"]["SK"] for one in sent if "DeleteRequest" in one]
        dynamodb.items = [item for item in dynamodb.items if item["SK"] not in deleted]
        return {"UnprocessedItems": dynamodb.unprocessed.pop(0) if dynamodb.unprocessed else {}}

    dynamodb.query = query
    dynamodb.get_item = get_item
    dynamodb.update_item = update_item
    dynamodb.put_item = put_item
    dynamodb.delete_item = delete_item
    dynamodb.batch_write_item = batch_write_item
    monkeypatch.setattr(store, "aws_client", lambda service: {"dynamodb": dynamodb}[service])
    monkeypatch.setattr(store, "time", SimpleNamespace(sleep=dynamodb.sleeps.append))
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


PAGES = [[COUNTER, ZAYO], [LUMEN]]


@pytest.fixture(name="paged")
def paged_fixture(dynamodb: SimpleNamespace) -> SimpleNamespace:
    def query(**request: Any) -> Dict[str, Any]:
        dynamodb.queries.append(request)
        page = PAGES[len(dynamodb.queries) - 1]
        answer: Dict[str, Any] = {"Items": list(page), "Count": len(page)}
        if page is not PAGES[-1]:
            answer["LastEvaluatedKey"] = {"PK": page[-1]["PK"], "SK": page[-1]["SK"]}
        return answer
    dynamodb.query = query
    return dynamodb


@pytest.mark.usefixtures("paged")
def test_a_partition_larger_than_a_page_answers_the_items_of_every_page() -> None:
    assert partition("the-table", "carriers") == [COUNTER, ZAYO, LUMEN]


def test_each_page_of_a_partition_starts_after_the_last_key_of_the_page_before(
    paged: SimpleNamespace
) -> None:
    partition("the-table", "carriers")
    assert [query.get("ExclusiveStartKey") for query in paged.queries] == [
        None, {"PK": ZAYO["PK"], "SK": ZAYO["SK"]},
    ]


def test_every_page_of_a_partition_is_read_by_its_key_and_prefix(paged: SimpleNamespace) -> None:
    partition("the-table", "carriers/1", "pops/")
    assert {query["KeyConditionExpression"] for query in paged.queries} == {
        "PK = :pk AND begins_with(SK, :prefix)",
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


def _update(dynamodb: SimpleNamespace) -> Dict[str, Any]:
    updates: List[Dict[str, Any]] = dynamodb.updates
    return updates[0]


@pytest.mark.usefixtures("dynamodb")
def test_a_reservation_answers_the_first_of_the_ids_it_takes() -> None:
    assert reserve("the-table", KEY, "next_pop", 3) == 4


def test_a_reservation_goes_to_the_table_it_names(dynamodb: SimpleNamespace) -> None:
    reserve("the-table", KEY, "next_pop", 3)
    assert _update(dynamodb)["TableName"] == "the-table"


def test_a_reservation_is_of_the_key_it_names(dynamodb: SimpleNamespace) -> None:
    reserve("the-table", KEY, "next_pop", 3)
    assert _update(dynamodb)["Key"] == KEY


def test_a_reservation_names_the_field_it_moves(dynamodb: SimpleNamespace) -> None:
    reserve("the-table", KEY, "next_pop", 3)
    assert _update(dynamodb)["ExpressionAttributeNames"] == {"#next": "next_pop"}


def test_a_reservation_starts_a_field_that_is_not_there_at_one(dynamodb: SimpleNamespace) -> None:
    reserve("the-table", KEY, "next_pop", 3)
    expression = "SET #next = if_not_exists(#next, :one) + :count"
    assert _update(dynamodb)["UpdateExpression"] == expression


def test_a_reservation_moves_the_field_by_its_count(dynamodb: SimpleNamespace) -> None:
    reserve("the-table", KEY, "next_pop", 3)
    values = {":one": {"N": "1"}, ":count": {"N": "3"}}
    assert _update(dynamodb)["ExpressionAttributeValues"] == values


def test_a_reservation_asks_for_the_new_value(dynamodb: SimpleNamespace) -> None:
    reserve("the-table", KEY, "next_pop", 3)
    assert _update(dynamodb)["ReturnValues"] == "UPDATED_NEW"


def test_a_reservation_passes_the_rest_of_the_request_through(dynamodb: SimpleNamespace) -> None:
    reserve("the-table", KEY, "next_pop", 3, ConditionExpression="attribute_exists(PK)")
    assert _update(dynamodb)["ConditionExpression"] == "attribute_exists(PK)"


@pytest.mark.usefixtures("dynamodb")
def test_the_next_id_is_the_one_the_counter_held() -> None:
    assert next_id("the-table", "carriers") == 6


def test_the_next_id_comes_from_the_collection_s_counter_item(dynamodb: SimpleNamespace) -> None:
    next_id("the-table", "carriers")
    assert _update(dynamodb)["Key"] == {"PK": {"S": "carriers"}, "SK": {"S": "#"}}


def test_the_next_id_starts_a_counter_that_is_not_there_at_one(dynamodb: SimpleNamespace) -> None:
    next_id("the-table", "carriers")
    expression = "SET #next = if_not_exists(#next, :one) + :count"
    assert _update(dynamodb)["UpdateExpression"] == expression


def test_the_next_id_moves_the_counter_by_one(dynamodb: SimpleNamespace) -> None:
    next_id("the-table", "carriers")
    values = {":one": {"N": "1"}, ":count": {"N": "1"}}
    assert _update(dynamodb)["ExpressionAttributeValues"] == values


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


@pytest.mark.usefixtures("dynamodb")
def test_a_deletion_answers_the_item_that_was_there() -> None:
    assert delete("the-table", "carriers", "2") == ZAYO


@pytest.mark.usefixtures("dynamodb")
def test_a_deletion_of_an_item_that_is_not_there_answers_none() -> None:
    assert delete("the-table", "carriers", "3") is None


def test_a_deletion_goes_to_the_table_it_names(dynamodb: SimpleNamespace) -> None:
    delete("the-table", "carriers", "2")
    assert dynamodb.deletes[0]["TableName"] == "the-table"


def test_a_deletion_is_of_the_item_s_key(dynamodb: SimpleNamespace) -> None:
    delete("the-table", "carriers", "2")
    assert dynamodb.deletes[0]["Key"] == {"PK": {"S": "carriers"}, "SK": {"S": "2"}}


def test_a_deletion_requires_the_item_to_exist(dynamodb: SimpleNamespace) -> None:
    delete("the-table", "carriers", "2")
    assert dynamodb.deletes[0]["ConditionExpression"] == "attribute_exists(PK)"


def test_a_deletion_asks_for_the_old_values(dynamodb: SimpleNamespace) -> None:
    delete("the-table", "carriers", "2")
    assert dynamodb.deletes[0]["ReturnValues"] == "ALL_OLD"


def test_a_deletion_the_store_refuses_for_another_reason_is_raised(
    dynamodb: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    def refuse(**_request: Any) -> Dict[str, Any]:
        raise ClientError({"Error": {"Code": "InternalServerError"}}, "DeleteItem")
    monkeypatch.setattr(dynamodb, "delete_item", refuse)
    with pytest.raises(ClientError):
        delete("the-table", "carriers", "2")


RENAME = {"UpdateExpression": "SET #next = :one", "ExpressionAttributeNames": {"#next": "next"}}


@pytest.mark.usefixtures("dynamodb")
def test_a_conditioned_write_answers_the_attributes_the_store_returns() -> None:
    assert conditioned("update_item", "the-table", KEY, **RENAME) == {"next": {"N": "7"}}


def test_a_conditioned_write_requires_the_item_to_exist(dynamodb: SimpleNamespace) -> None:
    conditioned("update_item", "the-table", KEY, **RENAME)
    assert dynamodb.updates[0]["ConditionExpression"] == "attribute_exists(PK)"


@pytest.mark.parametrize(("value", "expected"), [
    ({"S": "minuteman"}, "minuteman"),
    ({"N": "3"}, 3),
    ({"N": "-12"}, -12),
    ({"N": "0.6"}, 0.6),
    ({"BOOL": False}, False),
    ({"NULL": True}, None),
    ({"M": {"min": {"N": "3"}, "max": {"N": "6"}}}, {"min": 3, "max": 6}),
    ({"L": [{"S": "a"}, {"N": "1"}]}, ["a", 1]),
    ({"M": {"ceilings": {"L": [{"M": {"miles": {"N": "1.5"}}}]}}}, {"ceilings": [{"miles": 1.5}]}),
])
def test_plain_turns_an_attribute_value_into_json(value: Dict[str, Any], expected: Any) -> None:
    assert plain(value) == expected


def test_plain_keeps_an_integral_number_an_int() -> None:
    assert isinstance(plain({"N": "3"}), int)


def test_the_sort_id_of_a_top_level_item_is_its_sort_key() -> None:
    assert sort_id({"PK": {"S": "carriers"}, "SK": {"S": "3"}}) == 3


def test_the_sort_id_of_an_item_under_a_member_follows_its_prefix() -> None:
    assert sort_id({"PK": {"S": "carriers/1"}, "SK": {"S": "pops/7"}}) == 7


@pytest.mark.parametrize(("value", "expected"), [
    ("minuteman", {"S": "minuteman"}),
    (3, {"N": "3"}),
    (-12, {"N": "-12"}),
    (0.6, {"N": "0.6"}),
    (False, {"BOOL": False}),
    (None, {"NULL": True}),
    ({"min": 3, "max": 6}, {"M": {"min": {"N": "3"}, "max": {"N": "6"}}}),
    (["a", 1], {"L": [{"S": "a"}, {"N": "1"}]}),
    ({"ceilings": [{"miles": 1.5}]}, {"M": {"ceilings": {"L": [{"M": {"miles": {"N": "1.5"}}}]}}}),
])
def test_typed_turns_json_into_an_attribute_value(value: Any, expected: Dict[str, Any]) -> None:
    assert typed(value) == expected


@pytest.mark.parametrize("value", [3, 0.6, "3", False, None, {"a": [1]}])
def test_typed_is_undone_by_plain(value: Any) -> None:
    assert plain(typed(value)) == value


STATUS = {"status": "fail", "reason": "No backbone"}


@pytest.mark.usefixtures("dynamodb")
def test_an_assignment_answers_the_attributes_the_store_returns() -> None:
    assert assign("the-table", "wan-syntheses", "1", STATUS) == {"status": {"N": "7"}}


def test_an_assignment_goes_to_the_table_it_names(dynamodb: SimpleNamespace) -> None:
    assign("the-table", "wan-syntheses", "1", STATUS)
    assert _update(dynamodb)["TableName"] == "the-table"


def test_an_assignment_is_of_the_key_it_names(dynamodb: SimpleNamespace) -> None:
    assign("the-table", "wan-syntheses", "1", STATUS)
    assert _update(dynamodb)["Key"] == {"PK": {"S": "wan-syntheses"}, "SK": {"S": "1"}}


def test_an_assignment_sets_every_attribute_by_a_placeholder(dynamodb: SimpleNamespace) -> None:
    assign("the-table", "wan-syntheses", "1", STATUS)
    assert _update(dynamodb)["UpdateExpression"] == "SET #0 = :0, #1 = :1"


def test_an_assignment_names_the_attributes_it_sets(dynamodb: SimpleNamespace) -> None:
    assign("the-table", "wan-syntheses", "1", STATUS)
    assert _update(dynamodb)["ExpressionAttributeNames"] == {"#0": "status", "#1": "reason"}


def test_an_assignment_types_the_values_it_sets(dynamodb: SimpleNamespace) -> None:
    assign("the-table", "wan-syntheses", "1", STATUS)
    assert _update(dynamodb)["ExpressionAttributeValues"] == {
        ":0": {"S": "fail"}, ":1": {"S": "No backbone"},
    }


def test_an_assignment_requires_the_item_to_exist(dynamodb: SimpleNamespace) -> None:
    assign("the-table", "wan-syntheses", "1", STATUS)
    assert _update(dynamodb)["ConditionExpression"] == "attribute_exists(PK)"


def test_an_assignment_asks_for_the_whole_item(dynamodb: SimpleNamespace) -> None:
    assign("the-table", "wan-syntheses", "1", STATUS)
    assert _update(dynamodb)["ReturnValues"] == "ALL_NEW"


UNDER_LUMEN = [
    {"PK": {"S": "carriers/1"}, "SK": {"S": "pops/2"}},
    {"PK": {"S": "carriers/1"}, "SK": {"S": "pops/1"}},
]


@pytest.fixture(name="furnished")
def furnished_fixture(dynamodb: SimpleNamespace) -> SimpleNamespace:
    def query(**request: Any) -> Dict[str, Any]:
        dynamodb.queries.append(request)
        return {"Items": list(UNDER_LUMEN), "Count": len(UNDER_LUMEN)}
    dynamodb.query = query
    dynamodb.items.extend(UNDER_LUMEN)
    return dynamodb


@pytest.mark.usefixtures("furnished")
def test_a_removal_of_a_member_that_is_there_answers_true() -> None:
    assert remove("the-table", "carriers", "1") is True


@pytest.mark.usefixtures("furnished")
def test_a_removal_of_a_member_that_is_not_there_answers_false() -> None:
    assert remove("the-table", "carriers", "3") is False


def test_a_removal_reads_everything_under_the_member(furnished: SimpleNamespace) -> None:
    remove("the-table", "carriers", "1")
    assert _query(furnished)["ExpressionAttributeValues"] == {":pk": {"S": "carriers/1"}}


def _batched(dynamodb: SimpleNamespace) -> List[List[Dict[str, Any]]]:
    batches: List[Dict[str, Any]] = dynamodb.batches
    return [
        [one["DeleteRequest"]["Key"] for one in batch["RequestItems"]["the-table"]]
        for batch in batches
    ]


@pytest.fixture(name="crowded")
def crowded_fixture(dynamodb: SimpleNamespace) -> SimpleNamespace:
    under = [{"PK": {"S": "carriers/1"}, "SK": {"S": f"pops/{n}"}} for n in range(BATCH + 5)]

    def query(**request: Any) -> Dict[str, Any]:
        dynamodb.queries.append(request)
        return {"Items": list(under), "Count": len(under)}
    dynamodb.query = query
    dynamodb.items.extend(under)
    return dynamodb


@pytest.fixture(name="bare")
def bare_fixture(dynamodb: SimpleNamespace) -> SimpleNamespace:
    def query(**request: Any) -> Dict[str, Any]:
        dynamodb.queries.append(request)
        return {"Items": [], "Count": 0}
    dynamodb.query = query
    return dynamodb


def test_a_removal_batches_the_deletes_of_everything_under_the_member(
    furnished: SimpleNamespace
) -> None:
    remove("the-table", "carriers", "1")
    assert _batched(furnished) == [UNDER_LUMEN]


def test_a_removal_deletes_the_member_itself_by_one_delete(furnished: SimpleNamespace) -> None:
    remove("the-table", "carriers", "1")
    assert [request["Key"] for request in furnished.deletes] == [
        {"PK": {"S": "carriers"}, "SK": {"S": "1"}},
    ]


def test_a_removal_of_a_member_with_nothing_under_it_batches_nothing(
    bare: SimpleNamespace
) -> None:
    remove("the-table", "carriers", "1")
    assert bare.batches == []


def test_a_removal_sends_at_most_twenty_five_deletes_a_batch(crowded: SimpleNamespace) -> None:
    remove("the-table", "carriers", "1")
    assert [len(batch) for batch in _batched(crowded)] == [BATCH, 5]


def test_a_removal_sends_the_deletes_the_store_left_unprocessed_again(
    furnished: SimpleNamespace
) -> None:
    furnished.unprocessed = [{"the-table": [{"DeleteRequest": {"Key": UNDER_LUMEN[1]}}]}]
    remove("the-table", "carriers", "1")
    assert _batched(furnished) == [UNDER_LUMEN, [UNDER_LUMEN[1]]]


def test_a_removal_goes_to_the_table_it_names(furnished: SimpleNamespace) -> None:
    remove("the-table", "carriers", "1")
    tables = {request["TableName"] for request in furnished.deletes}
    assert tables | {table for batch in furnished.batches for table in batch["RequestItems"]} == {
        "the-table"
    }


def test_a_removal_requires_the_member_alone_to_exist(furnished: SimpleNamespace) -> None:
    remove("the-table", "carriers", "1")
    assert [request.get("ConditionExpression") for request in furnished.deletes] == [
        "attribute_exists(PK)",
    ]


def test_a_removal_the_store_refuses_for_another_reason_is_raised(
    furnished: SimpleNamespace
) -> None:
    def refuse(**request: Any) -> Dict[str, Any]:
        if "ConditionExpression" in request:
            raise ClientError({"Error": {"Code": "InternalServerError"}}, "DeleteItem")
        return {}
    furnished.delete_item = refuse
    with pytest.raises(ClientError):
        remove("the-table", "carriers", "1")


def _put_request(pop: int) -> Dict[str, Any]:
    return {"PutRequest": {"Item": {"PK": {"S": "carriers/1"}, "SK": {"S": f"pops/{pop}"}}}}


PUTS = [_put_request(pop) for pop in range(1, BATCH + 6)]


def _sent(dynamodb: SimpleNamespace) -> List[List[Dict[str, Any]]]:
    batches: List[Dict[str, Any]] = dynamodb.batches
    return [batch["RequestItems"]["the-table"] for batch in batches]


def test_a_batch_write_sends_at_most_twenty_five_requests_a_batch(
    dynamodb: SimpleNamespace
) -> None:
    batch_write("the-table", PUTS)
    assert [len(batch) for batch in _sent(dynamodb)] == [BATCH, 5]


def test_a_batch_write_sends_every_request_in_order(dynamodb: SimpleNamespace) -> None:
    batch_write("the-table", PUTS)
    assert [one for batch in _sent(dynamodb) for one in batch] == PUTS


def test_a_batch_write_sends_the_requests_the_store_left_unprocessed_again(
    dynamodb: SimpleNamespace
) -> None:
    dynamodb.unprocessed = [{"the-table": [PUTS[1]]}]
    batch_write("the-table", PUTS[:2])
    assert _sent(dynamodb) == [PUTS[:2], [PUTS[1]]]


def test_a_batch_write_pauses_before_each_resend_twice_as_long_as_before(
    dynamodb: SimpleNamespace
) -> None:
    dynamodb.unprocessed = [{"the-table": [PUTS[1]]}, {"the-table": [PUTS[1]]}]
    batch_write("the-table", PUTS[:2])
    assert dynamodb.sleeps == [PAUSE, 2 * PAUSE]


def test_a_batch_write_the_store_takes_whole_does_not_pause(dynamodb: SimpleNamespace) -> None:
    batch_write("the-table", PUTS)
    assert dynamodb.sleeps == []


def test_a_batch_write_the_store_keeps_leaving_unprocessed_is_raised(
    dynamodb: SimpleNamespace
) -> None:
    dynamodb.unprocessed = [{"the-table": [PUTS[1]]}] * ATTEMPTS
    with pytest.raises(ClientError):
        batch_write("the-table", PUTS[:2])


@pytest.fixture(name="exhausted")
def exhausted_fixture(dynamodb: SimpleNamespace) -> SimpleNamespace:
    dynamodb.unprocessed = [{"the-table": [PUTS[1]]}] * (ATTEMPTS + 1)
    with pytest.raises(ClientError):
        batch_write("the-table", PUTS[:2])
    return dynamodb


def test_a_batch_write_sends_a_batch_no_more_than_its_attempts(exhausted: SimpleNamespace) -> None:
    assert len(exhausted.batches) == ATTEMPTS


def test_a_batch_write_does_not_pause_after_its_last_attempt(exhausted: SimpleNamespace) -> None:
    assert len(exhausted.sleeps) == ATTEMPTS - 1


def test_a_batch_write_goes_to_the_table_it_names(dynamodb: SimpleNamespace) -> None:
    batch_write("the-table", PUTS[:2])
    assert {table for batch in dynamodb.batches for table in batch["RequestItems"]} == {
        "the-table"
    }


def test_a_batch_write_of_nothing_sends_nothing(dynamodb: SimpleNamespace) -> None:
    batch_write("the-table", [])
    assert dynamodb.batches == []
