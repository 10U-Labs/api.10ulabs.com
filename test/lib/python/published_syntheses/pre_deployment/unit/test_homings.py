from typing import Any, Dict

from published_syntheses import homed_counts, homing_miles_served


def _homing(kind: str, source_id: int, miles: float) -> Dict[str, Any]:
    return {"homing_kind": kind, "source_id": source_id, "target": 1, "distance_miles": miles}


HOMINGS: Dict[str, Any] = {"homings": [
    _homing("tenant_to_backbone", 1, 10.0),
    _homing("tenant_to_backbone", 1, 12.5),
    _homing("provider_to_backbone", 1, 100.0),
    _homing("tenant_to_backbone", 2, 3.0),
]}


def test_a_homing_is_counted_by_its_kind_and_its_source_s_id() -> None:
    assert homed_counts(HOMINGS) == {
        ("tenant_to_backbone", 1): 2, ("provider_to_backbone", 1): 1, ("tenant_to_backbone", 2): 1,
    }


def test_the_tenant_miles_are_the_sites_homings() -> None:
    assert homing_miles_served(HOMINGS, "tenant") == 25.5


def test_the_provider_miles_are_the_regions_homings() -> None:
    assert homing_miles_served(HOMINGS, "provider") == 100.0
