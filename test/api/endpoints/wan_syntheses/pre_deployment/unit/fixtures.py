from __future__ import annotations

import dataclasses
from typing import cast

from synthesizer.codec import OFF_NET_KIND, PROVIDER_KIND, SITE_KIND
from synthesizer.input_graph import FiberSegment, Site, SiteInfo, segment_key
from synthesizer.model import (
    KIND_ROADM,
    Homings,
    HomingSites,
    Synthesis,
    SynthesisArtifacts,
    SynthesisInputs,
    SynthesisMetrics,
    SynthesisParams,
    ForcedCircuits,
    OperatorCircuits,
    SynthesisCircuit,
    RoleExclusions,
    Tuning,
    ValidationReport,
)
from synthesizer.graphs import (
    biconnected_block_membership,
    build_adjacency,
    fiber_segments_along,
)
from synthesizer.search_plan import _SearchPlan
from synthesizer.synthesize import all_pairs_shortest, synthesize_two_tier
from synthesizer.overrides import apply_role_overrides
from synthesizer.stages import dual_home, finalize
from synthesizer.validation import diverse_circuit_count, validate_synthesis

RING_COORDS = {
    "P0": (40.0, -100.0),
    "P1": (41.0, -100.0),
    "P2": (41.5, -99.0),
    "P3": (41.0, -98.0),
    "P4": (40.0, -98.0),
    "P5": (39.5, -99.0),
}
SPUR_COORDS = {"P6": (37.0, -100.0)}
RING_SEGMENT_PAIRS = [
    ("P0", "P1"),
    ("P1", "P2"),
    ("P2", "P3"),
    ("P3", "P4"),
    ("P4", "P5"),
    ("P5", "P0"),
    ("P0", "P6"),
]
_FIXTURE_STATE = "XX"
_FIXTURE_COUNTRY = "United States"


def no_miles() -> SynthesisMetrics:
    return SynthesisMetrics(tenant_homing_miles=0.0, provider_homing_miles=0.0, physical_miles=0.0)


def carrier_pop(site_id: str, lat: float = 0.0, lon: float = 0.0) -> Site:
    return Site(
        id=site_id,
        name=site_id,
        kind="PoP",
        coords=(lat, lon),
        info=SiteInfo(
            municipality=site_id, state=_FIXTURE_STATE, country=_FIXTURE_COUNTRY
        ),
    )


def tenant_site(site_id: str, lat: float = 0.0, lon: float = 0.0) -> Site:
    return Site(id=site_id, name=site_id, kind=SITE_KIND, coords=(lat, lon))


def provider_region(site_id: str, lat: float = 0.0, lon: float = 0.0) -> Site:
    return Site(id=site_id, name=site_id, kind=PROVIDER_KIND, coords=(lat, lon))


def off_net_pop(site_id: str, lat: float = 0.0, lon: float = 0.0) -> Site:
    return Site(
        id=site_id,
        name=site_id,
        kind=OFF_NET_KIND,
        coords=(lat, lon),
        info=SiteInfo(
            municipality=site_id, state=_FIXTURE_STATE, country=_FIXTURE_COUNTRY
        ),
    )


def ring_sites() -> list[Site]:
    pops = [carrier_pop(n, lat, lon) for n, (lat, lon) in RING_COORDS.items()]
    pops += [carrier_pop(n, lat, lon) for n, (lat, lon) in SPUR_COORDS.items()]
    return pops


def ring_fiber_segments(distance: float = 100.0) -> dict[tuple[str, str], FiberSegment]:
    fiber: dict[tuple[str, str], FiberSegment] = {}
    for left, right in RING_SEGMENT_PAIRS:
        key = segment_key(left, right)
        fiber[key] = FiberSegment(source=key[0], target=key[1], distance_miles=distance)
    return fiber


SHARED_TRANSIT_WAN_POPS = ("a", "b", "c")
SHARED_TRANSIT_CIRCUITS = [("a", "x", "b"), ("a", "x", "c"), ("b", "c")]
DIVERSE_TRANSIT_CIRCUITS = [("a", "x", "b"), ("a", "y", "c"), ("b", "c")]


def meshed_backbone_synthesis(
    circuits: list[tuple[str, ...]], wan_pop_ids: tuple[str, ...]
) -> Synthesis:
    return Synthesis(
        wan_pop_ids=wan_pop_ids,
        transit_ids=(),
        homings=Homings([], []),
        fiber_segment_keys={
            key for pop_ids in circuits for key in fiber_segments_along(pop_ids)
        },
        drawn_circuits=[
            SynthesisCircuit("backbone_mesh", pop_ids[0], pop_ids[-1], pop_ids, 1.0)
            for pop_ids in circuits
        ],
        metrics=no_miles(),
    )


SHORT_OF_THREE_CITIES = "abcd"
SHORT_OF_THREE_WAN_POPS = ("a", "b", "c", "d")
SHORT_OF_THREE_CIRCUITS: list[tuple[str, ...]] = [
    ("a", "b"), ("a", "c"), ("b", "c"), ("b", "d"), ("c", "d"),
]


SPLIT_AT_TRANSIT_CITIES = "abcxy"
SPLIT_AT_TRANSIT_SEGMENTS = {
    ("a", "x"): 1.0,
    ("x", "b"): 1.0,
    ("x", "c"): 1.0,
    ("b", "c"): 1.0,
    ("a", "y"): 1.0,
    ("y", "c"): 1.0,
}


SPLIT_WAN_POPS = ("a", "b", "c", "d")
SPLIT_BACKBONE_CITIES = "abcdt"
SPLIT_BACKBONE_SEGMENTS = {("a", "t"): 50.0, ("t", "b"): 50.0, ("c", "d"): 100.0}
SPLIT_BACKBONE_CIRCUITS: list[tuple[str, ...]] = [("a", "t", "b"), ("c", "d")]


def split_backbone_synthesis() -> Synthesis:
    return meshed_backbone_synthesis(SPLIT_BACKBONE_CIRCUITS, SPLIT_WAN_POPS)


def carrier_pops_in_a_column() -> list[Site]:
    return [
        carrier_pop("P0", 0.0, 0.0),
        carrier_pop("P1", 0.0, 1.0),
        carrier_pop("P2", 0.0, 2.0),
    ]


def carrier_pops_by_id(site_ids: str) -> dict[str, Site]:
    return {site_id: carrier_pop(site_id) for site_id in site_ids}


def fiber_segments_from(
    pairs: dict[tuple[str, str], float],
) -> dict[tuple[str, str], FiberSegment]:
    fiber: dict[tuple[str, str], FiberSegment] = {}
    for (left, right), dist in pairs.items():
        key = segment_key(left, right)
        fiber[key] = FiberSegment(source=key[0], target=key[1], distance_miles=dist)
    return fiber


def fiber_segments_under_water(
    pairs: dict[tuple[str, str], float], under_water: set[tuple[str, str]]
) -> dict[tuple[str, str], FiberSegment]:
    keys = {segment_key(left, right) for left, right in under_water}
    return {
        key: dataclasses.replace(segment, submarine=key in keys)
        for key, segment in fiber_segments_from(pairs).items()
    }


def carrier_fiber_segments(
    pairs: dict[tuple[str, str], tuple[float, tuple[str, ...]]],
) -> dict[tuple[str, str], FiberSegment]:
    fiber: dict[tuple[str, str], FiberSegment] = {}
    for (left, right), (dist, carriers) in pairs.items():
        key = segment_key(left, right)
        fiber[key] = FiberSegment(
            source=key[0], target=key[1], distance_miles=dist,
            carriers=frozenset(carriers),
        )
    return fiber


def ring_params() -> SynthesisParams:
    return SynthesisParams(min_wan_pop_count=2)


def forced_off_net_case() -> tuple[Site, SynthesisParams]:
    site = off_net_pop("Dulles Hub", 40.5, -100.0)
    params = SynthesisParams(
        min_wan_pop_count=2,
        forced_wan_pop_names=("Dulles Hub",),
    )
    return site, params


RingInputs = tuple[list[Site], dict[tuple[str, str], FiberSegment]]


def _ring_inputs() -> RingInputs:
    return ring_sites(), ring_fiber_segments()


def run_synthesis(
    sites: list[Site],
    fiber_segments: dict[tuple[str, str], FiberSegment],
    params: SynthesisParams,
    off_net_pops: list[Site] | None = None,
) -> SynthesisArtifacts:
    homed = dual_home(sites, fiber_segments, params, off_net_pops or [])
    sites, fiber_segments, overrides = apply_role_overrides(
        homed.sites, homed.fiber_segments, params
    )
    synthesis = synthesize_two_tier(sites, fiber_segments, params, overrides)
    sites, fiber_segments, synthesis, validation = finalize(
        sites, fiber_segments, synthesis, params, overrides.degree_exempt_wan_pop_ids
    )
    return SynthesisArtifacts(
        sites, fiber_segments, synthesis, validation, homed.fabricated_ids
    )


def mesh_circuits(artifacts: SynthesisArtifacts) -> list[SynthesisCircuit]:
    return [
        drawn_circuit
        for drawn_circuit in artifacts.synthesis.drawn_circuits
        if drawn_circuit.purpose == "backbone_mesh"
    ]


def reasons_past_the_number(validation: ValidationReport) -> set[str]:
    return {
        str(unrequested["reason"])
        for entry in validation["backbone_diverse_circuits_above_target"]
        for unrequested in cast(list[dict[str, object]], entry["unrequested_links"])
    }


def synthesis_over_segments(
    site_ids: tuple[str, ...],
    segments: dict[tuple[str, str], float],
    number_of_diverse_circuits: int,
    transit_ids: tuple[str, ...] = (),
) -> SynthesisArtifacts:
    return synthesis_over_fiber(
        site_ids, fiber_segments_from(segments), number_of_diverse_circuits, transit_ids
    )


def synthesis_over_owned_fiber(
    site_ids: tuple[str, ...],
    segments: dict[tuple[str, str], tuple[float, tuple[str, ...]]],
    number_of_diverse_circuits: int,
    transit_ids: tuple[str, ...] = (),
) -> SynthesisArtifacts:
    return synthesis_over_fiber(
        site_ids, carrier_fiber_segments(segments), number_of_diverse_circuits, transit_ids,
    )


def synthesis_over_fiber(
    site_ids: tuple[str, ...],
    fiber: dict[tuple[str, str], FiberSegment],
    number_of_diverse_circuits: int,
    transit_ids: tuple[str, ...] = (),
) -> SynthesisArtifacts:
    cities = site_ids + transit_ids
    fewest = len(site_ids)
    return run_synthesis(
        [
            carrier_pop(city, 38.0, -115.0 + 2.0 * index)
            for index, city in enumerate(cities)
        ],
        fiber,
        SynthesisParams(
            min_wan_pop_count=fewest,
            max_wan_pop_count=len(site_ids),
            forced_wan_pop_names=site_ids,
            promote_high_degree_convergences=False,
            tuning=Tuning(
                backbone_number_of_diverse_circuits=number_of_diverse_circuits,
                homing_degree=homing_degree,
            ),
        ),
    )


def ring_artifacts() -> SynthesisArtifacts:
    sites, fiber = _ring_inputs()
    synthesis = synthesize_two_tier(sites, fiber, ring_params())
    return SynthesisArtifacts(
        sites, fiber, synthesis, validate_synthesis(sites, synthesis), frozenset()
    )


def ring_inputs_with_roadm(roadm_id: str) -> RingInputs:
    sites, fiber = _ring_inputs()
    sites = [
        dataclasses.replace(site, kind=KIND_ROADM) if site.id == roadm_id else site
        for site in sites
    ]
    return sites, fiber


def _forced_artifacts(
    params: SynthesisParams,
    inputs: RingInputs | None = None,
    circuits: OperatorCircuits = OperatorCircuits(),
) -> SynthesisArtifacts:
    sites, fiber_segments = inputs if inputs is not None else _ring_inputs()
    sites, fiber_segments, overrides = apply_role_overrides(
        sites, fiber_segments, params, circuits
    )
    synthesis = synthesize_two_tier(sites, fiber_segments, params, overrides)
    sites, fiber_segments, synthesis, validation = finalize(
        sites, fiber_segments, synthesis, params, overrides.degree_exempt_wan_pop_ids
    )
    return SynthesisArtifacts(sites, fiber_segments, synthesis, validation, frozenset())


def forced_wan_pop_artifacts(name: str) -> SynthesisArtifacts:
    return _forced_artifacts(
        SynthesisParams(
            min_wan_pop_count=2,
            forced_wan_pop_names=(name,),
        )
    )


def forced_roadm_wan_pop_artifacts(name: str) -> SynthesisArtifacts:
    params = SynthesisParams(
        min_wan_pop_count=2,
        forced_wan_pop_names=(name,),
    )
    return _forced_artifacts(params, ring_inputs_with_roadm(name))


def prohibited_wan_pop_artifacts(name: str) -> SynthesisArtifacts:
    return _forced_artifacts(
        SynthesisParams(
            min_wan_pop_count=2,
            exclusions=RoleExclusions(prohibited_wan_pop_names=(name,)),
        )
    )


def ring_inputs_with_demand(access_id: str, at_pop: str) -> RingInputs:
    sites, fiber = _ring_inputs()
    return [*sites, tenant_site(access_id, *RING_COORDS[at_pop])], fiber


def forced_circuit_artifacts(
    params: SynthesisParams, circuits: OperatorCircuits, inputs: RingInputs | None = None
) -> SynthesisArtifacts:
    return _forced_artifacts(params, inputs, circuits)


_HUB_CORNERS = ("hub_b0", "hub_b1", "hub_b2", "hub_b3")
_HUB_CENTER = "hub_dc"
_HUB_COORDS = {
    "hub_b0": (1.0, 0.0),
    "hub_b1": (0.0, 1.0),
    "hub_b2": (-1.0, 0.0),
    "hub_b3": (0.0, -1.0),
    "hub_dc": (0.0, 0.0),
}


def convergence_hub_inputs() -> RingInputs:
    pops = [carrier_pop(n, *_HUB_COORDS[n]) for n in (*_HUB_CORNERS, _HUB_CENTER)]
    spokes = {(_HUB_CENTER, corner): 1.0 for corner in _HUB_CORNERS}
    ring = {
        (_HUB_CORNERS[i], _HUB_CORNERS[(i + 1) % 4]): 1.5 for i in range(4)
    }
    return pops, fiber_segments_from({**spokes, **ring})


def convergence_hub_artifacts(
    max_wan_pop_count: int | None = None,
    promote_convergences: bool = True,
) -> SynthesisArtifacts:
    sites, fiber = convergence_hub_inputs()
    params = SynthesisParams(
        min_wan_pop_count=2,
        max_wan_pop_count=max_wan_pop_count,
        forced_wan_pop_names=_HUB_CORNERS,
        promote_high_degree_convergences=promote_convergences,
    )
    sites, fiber, overrides = apply_role_overrides(sites, fiber, params)
    synthesis = synthesize_two_tier(sites, fiber, params, overrides)
    return SynthesisArtifacts(
        sites, fiber, synthesis, validate_synthesis(sites, synthesis), frozenset()
    )


def synthesis_inputs_from_fiber(
    site_ids: list[str],
    fiber_segments: dict[tuple[str, str], FiberSegment],
    eligible: set[str],
    tenant_sites: list[Site] | None = None,
    coords: dict[str, tuple[float, float]] | None = None,
) -> SynthesisInputs:
    places = coords or {}
    pops = [carrier_pop(site_id, *places.get(site_id, (0.0, 0.0))) for site_id in site_ids]
    adjacency = build_adjacency(fiber_segments)
    paths = all_pairs_shortest(pops, adjacency)
    return SynthesisInputs(
        homing_sites=HomingSites(tenant_sites if tenant_sites is not None else [], []),
        carrier_pops=pops,
        fiber_segments=fiber_segments,
        eligible_wan_pop_ids=eligible,
        adjacency=adjacency,
        paths=paths,
        carrier_blocks=biconnected_block_membership(adjacency),
    )


def search_plan(
    candidates: list[str],
    strength: dict[str, float] | None = None,
    homing_degree: int = 2,
    forced_circuits: ForcedCircuits | None = None,
) -> _SearchPlan:
    strength_by_id = strength if strength is not None else {name: 1.0 for name in candidates}
    return _SearchPlan(
        candidates,
        strength_by_id,
        tuning=Tuning(homing_degree=homing_degree),
        forced_circuits=forced_circuits or ForcedCircuits(),
    )


TRIANGLE = fiber_segments_from({("a", "b"): 1.0, ("b", "c"): 1.0, ("a", "c"): 1.0})


FUNNEL_FIBER = fiber_segments_from({
    ("funnel", "east_a"): 40.0,
    ("funnel", "east_b"): 45.0,
    ("funnel", "east_c"): 50.0,
    ("funnel", "east_d"): 55.0,
    ("funnel", "west_a"): 60.0,
    ("east_a", "choke_east"): 40.0,
    ("east_b", "choke_east"): 45.0,
    ("east_c", "choke_east"): 50.0,
    ("east_d", "choke_east"): 55.0,
    ("west_a", "choke_west"): 60.0,
    ("second_funnel", "east_e"): 40.0,
    ("second_funnel", "east_f"): 45.0,
    ("second_funnel", "east_g"): 50.0,
    ("second_funnel", "east_h"): 55.0,
    ("second_funnel", "west_b"): 60.0,
    ("east_e", "choke_east"): 40.0,
    ("east_f", "choke_east"): 45.0,
    ("east_g", "choke_east"): 50.0,
    ("east_h", "choke_east"): 55.0,
    ("west_b", "choke_west"): 60.0,
    ("choke_east", "north"): 70.0,
    ("choke_east", "south"): 70.0,
    ("choke_west", "west"): 70.0,
    ("spread", "north"): 80.0,
    ("spread", "south"): 80.0,
    ("spread", "west"): 80.0,
})
FUNNEL_IDS = [
    "funnel", "second_funnel", "spread", "north", "south", "west",
    "east_a", "east_b", "east_c", "east_d", "west_a",
    "east_e", "east_f", "east_g", "east_h", "west_b",
    "choke_east", "choke_west",
]
FUNNEL_ELIGIBLE = {"funnel", "second_funnel", "spread", "north", "south", "west"}
FUNNEL_COORDS = {
    "funnel": (40.0, -100.0),
    "east_a": (40.0, -99.0), "east_b": (40.05, -99.0),
    "east_c": (39.95, -99.0), "east_d": (40.0, -98.9),
    "west_a": (40.0, -101.0),
    "second_funnel": (36.0, -100.0),
    "east_e": (36.0, -99.0), "east_f": (36.05, -99.0),
    "east_g": (35.95, -99.0), "east_h": (36.0, -98.9),
    "west_b": (36.0, -101.0),
    "choke_east": (38.0, -98.0), "choke_west": (38.0, -102.0),
    "north": (42.0, -108.0), "south": (34.0, -108.0), "west": (38.0, -110.0),
    "spread": (38.0, -108.0),
}


def funnel_sites() -> list[Site]:
    return [carrier_pop(site_id, *FUNNEL_COORDS[site_id]) for site_id in FUNNEL_IDS]


def funnel_transit_names() -> tuple[str, ...]:
    return tuple(sorted(set(FUNNEL_COORDS) - FUNNEL_ELIGIBLE))


CROSSING_SEGMENTS = {
    ("sea", "pdx"): 10.0, ("pdx", "hil"): 10.0, ("pdx", "eug"): 10.0,
    ("sea", "tok"): 1000.0, ("tok", "hil"): 1000.0, ("tok", "eug"): 1000.0,
}
CROSSING_FIBER = fiber_segments_from(CROSSING_SEGMENTS)
CROSSING_SUBMARINE_FIBER = fiber_segments_under_water(
    CROSSING_SEGMENTS, {("sea", "tok"), ("tok", "hil"), ("tok", "eug")}
)
CROSSING_IDS = ["sea", "hil", "eug", "pdx", "tok"]
CROSSING_ELIGIBLE = {"sea", "hil", "eug"}
CROSSING_COORDS = {
    "sea": (47.6, -122.3),
    "pdx": (45.5, -122.7),
    "hil": (45.5, -123.0),
    "eug": (44.0, -123.1),
    "tok": (35.7, 139.7),
}


def crossing_sites() -> list[Site]:
    return [carrier_pop(site_id, *CROSSING_COORDS[site_id]) for site_id in CROSSING_IDS]


def crossing_transit_names() -> tuple[str, ...]:
    return tuple(sorted(set(CROSSING_COORDS) - CROSSING_ELIGIBLE))


SHARED_HUB_SEGMENTS = {
    ("a", "h1"): 400.0, ("a", "h2"): 100.0, ("a", "h3"): 800.0,
    ("b", "h1"): 100.0, ("b", "h2"): 800.0, ("b", "h3"): 200.0,
    ("c", "h1"): 100.0, ("c", "h2"): 200.0, ("c", "h3"): 300.0,
}
SHARED_HUB_PEER_FIBER = fiber_segments_from({
    **SHARED_HUB_SEGMENTS,
    ("b", "d1"): 100.0, ("d1", "d"): 300.0,
    ("c", "d2"): 100.0, ("d2", "d"): 300.0,
})
SHARED_HUB_PEER_SITES = ("a", "b", "c", "d")
SHARED_HUB_PEER_IDS = ("a", "b", "c", "d", "h1", "h2", "h3", "d1", "d2")


def shared_hub_peer_sites() -> list[Site]:
    return [
        carrier_pop(site_id, 38.0, -115.0 + 2.0 * index)
        for index, site_id in enumerate(SHARED_HUB_PEER_IDS)
    ]


def shared_hub_peer_transit_names() -> tuple[str, ...]:
    return tuple(sorted(set(SHARED_HUB_PEER_IDS) - set(SHARED_HUB_PEER_SITES)))


def shared_hub_peer_artifacts(asked_for: int = 2) -> SynthesisArtifacts:
    return run_synthesis(
        shared_hub_peer_sites(),
        SHARED_HUB_PEER_FIBER,
        SynthesisParams(
            min_wan_pop_count=len(SHARED_HUB_PEER_SITES),
            max_wan_pop_count=len(SHARED_HUB_PEER_SITES),
            forced_wan_pop_names=SHARED_HUB_PEER_SITES,
            exclusions=RoleExclusions(
                prohibited_wan_pop_names=shared_hub_peer_transit_names()
            ),
            promote_high_degree_convergences=False,
            tuning=Tuning(backbone_number_of_diverse_circuits=asked_for),
        ),
    )


DISTANT_PEER_FIBER = fiber_segments_from({
    ("sea", "pdx"): 10.0,
    ("pdx", "hil"): 10.0,
    ("sea", "tok"): 1000.0,
    ("tok", "hil"): 1000.0,
    ("pdx", "syd"): 7000.0,
    ("hil", "syd"): 7000.0,
})
DISTANT_PEER_IDS = ["sea", "hil", "syd", "pdx", "tok"]
DISTANT_PEER_ELIGIBLE = {"sea", "hil", "syd"}
DISTANT_PEER_COORDS = {
    "sea": (47.6, -122.3),
    "pdx": (45.5, -122.7),
    "hil": (45.5, -123.0),
    "syd": (-33.9, 151.2),
    "tok": (35.7, 139.7),
}


def distant_peer_sites() -> list[Site]:
    return [
        carrier_pop(site_id, *DISTANT_PEER_COORDS[site_id])
        for site_id in DISTANT_PEER_IDS
    ]


def distant_peer_transit_names() -> tuple[str, ...]:
    return tuple(sorted(set(DISTANT_PEER_COORDS) - DISTANT_PEER_ELIGIBLE))


EXPRESS_FIBER = fiber_segments_from({
    ("sea", "pdx"): 1.0,
    ("pdx", "hil"): 1.0,
    ("hil", "alb"): 1.0,
    ("alb", "eug"): 1.0,
    ("eug", "tac"): 1.0,
    ("tac", "sea"): 1.0,
    ("sea", "hil"): 5.0,
    ("hil", "eug"): 5.0,
    ("eug", "sea"): 5.0,
})
EXPRESS_IDS = ["sea", "hil", "eug", "pdx", "alb", "tac"]
EXPRESS_ELIGIBLE = {"sea", "hil", "eug"}
EXPRESS_COORDS = {
    "sea": (47.6, -122.3),
    "pdx": (45.5, -122.7),
    "hil": (45.5, -123.0),
    "alb": (44.6, -123.1),
    "eug": (44.0, -123.1),
    "tac": (46.0, -122.9),
}


def express_sites() -> list[Site]:
    return [carrier_pop(site_id, *EXPRESS_COORDS[site_id]) for site_id in EXPRESS_IDS]


def express_transit_names() -> tuple[str, ...]:
    return tuple(sorted(set(EXPRESS_COORDS) - EXPRESS_ELIGIBLE))


def funnel_inputs() -> SynthesisInputs:
    return synthesis_inputs_from_fiber(
        FUNNEL_IDS, FUNNEL_FIBER, set(FUNNEL_ELIGIBLE), coords=FUNNEL_COORDS
    )


TWO_POCKET_FIBER = fiber_segments_from(
    {
        ("a", "b"): 1.0, ("b", "c"): 1.0, ("a", "c"): 1.0, ("c", "d"): 1.0,
        ("d", "e"): 1.0, ("e", "f"): 1.0, ("d", "f"): 1.0,
    }
)
TWO_POCKET_IDS = ["a", "b", "c", "d", "e", "f"]


MANY_PASS_SEGMENTS = {
    ("a", "c"): 32.0, ("a", "e"): 22.0, ("a", "f"): 18.0, ("a", "g"): 25.0,
    ("b", "c"): 36.0, ("b", "h"): 30.0, ("b", "i"): 22.0,
    ("c", "e"): 22.0, ("c", "h"): 7.0, ("c", "i"): 25.0, ("c", "j"): 28.0,
    ("d", "f"): 36.0, ("d", "j"): 22.0, ("d", "k"): 7.0, ("d", "l"): 11.0,
    ("e", "f"): 39.0, ("e", "g"): 25.0, ("e", "h"): 21.0, ("e", "i"): 25.0,
    ("f", "j"): 25.0, ("f", "k"): 34.0,
    ("h", "i"): 18.0, ("h", "j"): 35.0,
    ("j", "k"): 16.0, ("j", "l"): 32.0,
    ("k", "l"): 18.0,
}
MANY_PASS_SITES = ("c", "d", "j", "k", "l")
MANY_PASS_TRANSIT = ("a", "b", "e", "f", "g", "h", "i")
MANY_PASS_MILES = 159.0


OFFERED_WAYS_SITES = ("a", "b")
OFFERED_WAYS_TRANSIT = ("p", "q", "r")
OFFERED_WAYS_SEGMENTS: dict[tuple[str, str], tuple[float, tuple[str, ...]]] = {
    ("a", "p"): (1.0, ("zayo",)),
    ("b", "p"): (1.0, ("lumen",)),
    ("a", "q"): (1.0, ("zayo",)),
    ("b", "q"): (1.0, ("lumen",)),
    ("a", "r"): (2.5, ("lumen",)),
    ("b", "r"): (2.5, ("lumen",)),
}
OFFERED_WAYS_FIBER = carrier_fiber_segments(OFFERED_WAYS_SEGMENTS)

SHARED_TRANSIT_SITES = ("a", "b")
SHARED_TRANSIT_TRANSIT = ("m", "x", "y")
SHARED_TRANSIT_SEGMENTS: dict[tuple[str, str], tuple[float, tuple[str, ...]]] = {
    ("a", "m"): (10.0, ("lumen", "zayo")),
    ("b", "m"): (10.0, ("lumen", "zayo")),
    ("a", "x"): (50.0, ("zayo",)),
    ("b", "x"): (50.0, ("zayo",)),
    ("a", "y"): (60.0, ("lumen",)),
    ("b", "y"): (60.0, ("lumen",)),
}
SHARED_TRANSIT_FIBER = carrier_fiber_segments(SHARED_TRANSIT_SEGMENTS)
SHARED_TRANSIT_MILES = 120.0

ALREADY_NEEDED_SITES = ("b", "d", "f")
ALREADY_NEEDED_SEGMENTS: dict[tuple[str, str], tuple[float, tuple[str, ...]]] = {
    ("b", "c"): (16.0, ("cogent", "zayo")),
    ("b", "e"): (37.0, ("lumen", "zayo")),
    ("c", "d"): (34.0, ("lumen", "zayo")),
    ("c", "f"): (34.0, ("cogent", "lumen")),
    ("e", "f"): (16.0, ("cogent", "lumen")),
}
ALREADY_NEEDED_FIBER = carrier_fiber_segments(ALREADY_NEEDED_SEGMENTS)
ALREADY_NEEDED_MILES = 137.0
THE_SEGMENT_ONLY_A_SECOND_CIRCUIT_NEEDS = frozenset({("c", "f")})

FLOORED_ABOVE_SITES = ("b", "d", "e", "f")
FLOORED_ABOVE_TRANSIT = ("a", "c")
FLOORED_ABOVE_SEGMENTS: dict[tuple[str, str], tuple[float, tuple[str, ...]]] = {
    ("a", "d"): (56.0, ("lumen", "zayo")),
    ("a", "f"): (11.0, ("cogent", "zayo")),
    ("b", "d"): (33.0, ("cogent", "lumen")),
    ("b", "e"): (19.0, ("zayo",)),
    ("b", "f"): (47.0, ("cogent", "zayo")),
    ("c", "f"): (54.0, ("cogent", "lumen")),
    ("d", "f"): (16.0, ("cogent", "zayo")),
    ("e", "f"): (16.0, ("lumen", "zayo")),
}
FLOORED_ABOVE_MILES = 84.0

NEARER_PEER_SITES = ("s", "a", "b", "c", "d", "e")
NEARER_PEER_SEGMENTS = {
    ("s", "a"): 100.0, ("s", "b"): 100.0, ("s", "c"): 120.0, ("s", "d"): 130.0,
    ("a", "c"): 10.0, ("a", "d"): 10.0, ("a", "e"): 10.0,
    ("b", "c"): 10.0, ("b", "d"): 10.0, ("b", "e"): 10.0,
    ("c", "e"): 10.0,
}
NEARER_PEER_FIBER = fiber_segments_from(NEARER_PEER_SEGMENTS)
NEARER_PEER_CIRCUITS = 3
NEARER_PEER_MILES = 400.0

TWO_WAYS_TO_ONE_PEER_SEGMENTS = {
    ("a", "p"): 1.0, ("b", "p"): 1.0, ("a", "q"): 1.0, ("b", "q"): 1.0, ("b", "c"): 1.0,
}
TWO_WAYS_TO_ONE_PEER_WAN_POPS = ("a", "b", "c")
TWO_WAYS_TO_ONE_PEER_CIRCUITS: list[tuple[str, ...]] = [("a", "p", "b"), ("a", "q", "b")]


def two_ways_to_one_peer_credited() -> int:
    return diverse_circuit_count(
        meshed_backbone_synthesis(
            TWO_WAYS_TO_ONE_PEER_CIRCUITS, TWO_WAYS_TO_ONE_PEER_WAN_POPS
        ).drawn_circuits,
        "a",
    )


SHORT_AND_LONG_SITES = ("s", "t", "u")
SHORT_AND_LONG_TRANSIT = ("far", "near")
SHORT_AND_LONG_SEGMENTS = {
    ("s", "t"): 10.0,
    ("t", "u"): 10.0,
    ("s", "near"): 100.0, ("near", "u"): 100.0,
    ("s", "far"): 1000.0, ("far", "u"): 1000.0,
}
SHORT_AND_LONG_FIBER = fiber_segments_from(SHORT_AND_LONG_SEGMENTS)
ONLY_LONG_SEGMENTS = {
    ("s", "t"): 10.0,
    ("t", "u"): 10.0,
    ("s", "far"): 1000.0, ("far", "u"): 1000.0,
}
ONLY_LONG_FIBER = fiber_segments_from(ONLY_LONG_SEGMENTS)
THE_LONG_CIRCUIT = frozenset({("far", "s"), ("far", "u")})
