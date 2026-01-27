"""Registry of supported grid systems."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from .core.grid import GridProtocol
from .grids import (
    A5Grid,
    CSquaresGrid,
    GARSGrid,
    GeohashGrid,
    H3Grid,
    MaidenheadGrid,
    MGRSGrid,
    PlusCodeGrid,
    QuadkeyGrid,
    S2Grid,
    SlippyGrid,
    What3WordsGrid,
)


@dataclass(slots=True)
class SystemSpec:
    name: str
    factory: Callable[..., GridProtocol]
    precision_range: tuple[int, int]
    aliases: set[str] = field(default_factory=set)
    capabilities: set[str] = field(default_factory=set)

    def matches(self, key: str) -> bool:
        return key == self.name or key in self.aliases


_REGISTRY: dict[str, SystemSpec] = {}


def register(spec: SystemSpec) -> None:
    _REGISTRY[spec.name] = spec
    for alias in spec.aliases:
        _REGISTRY[alias] = spec


def get(name: str) -> SystemSpec:
    key = name.strip().lower()
    if key not in _REGISTRY:
        available = ", ".join(sorted({spec.name for spec in _REGISTRY.values()}))
        raise ValueError(f"Unknown grid system '{name}'. Available: {available}")
    return _REGISTRY[key]


def list() -> list[SystemSpec]:
    specs = {spec.name: spec for spec in _REGISTRY.values()}
    return [specs[name] for name in sorted(specs)]


def _register_defaults() -> None:
    register(
        SystemSpec(
            name="a5",
            factory=lambda precision, **opts: A5Grid(precision=precision, **opts),
            precision_range=(0, 30),
            aliases={"a5grid"},
        )
    )
    register(
        SystemSpec(
            name="geohash",
            factory=lambda precision, **opts: GeohashGrid(precision=precision, **opts),
            precision_range=(1, 12),
            aliases={"geo_hash"},
        )
    )
    register(
        SystemSpec(
            name="mgrs",
            factory=lambda precision, **opts: MGRSGrid(precision=precision, **opts),
            precision_range=(0, 5),
        )
    )
    register(
        SystemSpec(
            name="h3",
            factory=lambda precision, **opts: H3Grid(precision=precision, **opts),
            precision_range=(0, 15),
        )
    )
    register(
        SystemSpec(
            name="quadkey",
            factory=lambda precision, **opts: QuadkeyGrid(precision=precision, **opts),
            precision_range=(1, 23),
            aliases={"quad_key"},
        )
    )
    register(
        SystemSpec(
            name="s2",
            factory=lambda precision, **opts: S2Grid(precision=precision, **opts),
            precision_range=(0, 30),
        )
    )
    register(
        SystemSpec(
            name="slippy",
            factory=lambda precision, **opts: SlippyGrid(precision=precision, **opts),
            precision_range=(0, 22),
            aliases={"slippy_map"},
        )
    )
    register(
        SystemSpec(
            name="csquares",
            factory=lambda precision, **opts: CSquaresGrid(precision=precision, **opts),
            precision_range=(1, 5),
            aliases={"c-squares"},
        )
    )
    register(
        SystemSpec(
            name="gars",
            factory=lambda precision, **opts: GARSGrid(precision=precision, **opts),
            precision_range=(1, 3),
        )
    )
    register(
        SystemSpec(
            name="maidenhead",
            factory=lambda precision, **opts: MaidenheadGrid(precision=precision, **opts),
            precision_range=(1, 5),
            aliases={"maiden", "maidenhead_locator"},
        )
    )
    register(
        SystemSpec(
            name="pluscode",
            factory=lambda precision, **opts: PlusCodeGrid(precision=precision, **opts),
            precision_range=(1, 12),
            aliases={"plus_code", "olc"},
        )
    )
    register(
        SystemSpec(
            name="what3words",
            factory=lambda precision, **opts: What3WordsGrid(precision=precision, **opts),
            precision_range=(1, 1),
            aliases={"w3w"},
        )
    )


_register_defaults()
