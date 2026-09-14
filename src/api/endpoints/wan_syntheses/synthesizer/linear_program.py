from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import highspy

_WHOLE = 1.0

_SOLVER: Any = highspy.Highs

_SECONDS_A_PASS_MAY_RUN = 1.0


@dataclass(frozen=True)
class SegmentRow:
    columns: tuple[int, ...]
    floor: float


@dataclass(frozen=True)
class SegmentProgram:
    miles: tuple[float, ...]
    selected: frozenset[int]
    rows: tuple[SegmentRow, ...]


@dataclass(frozen=True)
class SegmentSelection:
    miles: float
    held: tuple[float, ...]


def _model(program: SegmentProgram) -> Any:
    model: Any = highspy.HighsLp()
    model.num_col_ = len(program.miles)
    model.num_row_ = len(program.rows)
    model.col_cost_ = list(program.miles)
    model.col_lower_ = [
        _WHOLE if column in program.selected else 0.0 for column in range(len(program.miles))
    ]
    model.col_upper_ = [_WHOLE] * len(program.miles)
    model.row_lower_ = [row.floor for row in program.rows]
    model.row_upper_ = [highspy.kHighsInf] * len(program.rows)
    model.a_matrix_.format_ = highspy.MatrixFormat.kRowwise
    starts, indices = _matrix(program.rows)
    model.a_matrix_.start_ = starts
    model.a_matrix_.index_ = indices
    model.a_matrix_.value_ = [_WHOLE] * len(indices)
    return model


def _matrix(rows: tuple[SegmentRow, ...]) -> tuple[list[int], list[int]]:
    starts = [0]
    indices: list[int] = []
    for row in rows:
        indices.extend(row.columns)
        starts.append(len(indices))
    return starts, indices


def _quiet_solver(program: SegmentProgram) -> Any:
    solver: Any = _SOLVER()
    solver.setOptionValue("output_flag", False)
    solver.passModel(_model(program))
    return solver


def _answer(solver: Any) -> SegmentSelection:
    if solver.getModelStatus() != highspy.HighsModelStatus.kOptimal:
        raise ValueError(
            "No fiber holding meets every requirement asked of it; the requirements were "
            "not capped against the fiber that is actually there"
        )
    return SegmentSelection(
        float(solver.getObjectiveValue()),
        tuple(float(held) for held in solver.getSolution().col_value),
    )


def solve(program: SegmentProgram) -> SegmentSelection:
    solver = _quiet_solver(program)
    solver.run()
    return _answer(solver)


class GrowingSegmentProgram:
    def __init__(self, miles: tuple[float, ...]) -> None:
        self._solver = _quiet_solver(SegmentProgram(miles, frozenset(), ()))
        self._whole: set[int] = set()

    def add_rows(self, rows: tuple[SegmentRow, ...]) -> None:
        if not rows:
            return
        starts, indices = _matrix(rows)
        self._solver.addRows(
            len(rows),
            [row.floor for row in rows],
            [highspy.kHighsInf] * len(rows),
            len(indices),
            starts[:-1],
            indices,
            [_WHOLE] * len(indices),
        )

    def hold_whole(self, columns: frozenset[int]) -> None:
        for column in sorted(columns - self._whole):
            self._solver.changeColBounds(column, _WHOLE, _WHOLE)
        self._whole |= columns

    def solve(self) -> SegmentSelection:
        self._solver.setOptionValue(
            "time_limit", self._solver.getRunTime() + _SECONDS_A_PASS_MAY_RUN
        )
        self._solver.run()
        if self._solver.getModelStatus() == highspy.HighsModelStatus.kTimeLimit:
            self._solver.setOptionValue("time_limit", highspy.kHighsInf)
            self._solver.clearSolver()
            self._solver.run()
        return _answer(self._solver)
