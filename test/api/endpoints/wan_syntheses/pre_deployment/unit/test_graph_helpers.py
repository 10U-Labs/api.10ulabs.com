from __future__ import annotations

import math

import pytest

from synthesizer.graphs import (
    articulation_points,
    biconnected_block_membership,
    bridges,
    connected_components,
    dijkstra,
    survives_any_one_site_loss,
    fiber_segments_along,
    reconstruct_path,
)
from synthesizer.input_graph import Site, segment_key, haversine_miles


def make_site(site_id: str, lat: float, lon: float) -> Site:
    return Site(id=site_id, name=site_id, kind="PoP", coords=(lat, lon))


def _adjacency(pairs: list[tuple[str, str]]) -> dict[str, list[tuple[str, float]]]:
    adjacency: dict[str, list[tuple[str, float]]] = {}
    for left, right in pairs:
        adjacency.setdefault(left, []).append((right, 1.0))
        adjacency.setdefault(right, []).append((left, 1.0))
    return adjacency


_TWO_POCKETS = _adjacency(
    [("a", "b"), ("b", "c"), ("a", "c"), ("c", "d"), ("d", "e"), ("e", "f"), ("d", "f")]
)

_BOWTIE = _adjacency(
    [("a", "b"), ("b", "c"), ("a", "c"), ("c", "d"), ("d", "e"), ("c", "e")]
)


def test_segment_key_orders_pair() -> None:
    assert segment_key("b", "a") == ("a", "b")


def test_segment_key_rejects_self_loop() -> None:
    with pytest.raises(ValueError):
        segment_key("a", "a")


def test_haversine_zero_distance() -> None:
    site = make_site("x", 40.0, -100.0)
    assert haversine_miles(site, site) == pytest.approx(0.0)


def test_haversine_known_distance() -> None:
    new_york = make_site("ny", 40.7128, -74.006)
    los_angeles = make_site("la", 34.0522, -118.2437)
    assert haversine_miles(new_york, los_angeles) == pytest.approx(2450.0, abs=30.0)


def test_dijkstra_distance_along_chain() -> None:
    adjacency = {"a": [("b", 2.0)], "b": [("a", 2.0), ("c", 3.0)], "c": [("b", 3.0)]}
    distances, _predecessors = dijkstra(adjacency, "a")
    assert distances["c"] == 5.0


def test_reconstruct_path_along_chain() -> None:
    adjacency = {"a": [("b", 2.0)], "b": [("a", 2.0), ("c", 3.0)], "c": [("b", 3.0)]}
    _distances, predecessors = dijkstra(adjacency, "a")
    assert reconstruct_path("a", "c", predecessors) == ("a", "b", "c")


def test_connected_components_counts_islands() -> None:
    ids = {"a", "b", "c", "d"}
    fiber_segment_keys = {("a", "b"), ("c", "d")}
    assert len(connected_components(ids, fiber_segment_keys)) == 2


def test_articulation_point_detected() -> None:
    ids = {"a", "b", "c"}
    fiber_segment_keys = {("a", "b"), ("b", "c")}
    assert articulation_points(ids, fiber_segment_keys) == {"b"}


def test_cycle_has_no_articulation_points() -> None:
    ids = {"a", "b", "c"}
    fiber_segment_keys = {("a", "b"), ("b", "c"), ("a", "c")}
    assert articulation_points(ids, fiber_segment_keys) == set()


def test_unreachable_target_has_infinite_distance() -> None:
    adjacency = {"a": [("b", 1.0)], "b": [("a", 1.0)], "c": []}
    distances, _predecessors = dijkstra(adjacency, "a")
    assert distances.get("c", math.inf) == math.inf


def test_dijkstra_relaxes_past_a_stale_heap_entry() -> None:
    adjacency = {
        "a": [("b", 10.0), ("c", 1.0)],
        "b": [("a", 10.0), ("c", 1.0)],
        "c": [("a", 1.0), ("b", 1.0)],
    }
    distances, _predecessors = dijkstra(adjacency, "a")
    assert distances["b"] == 2.0


def test_reconstruct_path_source_equals_target() -> None:
    assert reconstruct_path("a", "a", {}) == ("a",)


def test_reconstruct_path_unreachable_returns_empty() -> None:
    assert not reconstruct_path("a", "z", {})


def test_reconstruct_path_broken_chain_returns_empty() -> None:
    assert not reconstruct_path("a", "c", {"c": "b"})


def test_fiber_segments_along_a_three_site_circuit() -> None:
    assert fiber_segments_along(("a", "b", "c")) == {segment_key("a", "b"), segment_key("b", "c")}


def test_dfs_root_with_two_children_is_an_articulation_point() -> None:
    assert articulation_points({"a", "b", "c"}, {("a", "b"), ("a", "c")}) == {"a"}


def test_connected_components_ignores_external_endpoints() -> None:
    components = connected_components({"a", "b"}, {("a", "b"), ("a", "z")})
    assert components == [["a", "b"]]


def test_bridges_names_every_cut_segment_in_a_chain() -> None:
    assert bridges({"a", "b", "c"}, {("a", "b"), ("b", "c")}) == {
        segment_key("a", "b"),
        segment_key("b", "c"),
    }


def test_cycle_has_no_bridges() -> None:
    assert bridges({"a", "b", "c"}, {("a", "b"), ("b", "c"), ("a", "c")}) == set()


def test_dijkstra_paths_around_a_blocked_segment() -> None:
    adjacency = _adjacency([("a", "b"), ("b", "c"), ("a", "c")])
    distances, _predecessors = dijkstra(adjacency, "a", frozenset({segment_key("a", "c")}))
    assert distances["c"] == 2.0


def test_block_membership_labels_a_cycle_as_one_shared_block() -> None:
    blocks = biconnected_block_membership(_adjacency([("a", "b"), ("b", "c"), ("a", "c")]))
    assert blocks["a"] == blocks["b"] == blocks["c"] != frozenset()


def test_block_membership_splits_two_pockets() -> None:
    blocks = biconnected_block_membership(_TWO_POCKETS)
    assert not blocks["a"] & blocks["d"]


def test_block_membership_gives_a_bridge_no_block() -> None:
    blocks = biconnected_block_membership(_TWO_POCKETS)
    assert not blocks["c"] & blocks["d"]


def test_block_membership_labels_a_chain_as_blockless() -> None:
    blocks = biconnected_block_membership(_adjacency([("a", "b"), ("b", "c")]))
    assert blocks == {"a": frozenset(), "b": frozenset(), "c": frozenset()}


def test_block_membership_puts_a_cut_city_in_two_blocks() -> None:
    assert len(biconnected_block_membership(_BOWTIE)["c"]) == 2


def test_block_membership_keeps_bowtie_lobes_in_separate_blocks() -> None:
    blocks = biconnected_block_membership(_BOWTIE)
    assert not blocks["a"] & blocks["d"]


def test_survives_any_one_site_loss_true_for_a_cycle() -> None:
    assert survives_any_one_site_loss({"a", "b", "c"}, {("a", "b"), ("b", "c"), ("a", "c")}) is True


def test_survives_any_one_site_loss_false_for_a_chain() -> None:
    assert survives_any_one_site_loss({"a", "b", "c"}, {("a", "b"), ("b", "c")}) is False


def test_survives_any_one_site_loss_false_when_disconnected() -> None:
    assert survives_any_one_site_loss({"a", "b", "c", "d"}, {("a", "b"), ("c", "d")}) is False
