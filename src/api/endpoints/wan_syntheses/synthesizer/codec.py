from __future__ import annotations

import re
from typing import Any

from synthesizer.input_graph import (
    CarrierPop,
    FiberSegment,
    OffNetPop,
    ProviderRegion,
    TenantSite,
    Vertex,
    VertexInfo,
    segment_key,
    haversine_miles,
)


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "x"


def _city(row: dict[str, Any]) -> str:
    region = row["state"] if row["country"] == "United States" else row["country"]
    return f"{row['municipality']}, {region}"


def _unique(base: str, used: set[str]) -> str:
    vertex_id = base
    suffix = 2
    while vertex_id in used:
        vertex_id = f"{base}-{suffix}"
        suffix += 1
    used.add(vertex_id)
    return vertex_id


def _vertex(row: dict[str, Any], vertex_id: str, name: str, kind: type[Vertex]) -> Vertex:
    return kind(
        id=vertex_id,
        name=name,
        coords=(float(row["latitude"]), float(row["longitude"])),
        info=VertexInfo(
            municipality=row["municipality"], state=row["state"], country=row["country"]
        ),
        exempt_from_distance_constraint=bool(row.get("exempt_from_distance_constraint")),
    )


def _load_vertices(
    rows: list[dict[str, Any]], prefix: str, kind: type[Vertex], named: bool
) -> list[Vertex]:
    used: set[str] = set()
    vertices: list[Vertex] = []
    for row in rows:
        name = row["name"] if named else _city(row)
        vertex_id = _unique(f"{prefix}-{_slug(name)}", used)
        vertices.append(_vertex(row, vertex_id, name, kind))
    return vertices


def load_regions(rows: list[dict[str, Any]]) -> list[Vertex]:
    return _load_vertices(rows, "provider", ProviderRegion, named=True)


def load_sites(rows: list[dict[str, Any]]) -> list[Vertex]:
    return _load_vertices(rows, "site", TenantSite, named=True)


def load_off_net(rows: list[dict[str, Any]]) -> list[Vertex]:
    return _load_vertices(rows, "offnet", OffNetPop, named=False)


def load_merged_carriers(
    pop_rows: list[dict[str, Any]], segment_rows: list[dict[str, Any]]
) -> tuple[list[Vertex], dict[tuple[str, str], FiberSegment]]:
    used: set[str] = set()
    pops: list[Vertex] = []
    by_city: dict[tuple[str, str], Vertex] = {}
    for row in pop_rows:
        city = (row["municipality"], row["state"])
        if city in by_city:
            continue
        name = _city(row)
        pop = _vertex(row, _unique(_slug(name), used), name, CarrierPop)
        pops.append(pop)
        by_city[city] = pop
    fiber_segments: dict[tuple[str, str], FiberSegment] = {}
    owners_by_key: dict[tuple[str, str], set[str]] = {}
    connected: set[str] = set()
    for row in segment_rows:
        source = by_city.get((row["a_municipality"], row["a_state"]))
        target = by_city.get((row["z_municipality"], row["z_state"]))
        if source is None or target is None or source.id == target.id:
            continue
        key = segment_key(source.id, target.id)
        if row.get("carrier"):
            owners_by_key.setdefault(key, set()).add(str(row["carrier"]))
        fiber_segments[key] = FiberSegment(
            source=key[0], target=key[1], distance_miles=haversine_miles(source, target),
            carriers=frozenset(owners_by_key.get(key, ())),
            submarine=bool(row.get("submarine")) or (
                key in fiber_segments and fiber_segments[key].submarine
            ),
        )
        connected.update(key)
    pops = [pop for pop in by_city.values() if pop.id in connected]
    return pops, fiber_segments
