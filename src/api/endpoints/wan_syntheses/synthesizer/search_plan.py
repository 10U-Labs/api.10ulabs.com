from __future__ import annotations

from dataclasses import dataclass, field

from synthesizer.model import ForcedCircuits, Tuning


@dataclass(frozen=True)
class _SearchPlan:
    wan_pop_candidates: list[str]
    strength_by_id: dict[str, float]
    tuning: Tuning = field(default_factory=Tuning)
    forced_circuits: ForcedCircuits = field(default_factory=ForcedCircuits)

    @property
    def required_wan_pops(self) -> frozenset[str]:
        return self.forced_circuits.required_wan_pops
