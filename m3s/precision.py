"""Precision selection utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, NamedTuple

from .core.types import Bbox
from .systems import get as get_system
from .units import detect_area, parse_area, parse_length


@dataclass(frozen=True, slots=True)
class Location:
    lat: float
    lon: float


@dataclass(frozen=True, slots=True)
class PrecisionTarget:
    kind: Literal["size", "area", "cells"]
    value: float

    @staticmethod
    def size(value: str | float) -> "PrecisionTarget":
        if isinstance(value, str):
            meters = parse_length(value)
        else:
            meters = float(value)
        return PrecisionTarget("size", meters)

    @staticmethod
    def area(value: str | float) -> "PrecisionTarget":
        if isinstance(value, str):
            km2 = parse_area(value)
        else:
            km2 = float(value)
        return PrecisionTarget("area", km2)

    @staticmethod
    def max_cells(value: int) -> "PrecisionTarget":
        return PrecisionTarget("cells", float(value))


@dataclass(slots=True)
class PrecisionConstraints:
    max_size_m: float | None = None
    max_area_km2: float | None = None
    max_cells: int | None = None
    bbox: Bbox | None = None


class PrecisionChoice(NamedTuple):
    precision: int
    metrics: dict[str, float]
    score: float
    rationale: str


def _parse_target(target: PrecisionTarget | str | float | None) -> PrecisionTarget:
    if target is None:
        return PrecisionTarget.size("1km")
    if isinstance(target, PrecisionTarget):
        return target
    if isinstance(target, (int, float)):
        return PrecisionTarget.size(float(target))
    if detect_area(target):
        return PrecisionTarget.area(target)
    return PrecisionTarget.size(target)


def _target_metric_name(target: PrecisionTarget) -> str:
    if target.kind == "area":
        return "area_km2"
    if target.kind == "cells":
        return "cells"
    return "size_m"


def _score_closest_under(values: list[tuple[int, dict[str, float]]], metric: str, target: float) -> PrecisionChoice:
    eligible = [(p, m) for p, m in values if m[metric] <= target]
    if eligible:
        precision, metrics = max(eligible, key=lambda item: item[1][metric])
        score = 1.0 - abs(metrics[metric] - target) / max(target, 1e-9)
        return PrecisionChoice(precision, metrics, score, "closest_under")
    precision, metrics = min(values, key=lambda item: abs(item[1][metric] - target))
    score = 1.0 - abs(metrics[metric] - target) / max(target, 1e-9)
    return PrecisionChoice(precision, metrics, score, "closest_under_fallback")


def _score_closest_over(values: list[tuple[int, dict[str, float]]], metric: str, target: float) -> PrecisionChoice:
    eligible = [(p, m) for p, m in values if m[metric] >= target]
    if eligible:
        precision, metrics = min(eligible, key=lambda item: item[1][metric])
        score = 1.0 - abs(metrics[metric] - target) / max(target, 1e-9)
        return PrecisionChoice(precision, metrics, score, "closest_over")
    precision, metrics = min(values, key=lambda item: abs(item[1][metric] - target))
    score = 1.0 - abs(metrics[metric] - target) / max(target, 1e-9)
    return PrecisionChoice(precision, metrics, score, "closest_over_fallback")


def _score_min_cells(values: list[tuple[int, dict[str, float]]]) -> PrecisionChoice:
    precision, metrics = min(values, key=lambda item: item[1].get("cells", float("inf")))
    return PrecisionChoice(precision, metrics, 1.0, "min_cells")


def best(
    system: str,
    target: PrecisionTarget | str | float | None = None,
    constraints: PrecisionConstraints | None = None,
    at: Location | None = None,
    policy: Literal["closest_under", "closest_over", "min_cells", "balanced"] = "closest_under",
    weights: dict[str, float] | None = None,
) -> PrecisionChoice:
    spec = get_system(system)
    target_spec = _parse_target(target)
    metric_name = _target_metric_name(target_spec)
    min_precision, max_precision = spec.precision_range

    values: list[tuple[int, dict[str, float]]] = []
    for precision in range(min_precision, max_precision + 1):
        grid = spec.factory(precision)
        metrics = grid.metrics(at=at)
        if constraints and constraints.bbox is not None:
            metrics["cells"] = float(len(grid.cells_in_bbox(constraints.bbox)))
        values.append((precision, metrics))

    if not values:
        raise ValueError(f"No precision candidates for system '{system}'")

    filtered = values
    if constraints:
        filtered = []
        for precision, metrics in values:
            if constraints.max_size_m is not None and metrics.get("size_m", 0.0) > constraints.max_size_m:
                continue
            if constraints.max_area_km2 is not None and metrics.get("area_km2", 0.0) > constraints.max_area_km2:
                continue
            if constraints.max_cells is not None and metrics.get("cells", 0.0) > constraints.max_cells:
                continue
            filtered.append((precision, metrics))
        if not filtered:
            filtered = values

    if policy == "min_cells":
        return _score_min_cells(filtered)

    if policy == "balanced":
        weights = weights or {"size_m": 1.0, "area_km2": 1.0}
        def score_item(item: tuple[int, dict[str, float]]) -> float:
            precision, metrics = item
            del precision
            score = 0.0
            for key, weight in weights.items():
                if key not in metrics:
                    continue
                score += weight * metrics[key]
            return score
        precision, metrics = min(filtered, key=score_item)
        return PrecisionChoice(precision, metrics, 1.0, "balanced")

    target_value = target_spec.value
    if policy == "closest_over":
        return _score_closest_over(filtered, metric_name, target_value)

    return _score_closest_under(filtered, metric_name, target_value)


def profile(system: str, precision: int, at: Location | None = None) -> dict[str, float]:
    spec = get_system(system)
    grid = spec.factory(precision)
    return grid.metrics(at=at)


def compare(
    system: str, precisions: list[int], at: Location | None = None
) -> list[PrecisionChoice]:
    spec = get_system(system)
    choices = []
    for precision in precisions:
        grid = spec.factory(precision)
        metrics = grid.metrics(at=at)
        choices.append(PrecisionChoice(precision, metrics, 1.0, "profile"))
    return choices
