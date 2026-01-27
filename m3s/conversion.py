"""Grid conversion utilities for M3S."""

from __future__ import annotations

import warnings
from typing import Iterable, Optional

import pandas as pd

from .core.cell import Cell
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


class GridConverter:
    """Convert between grid systems."""

    GRID_FACTORIES = {
        "a5": lambda precision: A5Grid(precision=precision),
        "geohash": lambda precision: GeohashGrid(precision=precision),
        "mgrs": lambda precision: MGRSGrid(precision=precision),
        "h3": lambda precision: H3Grid(precision=precision),
        "quadkey": lambda precision: QuadkeyGrid(precision=precision),
        "s2": lambda precision: S2Grid(precision=precision),
        "slippy": lambda precision: SlippyGrid(precision=precision),
        "csquares": lambda precision: CSquaresGrid(precision=precision),
        "gars": lambda precision: GARSGrid(precision=precision),
        "maidenhead": lambda precision: MaidenheadGrid(precision=precision),
        "pluscode": lambda precision: PlusCodeGrid(precision=precision),
        "what3words": lambda precision: What3WordsGrid(precision=precision),
    }

    DEFAULT_PRECISIONS = {
        "a5": 6,
        "geohash": 5,
        "mgrs": 1,
        "h3": 7,
        "quadkey": 12,
        "s2": 10,
        "slippy": 12,
        "csquares": 2,
        "gars": 2,
        "maidenhead": 4,
        "pluscode": 8,
        "what3words": 1,
    }

    def __init__(self) -> None:
        self._grid_cache: dict[tuple[str, int], GridProtocol] = {}

    def _get_grid(self, system_name: str, precision: Optional[int] = None) -> GridProtocol:
        if system_name not in self.GRID_FACTORIES:
            available = ", ".join(sorted(self.GRID_FACTORIES))
            raise ValueError(
                f"Unknown grid system '{system_name}'. Available: {available}"
            )

        if precision is None:
            precision = self.DEFAULT_PRECISIONS[system_name]

        cache_key = (system_name, precision)
        if cache_key not in self._grid_cache:
            factory = self.GRID_FACTORIES[system_name]
            self._grid_cache[cache_key] = factory(precision)
        return self._grid_cache[cache_key]

    def convert_cell(
        self,
        cell: Cell,
        target_system: str,
        target_precision: Optional[int] = None,
        method: str = "centroid",
    ) -> Cell | list[Cell]:
        target_grid = self._get_grid(target_system, target_precision)

        if method == "centroid":
            centroid = cell.polygon.centroid
            return target_grid.cell(centroid.y, centroid.x)

        if method in {"overlap", "contains"}:
            min_lon, min_lat, max_lon, max_lat = cell.polygon.bounds
            target_cells = target_grid.cells_in_bbox((min_lon, min_lat, max_lon, max_lat))
            if method == "overlap":
                return [c for c in target_cells if cell.polygon.intersects(c.polygon)]
            return [c for c in target_cells if cell.polygon.contains(c.polygon)]

        raise ValueError(f"Unknown conversion method: {method}")

    def convert_cells_batch(
        self,
        cells: Iterable[Cell],
        target_system: str,
        target_precision: Optional[int] = None,
        method: str = "centroid",
    ) -> list[Cell | list[Cell]]:
        return [
            self.convert_cell(cell, target_system, target_precision, method)
            for cell in cells
        ]

    def create_conversion_table(
        self,
        source_system: str,
        target_system: str,
        bounds: tuple[float, float, float, float],
        source_precision: Optional[int] = None,
        target_precision: Optional[int] = None,
        method: str = "centroid",
    ) -> pd.DataFrame:
        source_grid = self._get_grid(source_system, source_precision)
        min_lon, min_lat, max_lon, max_lat = bounds
        source_cells = source_grid.cells_in_bbox((min_lon, min_lat, max_lon, max_lat))

        rows: list[dict[str, object]] = []
        for source_cell in source_cells:
            targets = self.convert_cell(
                source_cell, target_system, target_precision, method
            )
            if isinstance(targets, list):
                for target_cell in targets:
                    rows.append(
                        {
                            "source_system": source_system,
                            "source_id": source_cell.id,
                            "source_precision": source_cell.precision,
                            "target_system": target_system,
                            "target_id": target_cell.id,
                            "target_precision": target_cell.precision,
                            "conversion_method": method,
                        }
                    )
            else:
                rows.append(
                    {
                        "source_system": source_system,
                        "source_id": source_cell.id,
                        "source_precision": source_cell.precision,
                        "target_system": target_system,
                        "target_id": targets.id,
                        "target_precision": targets.precision,
                        "conversion_method": method,
                    }
                )

        return pd.DataFrame(rows)

    def get_equivalent_precision(
        self, source_system: str, source_precision: int, target_system: str
    ) -> int:
        source_grid = self._get_grid(source_system, source_precision)
        source_area = source_grid.area_km2

        best_precision = self.DEFAULT_PRECISIONS[target_system]
        best_diff = float("inf")
        test_range = range(1, 16) if target_system != "what3words" else [1]

        for test_precision in test_range:
            try:
                target_grid = self._get_grid(target_system, test_precision)
            except Exception:
                continue
            diff = abs(source_area - target_grid.area_km2)
            if diff < best_diff:
                best_diff = diff
                best_precision = test_precision

        return best_precision

    def get_system_info(self) -> pd.DataFrame:
        info_data = []
        for system_name, factory in self.GRID_FACTORIES.items():
            try:
                default_precision = self.DEFAULT_PRECISIONS[system_name]
                grid = self._get_grid(system_name, default_precision)
                info_data.append(
                    {
                        "system": system_name,
                        "class": grid.__class__.__name__,
                        "default_precision": default_precision,
                        "default_area_km2": grid.area_km2,
                    }
                )
            except Exception as exc:
                warnings.warn(
                    f"Could not load info for {system_name}: {exc}", stacklevel=2
                )
        return pd.DataFrame(info_data)


_converter: Optional[GridConverter] = None


def get_converter() -> GridConverter:
    """Get or create the global converter instance."""
    global _converter
    if _converter is None:
        _converter = GridConverter()
    return _converter


def convert_cell(
    cell: Cell, target_system: str, **kwargs
) -> Cell | list[Cell]:
    """Convert a single grid cell to another system."""
    return get_converter().convert_cell(cell, target_system, **kwargs)


def convert_cells(
    cells: Iterable[Cell], target_system: str, **kwargs
) -> list[Cell | list[Cell]]:
    """Convert multiple grid cells to another system."""
    return get_converter().convert_cells_batch(cells, target_system, **kwargs)


def get_equivalent_precision(
    source_system: str, source_precision: int, target_system: str
) -> int:
    """Find equivalent precision between grid systems."""
    return get_converter().get_equivalent_precision(
        source_system, source_precision, target_system
    )


def create_conversion_table(
    source_system: str, target_system: str, bounds: tuple[float, float, float, float], **kwargs
) -> pd.DataFrame:
    """Create a conversion table between two grid systems."""
    return get_converter().create_conversion_table(
        source_system, target_system, bounds, **kwargs
    )


def list_grid_systems() -> pd.DataFrame:
    """List all available grid systems with information."""
    return get_converter().get_system_info()
