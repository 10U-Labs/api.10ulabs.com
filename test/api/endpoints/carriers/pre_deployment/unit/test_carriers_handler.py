from types import ModuleType, SimpleNamespace
from typing import Any, Dict, List

import pytest
from harness import CARRIERS, answer, get, post, served, stored

CARRIER = "/carriers/{carrier}"


def test_an_empty_store_answers_no_carriers(carriers_handler: ModuleType) -> None:
    assert served(carriers_handler, get()) == []


def test_an_empty_store_answers_200(carriers_handler: ModuleType) -> None:
    assert answer(carriers_handler, get())["statusCode"] == 200


def test_the_carriers_answer_by_id_and_name_in_id_order(
    carriers_handler: ModuleType, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    listed = served(carriers_handler, get())
    assert listed == [{"id": 1, "name": "lumen"}, {"id": 2, "name": "zayo"}]


def test_the_carriers_are_read_from_the_table_the_environment_names(
    carriers_handler: ModuleType, store: SimpleNamespace
) -> None:
    answer(carriers_handler, get())
    assert store.queries[0]["TableName"] == "store"


def test_the_carriers_are_read_from_their_own_partition(
    carriers_handler: ModuleType, store: SimpleNamespace
) -> None:
    answer(carriers_handler, get())
    assert store.queries[0]["ExpressionAttributeValues"] == {":pk": {"S": "carriers"}}


def test_a_store_that_refuses_the_read_answers_500(
    carriers_handler: ModuleType, store: SimpleNamespace
) -> None:
    store.failing = True
    assert answer(carriers_handler, get())["statusCode"] == 500


def test_a_store_that_refuses_the_read_names_the_error(
    carriers_handler: ModuleType, store: SimpleNamespace
) -> None:
    store.failing = True
    assert served(carriers_handler, get())["error"] == "Failed to read the carriers"


def test_another_resource_answers_404(carriers_handler: ModuleType) -> None:
    assert answer(carriers_handler, get("/pops"))["statusCode"] == 404


def _get_one(carrier: str) -> Dict[str, Any]:
    return {**get(CARRIER), "pathParameters": {"carrier": carrier}}


def test_a_stored_carrier_answers_200(
    carriers_handler: ModuleType, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert answer(carriers_handler, _get_one("2"))["statusCode"] == 200


def test_a_stored_carrier_answers_by_id_and_name(
    carriers_handler: ModuleType, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert served(carriers_handler, _get_one("2")) == {"id": 2, "name": "zayo"}


def test_a_carrier_is_read_from_the_table_the_environment_names(
    carriers_handler: ModuleType, store: SimpleNamespace
) -> None:
    answer(carriers_handler, _get_one("2"))
    assert store.gets[0]["TableName"] == "store"


def test_a_carrier_is_read_by_its_key_in_the_collection(
    carriers_handler: ModuleType, store: SimpleNamespace
) -> None:
    answer(carriers_handler, _get_one("2"))
    assert store.gets[0]["Key"] == {"PK": {"S": "carriers"}, "SK": {"S": "2"}}


def test_an_unknown_carrier_answers_404(
    carriers_handler: ModuleType, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert answer(carriers_handler, _get_one("3"))["statusCode"] == 404


def test_an_unknown_carrier_names_the_error(carriers_handler: ModuleType) -> None:
    assert served(carriers_handler, _get_one("3"))["error"] == "No such carrier"


@pytest.mark.parametrize("carrier", ["#", "", "lumen", "-1"])
def test_an_id_that_is_not_a_number_answers_404(carriers_handler: ModuleType, carrier: str) -> None:
    assert answer(carriers_handler, _get_one(carrier))["statusCode"] == 404


def test_the_counter_is_never_asked_for_as_a_carrier(
    carriers_handler: ModuleType, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    answer(carriers_handler, _get_one("#"))
    assert store.gets == []


def test_a_store_that_refuses_the_carrier_answers_500(
    carriers_handler: ModuleType, store: SimpleNamespace
) -> None:
    store.failing = True
    assert answer(carriers_handler, _get_one("2"))["statusCode"] == 500


def test_a_store_that_refuses_the_carrier_names_the_error(
    carriers_handler: ModuleType, store: SimpleNamespace
) -> None:
    store.failing = True
    assert served(carriers_handler, _get_one("2"))["error"] == "Failed to read the carrier"


def _counter(store: SimpleNamespace) -> Dict[str, Any]:
    return next(item for item in store.items if item["SK"] == {"S": "#"})


def test_a_carrier_is_created_with_201(carriers_handler: ModuleType) -> None:
    assert answer(carriers_handler, post({"name": "lumen"}))["statusCode"] == 201


def test_the_first_carrier_is_number_one(carriers_handler: ModuleType) -> None:
    assert served(carriers_handler, post({"name": "lumen"})) == {"id": 1, "name": "lumen"}


def test_the_created_carrier_is_located_under_the_collection(carriers_handler: ModuleType) -> None:
    headers = answer(carriers_handler, post({"name": "lumen"}))["headers"]
    assert headers["Location"] == "/carriers/1"


def test_the_id_is_the_next_the_counter_holds(
    carriers_handler: ModuleType, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert served(carriers_handler, post({"name": "cogent"}))["id"] == 3


def test_the_counter_moves_past_the_id_it_gave(
    carriers_handler: ModuleType, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    answer(carriers_handler, post({"name": "cogent"}))
    assert _counter(store)["next"] == {"N": "4"}


def test_an_id_is_never_reused(carriers_handler: ModuleType) -> None:
    given = [served(carriers_handler, post({"name": name}))["id"] for name in ("lumen", "zayo")]
    assert given == [1, 2]


def test_the_counter_is_advanced_in_the_table_the_environment_names(
    carriers_handler: ModuleType, store: SimpleNamespace
) -> None:
    answer(carriers_handler, post({"name": "lumen"}))
    assert store.updates[0]["TableName"] == "store"


def test_the_counter_is_the_hash_item_of_the_collection(
    carriers_handler: ModuleType, store: SimpleNamespace
) -> None:
    answer(carriers_handler, post({"name": "lumen"}))
    assert store.updates[0]["Key"] == {"PK": {"S": "carriers"}, "SK": {"S": "#"}}


def test_the_carrier_is_written_with_its_own_counters_at_one(
    carriers_handler: ModuleType, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    answer(carriers_handler, post({"name": "cogent"}))
    assert store.items[-1] == {
        "PK": {"S": "carriers"}, "SK": {"S": "3"}, "name": {"S": "cogent"},
        "next_pop": {"N": "1"}, "next_fiber_segment": {"N": "1"},
    }


def test_the_created_carrier_is_then_listed(carriers_handler: ModuleType) -> None:
    answer(carriers_handler, post({"name": "lumen"}))
    assert served(carriers_handler, get()) == [{"id": 1, "name": "lumen"}]


@pytest.mark.parametrize("body", [
    {},
    {"name": 1},
    {"name": ""},
    {"name": "lumen", "id": 9},
    ["lumen"],
])
def test_a_body_that_is_not_exactly_a_name_answers_400(
    carriers_handler: ModuleType, body: Any
) -> None:
    assert answer(carriers_handler, post(body))["statusCode"] == 400


def test_a_body_that_is_not_json_answers_400(carriers_handler: ModuleType) -> None:
    event = {"resource": CARRIERS, "httpMethod": "POST", "body": "{"}
    assert answer(carriers_handler, event)["statusCode"] == 400


def test_a_refused_body_names_what_is_expected(carriers_handler: ModuleType) -> None:
    assert served(carriers_handler, post({}))["error"] == "The body must be exactly {\"name\"}"


def test_a_refused_body_writes_nothing(
    carriers_handler: ModuleType, store: SimpleNamespace
) -> None:
    answer(carriers_handler, post({}))
    assert store.items == []


def test_a_store_that_refuses_the_write_answers_500(
    carriers_handler: ModuleType, store: SimpleNamespace
) -> None:
    store.failing = True
    assert answer(carriers_handler, post({"name": "lumen"}))["statusCode"] == 500


def test_a_store_that_refuses_the_write_names_the_error(
    carriers_handler: ModuleType, store: SimpleNamespace
) -> None:
    store.failing = True
    error = served(carriers_handler, post({"name": "lumen"}))["error"]
    assert error == "Failed to create the carrier"


def _put(body: Any, carrier: str = "2") -> Dict[str, Any]:
    return {**post(body, CARRIER), "httpMethod": "PUT", "pathParameters": {"carrier": carrier}}


def test_a_stored_carrier_is_renamed_with_200(
    carriers_handler: ModuleType, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert answer(carriers_handler, _put({"name": "zayo group"}))["statusCode"] == 200


def test_a_renamed_carrier_answers_by_id_and_new_name(
    carriers_handler: ModuleType, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert served(carriers_handler, _put({"name": "zayo group"})) == {"id": 2, "name": "zayo group"}


def test_a_renamed_carrier_is_then_listed_by_its_new_name(
    carriers_handler: ModuleType, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    answer(carriers_handler, _put({"name": "zayo group"}))
    listed = served(carriers_handler, get())
    assert listed == [{"id": 1, "name": "lumen"}, {"id": 2, "name": "zayo group"}]


def test_a_rename_keeps_the_carrier_s_own_counters(
    carriers_handler: ModuleType, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    answer(carriers_handler, _put({"name": "lumen technologies"}, "1"))
    assert stored(store, "1")["next_pop"] == {"N": "4"}


@pytest.fixture(name="rename_request")
def rename_request_fixture(
    carriers_handler: ModuleType, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> Dict[str, Any]:
    store.items.extend(carriers)
    answer(carriers_handler, _put({"name": "zayo group"}))
    return dict(store.updates[0])


def test_a_rename_goes_to_the_table_the_environment_names(rename_request: Dict[str, Any]) -> None:
    assert rename_request["TableName"] == "store"


def test_a_rename_is_of_the_carrier_s_key(rename_request: Dict[str, Any]) -> None:
    assert rename_request["Key"] == {"PK": {"S": "carriers"}, "SK": {"S": "2"}}


def test_a_rename_requires_the_carrier_to_exist_in_the_store(
    rename_request: Dict[str, Any]
) -> None:
    assert rename_request["ConditionExpression"] == "attribute_exists(PK)"


def test_renaming_an_unknown_carrier_answers_404(carriers_handler: ModuleType) -> None:
    assert answer(carriers_handler, _put({"name": "zayo group"}))["statusCode"] == 404


def test_renaming_an_unknown_carrier_names_the_error(carriers_handler: ModuleType) -> None:
    assert served(carriers_handler, _put({"name": "zayo group"}))["error"] == "No such carrier"


@pytest.mark.parametrize("carrier", ["#", "", "lumen", "-1"])
def test_renaming_an_id_that_is_not_a_number_answers_404(
    carriers_handler: ModuleType, carrier: str
) -> None:
    assert answer(carriers_handler, _put({"name": "zayo group"}, carrier))["statusCode"] == 404


def test_renaming_an_id_that_is_not_a_number_asks_the_store_nothing(
    carriers_handler: ModuleType, store: SimpleNamespace
) -> None:
    answer(carriers_handler, _put({"name": "zayo group"}, "#"))
    assert store.updates == []


@pytest.mark.parametrize("body", [
    {},
    {"name": 1},
    {"name": ""},
    {"name": "zayo group", "id": 9},
    ["zayo group"],
])
def test_a_rename_that_is_not_exactly_a_name_answers_400(
    carriers_handler: ModuleType, store: SimpleNamespace, carriers: List[Dict[str, Any]], body: Any
) -> None:
    store.items.extend(carriers)
    assert answer(carriers_handler, _put(body))["statusCode"] == 400


def test_a_rename_that_is_not_json_answers_400(carriers_handler: ModuleType) -> None:
    event = {**_put({}), "body": "{"}
    assert answer(carriers_handler, event)["statusCode"] == 400


def test_a_refused_rename_names_what_is_expected(carriers_handler: ModuleType) -> None:
    assert served(carriers_handler, _put({}))["error"] == "The body must be exactly {\"name\"}"


def test_a_refused_rename_changes_nothing(
    carriers_handler: ModuleType, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    answer(carriers_handler, _put({}))
    assert (store.updates, stored(store, "2")["name"]) == ([], {"S": "zayo"})


def test_a_store_that_refuses_the_rename_answers_500(
    carriers_handler: ModuleType, store: SimpleNamespace
) -> None:
    store.failing = True
    assert answer(carriers_handler, _put({"name": "zayo group"}))["statusCode"] == 500


def test_a_store_that_refuses_the_rename_names_the_error(
    carriers_handler: ModuleType, store: SimpleNamespace
) -> None:
    store.failing = True
    error = served(carriers_handler, _put({"name": "zayo group"}))["error"]
    assert error == "Failed to update the carrier"


def _delete(carrier: str = "1") -> Dict[str, Any]:
    return {**get(CARRIER), "httpMethod": "DELETE", "pathParameters": {"carrier": carrier}}


@pytest.fixture(name="deleted")
def deleted_fixture(
    carriers_handler: ModuleType, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> Dict[str, Any]:
    store.items.extend(carriers)
    return dict(answer(carriers_handler, _delete()))


def test_a_stored_carrier_is_deleted_with_204(deleted: Dict[str, Any]) -> None:
    assert deleted["statusCode"] == 204


def test_a_deletion_answers_noserved(deleted: Dict[str, Any]) -> None:
    assert deleted["body"] == ""


@pytest.mark.usefixtures("deleted")
def test_a_deleted_carrier_is_no_longer_listed(carriers_handler: ModuleType) -> None:
    assert served(carriers_handler, get()) == [{"id": 2, "name": "zayo"}]


@pytest.mark.usefixtures("deleted")
def test_a_deleted_carrier_is_no_longer_served(carriers_handler: ModuleType) -> None:
    assert answer(carriers_handler, _get_one("1"))["statusCode"] == 404


@pytest.mark.usefixtures("deleted")
def test_everything_under_a_deleted_carrier_goes_with_it(store: SimpleNamespace) -> None:
    assert [item for item in store.items if item["PK"] == {"S": "carriers/1"}] == []


@pytest.mark.usefixtures("deleted")
def test_a_deletion_leaves_the_other_carriers_alone(store: SimpleNamespace) -> None:
    assert [item["SK"]["S"] for item in store.items] == ["#", "2"]


@pytest.mark.usefixtures("deleted")
def test_a_deletion_goes_to_the_table_the_environment_names(store: SimpleNamespace) -> None:
    assert {request["TableName"] for request in store.deletes} == {"store"}


@pytest.mark.usefixtures("deleted")
def test_the_carrier_is_deleted_after_everything_under_it(store: SimpleNamespace) -> None:
    assert [request["Key"] for request in store.deletes] == [
        {"PK": {"S": "carriers/1"}, "SK": {"S": "pops/3"}},
        {"PK": {"S": "carriers/1"}, "SK": {"S": "pops/1"}},
        {"PK": {"S": "carriers/1"}, "SK": {"S": "fiber_segments/1"}},
        {"PK": {"S": "carriers"}, "SK": {"S": "1"}},
    ]


@pytest.mark.usefixtures("deleted")
def test_deleting_the_carrier_requires_it_to_exist_in_the_store(store: SimpleNamespace) -> None:
    assert store.deletes[-1]["ConditionExpression"] == "attribute_exists(PK)"


def test_deleting_an_unknown_carrier_answers_404(carriers_handler: ModuleType) -> None:
    assert answer(carriers_handler, _delete("3"))["statusCode"] == 404


def test_deleting_an_unknown_carrier_names_the_error(carriers_handler: ModuleType) -> None:
    assert served(carriers_handler, _delete("3"))["error"] == "No such carrier"


@pytest.mark.parametrize("carrier", ["#", "", "lumen", "-1"])
def test_deleting_an_id_that_is_not_a_number_answers_404(
    carriers_handler: ModuleType, carrier: str
) -> None:
    assert answer(carriers_handler, _delete(carrier))["statusCode"] == 404


def test_deleting_an_id_that_is_not_a_number_deletes_nothing(
    carriers_handler: ModuleType, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    answer(carriers_handler, _delete("#"))
    assert (store.deletes, len(store.items)) == ([], 6)


def test_a_store_that_refuses_the_deletion_answers_500(
    carriers_handler: ModuleType, store: SimpleNamespace
) -> None:
    store.failing = True
    assert answer(carriers_handler, _delete())["statusCode"] == 500


def test_a_store_that_refuses_the_deletion_names_the_error(
    carriers_handler: ModuleType, store: SimpleNamespace
) -> None:
    store.failing = True
    assert served(carriers_handler, _delete())["error"] == "Failed to delete the carrier"
