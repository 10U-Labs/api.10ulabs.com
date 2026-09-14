from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from synthesizer.model import (
    SynthesisParams,
    NamedCircuit,
    OperatorCircuits,
    RoleExclusions,
    SearchMemoryBudget,
    Tuning,
)

@dataclass(frozen=True)
class AppConfig:
    params: SynthesisParams
    operator_circuits: OperatorCircuits = field(default_factory=OperatorCircuits)


def _mapping(data: dict[str, Any], key: str) -> dict[str, Any]:
    section = data.get(key, {})
    if not isinstance(section, dict):
        raise ValueError(f"config section '{key}' must be a mapping")
    return section


def _str_list(data: dict[str, Any], key: str, default: list[str]) -> tuple[str, ...]:
    value = data.get(key, default)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"config key '{key}' must be a list of strings")
    return tuple(value)


def _required_bool(data: dict[str, Any], key: str) -> bool:
    if key not in data:
        raise ValueError(f"config key '{key}' is required and has no default")
    value = data[key]
    if not isinstance(value, bool):
        raise ValueError(f"config key '{key}' must be a boolean")
    return value


def _required_int(data: dict[str, Any], key: str) -> int:
    if key not in data:
        raise ValueError(f"config key '{key}' is required and has no default")
    value = data[key]
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"config key '{key}' must be an integer")
    return value


def _named_circuit_list(synthesis: dict[str, Any], key: str) -> tuple[NamedCircuit, ...]:
    value = synthesis.get(key, [])
    if not isinstance(value, list):
        raise ValueError(f"config key '{key}' must be a list")
    written: list[NamedCircuit] = []
    for item in value:
        if not isinstance(item, dict) or not all(
            isinstance(item.get(name), str) for name in ("source", "target")
        ):
            raise ValueError(f"each {key} entry must map source and target to strings")
        written.append(NamedCircuit(item["source"], item["target"]))
    return tuple(written)


def _operator_circuits(synthesis: dict[str, Any]) -> OperatorCircuits:
    return OperatorCircuits(
        backbone=_named_circuit_list(synthesis, "forced_circuits"),
        homes=_named_circuit_list(synthesis, "forced_homes"),
        removed_backbone=_named_circuit_list(synthesis, "prohibited_circuits"),
    )


SETTINGS_KEYS = frozenset({
    "wan_pop_search_memory_share",
    "bytes_per_wan_pop_combination",
    "compass_sector_count",
})


def _checked_settings(settings: dict[str, Any]) -> dict[str, Any]:
    unknown = sorted(set(settings) - SETTINGS_KEYS)
    if unknown:
        raise ValueError(
            f"settings resource carries unknown keys: {', '.join(unknown)}"
        )
    return settings


def _sector_count(settings: dict[str, Any], default: int) -> int:
    value = settings.get("compass_sector_count", default)
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError("settings key 'compass_sector_count' must be an integer of at least 1")
    return value


def _memory_share(settings: dict[str, Any], default: float) -> float:
    value = settings.get("wan_pop_search_memory_share", default)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("settings key 'wan_pop_search_memory_share' must be a number")
    if not 0.0 < value <= 1.0:
        raise ValueError(
            "settings key 'wan_pop_search_memory_share' must be above 0 and at most 1"
        )
    return float(value)


def _tuning(tuning: dict[str, Any], settings: dict[str, Any]) -> Tuning:
    base = Tuning()
    settings = _checked_settings(settings)
    return Tuning(
        compass_sector_count=_sector_count(settings, base.compass_sector_count),
        backbone_number_of_diverse_circuits=_required_int(
            tuning, "backbone_number_of_diverse_circuits"
        ),
        backbone_coverage_target_miles=_required_int(
            tuning, "backbone_coverage_target_miles"
        ),
        homing_degree=_required_int(tuning, "homing_degree"),
        search_memory_budget=SearchMemoryBudget(
            memory_share=_memory_share(settings, base.search_memory_budget.memory_share),
            bytes_per_combination=settings.get(
                "bytes_per_wan_pop_combination", base.search_memory_budget.bytes_per_combination
            ),
        ),
    )


def _params(
    synthesis: dict[str, Any], tuning: dict[str, Any], settings: dict[str, Any]
) -> SynthesisParams:
    base = SynthesisParams()
    return SynthesisParams(
        min_wan_pop_count=synthesis.get("min_wan_pop_count", base.min_wan_pop_count),
        max_wan_pop_count=synthesis.get("max_wan_pop_count", base.max_wan_pop_count),
        forced_wan_pop_names=_str_list(synthesis, "forced_wan_pops", []),
        degree_exempt_wan_pop_names=_str_list(synthesis, "degree_exempt_wan_pops", []),
        exclusions=RoleExclusions(
            prohibited_wan_pop_names=_str_list(synthesis, "prohibited_wan_pops", []),
        ),
        tuning=_tuning(tuning, settings),
        promote_high_degree_convergences=_required_bool(
            synthesis, "promote_high_degree_convergences_to_wan_pops"
        ),
    )


def config_from_data(data: dict[str, Any]) -> AppConfig:
    synthesis = _mapping(data, "synthesis")
    return AppConfig(
        params=_params(synthesis, _mapping(data, "tuning"), _mapping(data, "settings")),
        operator_circuits=_operator_circuits(synthesis),
    )


LIST_INPUTS = (
    "forced_wan_pops",
    "degree_exempt_wan_pops",
    "prohibited_wan_pops",
    "forced_circuits",
    "forced_homes",
    "prohibited_circuits",
)


def app_config_from_record(record: dict[str, Any], lists: dict[str, list[Any]]) -> AppConfig:
    count = _mapping(record, "wan_pop_count")
    synthesis: dict[str, Any] = {key: lists.get(key, []) for key in LIST_INPUTS}
    synthesis["promote_high_degree_convergences_to_wan_pops"] = _required_bool(
        record, "convergence_promotion"
    )
    if "min" in count:
        synthesis["min_wan_pop_count"] = count["min"]
    if "max" in count:
        synthesis["max_wan_pop_count"] = count["max"]
    tuning = {
        **_mapping(record, "knobs"),
        "backbone_number_of_diverse_circuits": _required_int(
            record, "backbone_number_of_diverse_circuits"
        ),
        "homing_degree": _required_int(record, "homing_degree"),
    }
    return config_from_data({
        "synthesis": synthesis,
        "tuning": tuning,
        "settings": _mapping(record, "settings"),
    })
