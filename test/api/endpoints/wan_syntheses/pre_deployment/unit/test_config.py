from __future__ import annotations

from dataclasses import fields
from typing import Any

import pytest

from synthesizer.config import AppConfig, app_config_from_record, config_from_data
from synthesizer.model import NamedCircuit, OperatorCircuits


_REQUIRED_TUNING = {
    "backbone_number_of_diverse_circuits": 3,
    "homing_degree": 2,
    "backbone_coverage_target_miles": 600,
}


def _config(data: dict[str, Any]) -> AppConfig:
    merged = dict(data)
    merged["tuning"] = {**_REQUIRED_TUNING, **data.get("tuning", {})}
    synthesis = data.get("synthesis", {})
    if isinstance(synthesis, dict):
        merged["synthesis"] = {
            "promote_high_degree_convergences_to_wan_pops": True,
            **synthesis,
        }
    return config_from_data(merged)


def default_config() -> AppConfig:
    return _config({})


def test_default_min_wan_pop_count() -> None:
    assert default_config().params.min_wan_pop_count == 3


def test_default_has_no_forced_wan_pops() -> None:
    assert len(default_config().params.forced_wan_pop_names) == 0


def test_default_max_wan_pop_count_is_none() -> None:
    assert default_config().params.max_wan_pop_count is None


def test_config_holds_no_label() -> None:
    assert "label" not in {held.name for held in fields(AppConfig)}


def test_reads_min_wan_pop_count() -> None:
    assert _config({"synthesis": {"min_wan_pop_count": 5}}).params.min_wan_pop_count == 5


def test_reads_max_wan_pop_count() -> None:
    assert _config({"synthesis": {"max_wan_pop_count": 7}}).params.max_wan_pop_count == 7


def test_default_homing_degree() -> None:
    assert default_config().params.tuning.homing_degree == 2


def test_reads_homing_degree() -> None:
    assert _config(
        {"tuning": {"homing_degree": 3}}
    ).params.tuning.homing_degree == 3


def test_default_backbone_number_of_diverse_circuits_is_three() -> None:
    assert default_config().params.tuning.backbone_number_of_diverse_circuits == 3


def test_reads_backbone_number_of_diverse_circuits() -> None:
    assert _config(
        {"tuning": {"backbone_number_of_diverse_circuits": 4}}
    ).params.tuning.backbone_number_of_diverse_circuits == 4


def test_the_old_mesh_degree_key_is_refused() -> None:
    with pytest.raises(ValueError, match="backbone_number_of_diverse_circuits"):
        config_from_data({
            "synthesis": {
                    "promote_high_degree_convergences_to_wan_pops": True,
            },
            "tuning": {
                "backbone_mesh_degree": 3,
                "homing_degree": 2,
                "backbone_coverage_target_miles": 600,
            },
        })


def test_reads_forced_wan_pops() -> None:
    assert _config(
        {"synthesis": {"forced_wan_pops": ["Atlanta, GA"]}}
    ).params.forced_wan_pop_names == ("Atlanta, GA",)


def test_reads_degree_exempt_wan_pops() -> None:
    assert _config(
        {"synthesis": {"degree_exempt_wan_pops": ["San Jose, CA"]}}
    ).params.degree_exempt_wan_pop_names == ("San Jose, CA",)


def test_default_exempts_no_wan_pop_from_the_degree() -> None:
    assert len(default_config().params.degree_exempt_wan_pop_names) == 0


def test_degree_exempt_wan_pops_must_be_a_list() -> None:
    with pytest.raises(ValueError):
        _config({"synthesis": {"degree_exempt_wan_pops": "San Jose, CA"}})


def test_default_has_no_forced_circuits() -> None:
    assert len(default_config().operator_circuits.backbone) == 0


def test_reads_forced_circuits() -> None:
    pinned = {"source": "Dallas, TX", "target": "Denver, CO"}
    assert _config({"synthesis": {"forced_circuits": [pinned]}}).operator_circuits.backbone == (
        NamedCircuit("Dallas, TX", "Denver, CO"),
    )


def test_forced_circuits_must_be_a_list() -> None:
    with pytest.raises(ValueError):
        _config({"synthesis": {"forced_circuits": {"source": "A"}}})


def test_a_forced_circuit_must_be_a_mapping() -> None:
    with pytest.raises(ValueError):
        _config({"synthesis": {"forced_circuits": ["Dallas, TX"]}})


def test_a_forced_circuit_requires_a_source_and_target() -> None:
    with pytest.raises(ValueError):
        _config({"synthesis": {"forced_circuits": [{"source": "A"}]}})


def test_a_forced_circuit_ignores_a_leftover_type() -> None:
    pinned = {"source": "A", "target": "B", "type": "access-backbone"}
    assert _config({"synthesis": {"forced_circuits": [pinned]}}).operator_circuits.backbone == (
        NamedCircuit("A", "B"),
    )


def test_default_has_no_forced_homes() -> None:
    assert len(default_config().operator_circuits.homes) == 0


def test_reads_forced_homes() -> None:
    home = {"source": "Kirtland, NM", "target": "Denver, CO"}
    assert _config({"synthesis": {"forced_homes": [home]}}).operator_circuits.homes == (
        NamedCircuit("Kirtland, NM", "Denver, CO"),
    )


def test_forced_homes_must_be_a_list() -> None:
    with pytest.raises(ValueError):
        _config({"synthesis": {"forced_homes": {"source": "A"}}})


def test_a_forced_home_is_not_read_as_a_mesh_pair() -> None:
    home = {"source": "Kirtland, NM", "target": "Denver, CO"}
    assert len(_config({"synthesis": {"forced_homes": [home]}}).operator_circuits.backbone) == 0


def test_default_has_no_prohibited_circuits() -> None:
    assert len(default_config().operator_circuits.removed_backbone) == 0


def test_reads_prohibited_circuits() -> None:
    synthesis = {"prohibited_circuits": [{"source": "Seattle, WA", "target": "Boise, ID"}]}
    assert _config({"synthesis": synthesis}).operator_circuits.removed_backbone == (
        NamedCircuit("Seattle, WA", "Boise, ID"),
    )


def test_default_has_no_prohibited_wan_pops() -> None:
    assert len(default_config().params.exclusions.prohibited_wan_pop_names) == 0


def test_reads_promote_high_degree_convergences_true() -> None:
    assert _config(
        {"synthesis": {"promote_high_degree_convergences_to_wan_pops": True}}
    ).params.promote_high_degree_convergences is True


def test_reads_promote_high_degree_convergences_false() -> None:
    assert _config(
        {"synthesis": {"promote_high_degree_convergences_to_wan_pops": False}}
    ).params.promote_high_degree_convergences is False


def test_promote_high_degree_convergences_must_be_a_boolean() -> None:
    with pytest.raises(ValueError):
        _config({"synthesis": {"promote_high_degree_convergences_to_wan_pops": "yes"}})


def test_promote_high_degree_convergences_is_required() -> None:
    with pytest.raises(ValueError):
        config_from_data({"tuning": _REQUIRED_TUNING, "synthesis": {}})


def test_reads_prohibited_wan_pops() -> None:
    synthesis = {"prohibited_wan_pops": ["Denver, CO", "Boise, ID"]}
    assert _config({"synthesis": synthesis}).params.exclusions.prohibited_wan_pop_names == (
        "Denver, CO",
        "Boise, ID",
    )


def test_prohibited_wan_pops_must_be_a_list_of_strings() -> None:
    with pytest.raises(ValueError):
        _config({"synthesis": {"prohibited_wan_pops": "Denver, CO"}})


def test_reads_settings_compass_sector_count() -> None:
    tuning = _config({"settings": {"compass_sector_count": 6}}).params.tuning
    assert tuning.compass_sector_count == 6


def test_reads_tuning_coverage_target() -> None:
    assert _config(
        {"tuning": {"backbone_coverage_target_miles": 250}}
    ).params.tuning.backbone_coverage_target_miles == 250


def test_reads_settings_wan_pop_search_memory_share() -> None:
    assert _config(
        {"settings": {"wan_pop_search_memory_share": 0.3}}
    ).params.tuning.search_memory_budget.memory_share == 0.3


def test_reads_settings_bytes_per_combination() -> None:
    assert _config(
        {"settings": {"bytes_per_wan_pop_combination": 200}}
    ).params.tuning.search_memory_budget.bytes_per_combination == 200


@pytest.mark.parametrize("value", [0, -1, 8.0, True, "8"])
def test_rejects_a_compass_sector_count_that_is_not_a_positive_integer(
        value: object) -> None:
    with pytest.raises(ValueError, match="compass_sector_count"):
        _config({"settings": {"compass_sector_count": value}})


@pytest.mark.parametrize("value", [1.5, 0, 0.0, -0.1, True, "half"])
def test_rejects_a_memory_share_outside_zero_to_one(value: object) -> None:
    with pytest.raises(ValueError, match="wan_pop_search_memory_share"):
        _config({"settings": {"wan_pop_search_memory_share": value}})


def test_accepts_a_memory_share_of_exactly_one() -> None:
    parsed = _config({"settings": {"wan_pop_search_memory_share": 1}})
    budget = parsed.params.tuning.search_memory_budget
    assert budget.memory_share == 1.0


def test_rejects_a_settings_document_written_before_the_rename() -> None:
    with pytest.raises(ValueError, match="unknown keys"):
        _config({"settings": {"compass_octants": 8, "enum_memory_fraction": 0.6}})


def test_rejects_an_unrecognised_settings_key() -> None:
    with pytest.raises(ValueError, match="compass_sectors"):
        _config({"settings": {"compass_sectors": 8}})


def test_a_dial_left_in_the_tuning_section_is_not_read() -> None:
    assert _config({"tuning": {"compass_octants": 6}}).params.tuning.compass_sector_count == 8


def test_missing_required_degree_is_rejected() -> None:
    with pytest.raises(ValueError):
        config_from_data({
            "tuning": {
                "backbone_number_of_diverse_circuits": 3,
                "backbone_coverage_target_miles": 600,
            }
        })


def test_non_integer_degree_is_rejected() -> None:
    with pytest.raises(ValueError):
        config_from_data(
            {"tuning": {"backbone_number_of_diverse_circuits": "three", "homing_degree": 2}}
        )


def test_boolean_degree_is_rejected() -> None:
    with pytest.raises(ValueError):
        config_from_data(
            {"tuning": {"backbone_number_of_diverse_circuits": True, "homing_degree": 2}}
        )


def test_missing_coverage_target_is_rejected() -> None:
    with pytest.raises(ValueError):
        config_from_data(
            {
                "tuning": {"backbone_number_of_diverse_circuits": 3, "homing_degree": 2},
                "synthesis": {
                    "promote_high_degree_convergences_to_wan_pops": True
                },
            }
        )


def test_non_number_coverage_target_is_rejected() -> None:
    with pytest.raises(ValueError):
        _config({"tuning": {"backbone_coverage_target_miles": "far"}})


def test_a_config_naming_no_backup_path_multiple_loads() -> None:
    assert config_from_data(
        {
            "tuning": {
                "backbone_number_of_diverse_circuits": 3,
                "homing_degree": 2,
                "backbone_coverage_target_miles": 600,
            },
            "synthesis": {"promote_high_degree_convergences_to_wan_pops": True},
        }
    ).params.tuning.backbone_number_of_diverse_circuits == 3


def test_fractional_coverage_target_is_rejected() -> None:
    with pytest.raises(ValueError):
        _config({"tuning": {"backbone_coverage_target_miles": 400.5}})


def test_section_must_be_a_mapping() -> None:
    with pytest.raises(ValueError):
        _config({"synthesis": "not a mapping"})


def test_forced_wan_pops_must_be_a_list() -> None:
    with pytest.raises(ValueError):
        _config({"synthesis": {"forced_wan_pops": "Atlanta, GA"}})


def _record(**overrides: Any) -> dict[str, Any]:
    record: dict[str, Any] = {
        "label": "Minuteman",
        "wan_pop_count": {"min": 3, "max": 5},
        "backbone_number_of_diverse_circuits": 3,
        "homing_degree": 2,
        "convergence_promotion": True,
        "knobs": {"backbone_coverage_target_miles": 600},
        "settings": {},
        "status": "creating",
    }
    record.update(overrides)
    return record


def _from_record(record: dict[str, Any], **lists: list[Any]) -> AppConfig:
    return app_config_from_record(record, lists)


def test_app_config_from_record_folds_settings_into_tuning() -> None:
    record = _record(settings={"wan_pop_search_memory_share": 0.25})
    budget = _from_record(record).params.tuning.search_memory_budget
    assert budget.memory_share == 0.25


def test_app_config_from_record_reads_every_dial_from_settings() -> None:
    record = _record(settings={
        "compass_sector_count": 4, "wan_pop_search_memory_share": 0.25,
        "bytes_per_wan_pop_combination": 320,
    })
    budget = _from_record(record).params.tuning.search_memory_budget
    assert (budget.memory_share, budget.bytes_per_combination) == (0.25, 320)


def test_app_config_from_record_ignores_a_dial_left_in_knobs() -> None:
    record = _record(knobs={"backbone_coverage_target_miles": 600, "compass_octants": 4})
    assert _from_record(record).params.tuning.compass_sector_count == 8


def test_app_config_from_record_without_settings_is_unchanged() -> None:
    assert _from_record(_record()) == _from_record(_record(settings={}))


def test_app_config_from_record_assembles_the_two_degrees() -> None:
    tuning = _from_record(_record()).params.tuning
    assert (tuning.backbone_number_of_diverse_circuits, tuning.homing_degree) == (3, 2)


def test_app_config_from_record_leaves_the_label_and_the_status_unread() -> None:
    assert _from_record(_record(label="DAF", status="fail")) == _from_record(_record())


def test_app_config_from_record_reads_wan_pop_count() -> None:
    params = _from_record(_record()).params
    assert (params.min_wan_pop_count, params.max_wan_pop_count) == (3, 5)


def test_app_config_from_record_reads_forced_wan_pops() -> None:
    params = _from_record(_record(), forced_wan_pops=["Denver, CO"]).params
    assert params.forced_wan_pop_names == ("Denver, CO",)


def test_app_config_from_record_reads_the_degree_exempt_wan_pops() -> None:
    params = _from_record(_record(), degree_exempt_wan_pops=["San Jose, CA"]).params
    assert params.degree_exempt_wan_pop_names == ("San Jose, CA",)


def test_app_config_from_record_exempts_nobody_without_the_list() -> None:
    params = _from_record(_record()).params
    assert len(params.degree_exempt_wan_pop_names) == 0


def test_app_config_from_record_requires_each_degree() -> None:
    record = _record()
    del record["homing_degree"]
    with pytest.raises(ValueError):
        _from_record(record)


def test_app_config_from_record_requires_coverage_target() -> None:
    with pytest.raises(ValueError):
        _from_record(_record(knobs={}))


def test_app_config_from_record_rejects_a_non_integer_degree() -> None:
    with pytest.raises(ValueError):
        _from_record(_record(backbone_number_of_diverse_circuits="three"))


def test_app_config_from_record_defaults_count_when_absent() -> None:
    params = _from_record(_record(wan_pop_count={})).params
    assert (params.min_wan_pop_count, params.max_wan_pop_count) == (3, None)


def test_app_config_from_record_reads_only_min_when_max_absent() -> None:
    params = _from_record(_record(wan_pop_count={"min": 4})).params
    assert (params.min_wan_pop_count, params.max_wan_pop_count) == (4, None)


def test_app_config_from_record_reads_convergence_promotion() -> None:
    params = _from_record(_record(convergence_promotion=False)).params
    assert params.promote_high_degree_convergences is False


def test_app_config_from_record_requires_convergence_promotion() -> None:
    record = _record()
    del record["convergence_promotion"]
    with pytest.raises(ValueError):
        _from_record(record)


def test_app_config_from_record_parses_the_written_circuits() -> None:
    config = _from_record(
        _record(),
        forced_circuits=[{"source": "A", "target": "B"}],
        forced_homes=[{"source": "S", "target": "B"}],
        prohibited_circuits=[{"source": "C", "target": "D"}],
    )
    assert config.operator_circuits == OperatorCircuits(
        backbone=(NamedCircuit("A", "B"),),
        homes=(NamedCircuit("S", "B"),),
        removed_backbone=(NamedCircuit("C", "D"),),
    )
