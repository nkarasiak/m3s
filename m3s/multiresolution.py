"""Multi-resolution grid operations for M3S."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import Point
from shapely.strtree import STRtree

from .core.cell import Cell
from .core.grid import GridProtocol
from .core.types import Bbox
from .relationships import GridRelationshipAnalyzer


@dataclass
class ResolutionLevel:
    """Resolution level metadata."""

    level: int
    precision: int
    area_km2: float
    cells: list[Cell]


class MultiResolutionGrid:
    """Multi-resolution grid supporting hierarchical operations."""

    def __init__(
        self, grid_factory: Callable[[int], GridProtocol], resolution_levels: list[int]
    ) -> None:
        self.grid_factory = grid_factory
        self.resolution_levels = sorted(resolution_levels)
        self._level_index = {
            precision: idx for idx, precision in enumerate(self.resolution_levels)
        }
        self.grids: dict[int, GridProtocol] = {}
        self.levels: dict[int, ResolutionLevel] = {}

        for level_idx, precision in enumerate(self.resolution_levels):
            grid = grid_factory(precision)
            self.grids[precision] = grid
            self.levels[level_idx] = ResolutionLevel(
                level=level_idx,
                precision=precision,
                area_km2=grid.area_km2,
                cells=[],
            )

    def populate_region(
        self,
        bounds: Bbox,
        adaptive: bool = False,
        density_threshold: Optional[float] = None,
    ) -> dict[int, list[Cell]]:
        min_lon, min_lat, max_lon, max_lat = bounds
        result: dict[int, list[Cell]] = {}

        for precision, grid in self.grids.items():
            cells = list(grid.cells_in_bbox((min_lon, min_lat, max_lon, max_lat)))
            if adaptive and density_threshold is not None:
                cells = self._apply_adaptive_filtering(cells, density_threshold)
            result[precision] = cells
            level_idx = self._level_index[precision]
            self.levels[level_idx].cells = cells

        return result

    def _apply_adaptive_filtering(self, cells: list[Cell], density_threshold: float) -> list[Cell]:
        if len(cells) <= density_threshold:
            return cells
        step = max(1, len(cells) // int(density_threshold))
        return cells[::step]

    def get_hierarchical_cells(
        self, point: Point, max_levels: Optional[int] = None
    ) -> dict[int, Cell]:
        lat, lon = point.y, point.x
        result: dict[int, Cell] = {}

        levels_to_process = self.resolution_levels
        if max_levels is not None:
            levels_to_process = levels_to_process[:max_levels]

        for precision in levels_to_process:
            grid = self.grids[precision]
            result[precision] = grid.cell(lat, lon)

        return result

    def get_parent_child_relationships(self, bounds: Bbox) -> dict[str, list[str]]:
        relationships: dict[str, list[str]] = {}
        analyzer = GridRelationshipAnalyzer()
        level_cells = self.populate_region(bounds)

        for i in range(len(self.resolution_levels) - 1):
            parent_precision = self.resolution_levels[i]
            child_precision = self.resolution_levels[i + 1]
            parent_cells = level_cells[parent_precision]
            child_cells = level_cells[child_precision]

            for parent_cell in parent_cells:
                children = analyzer.find_contained_cells(parent_cell, child_cells)
                if children:
                    relationships[str(parent_cell.id)] = [str(child.id) for child in children]

        return relationships

    def create_level_of_detail_view(
        self,
        bounds: Bbox,
        detail_function: Optional[Callable[[Cell], int]] = None,
    ) -> gpd.GeoDataFrame:
        if detail_function is None:
            detail_function = self._default_detail_function

        base_precision = self.resolution_levels[0]
        base_cells = list(self.grids[base_precision].cells_in_bbox(bounds))

        selected_cells: list[Cell] = []
        for base_cell in base_cells:
            detail_level = detail_function(base_cell)
            if detail_level < len(self.resolution_levels):
                target_precision = self.resolution_levels[detail_level]
                if target_precision == base_precision:
                    selected_cells.append(base_cell)
                else:
                    base_polygon = base_cell.polygon
                    cell_bounds = base_polygon.bounds
                    fine_cells = list(self.grids[target_precision].cells_in_bbox(
                        (cell_bounds[0], cell_bounds[1], cell_bounds[2], cell_bounds[3])
                    ))
                    if not fine_cells:
                        continue
                    if len(fine_cells) <= 32:
                        for fine_cell in fine_cells:
                            if base_polygon.intersects(fine_cell.polygon):
                                selected_cells.append(fine_cell)
                    else:
                        fine_polygons = [cell.polygon for cell in fine_cells]
                        tree = STRtree(fine_polygons)
                        matches = tree.query(base_polygon, predicate="intersects")
                        for match_idx in matches:
                            selected_cells.append(fine_cells[int(match_idx)])
            else:
                selected_cells.append(base_cell)

        if not selected_cells:
            return gpd.GeoDataFrame()

        data = [
            {
                "cell_id": cell.id,
                "precision": cell.precision,
                "area_km2": cell.area_km2,
                "geometry": cell.polygon,
            }
            for cell in selected_cells
        ]
        return gpd.GeoDataFrame(data)

    def _default_detail_function(self, cell: Cell) -> int:
        area = cell.area_km2
        if area > 1000:
            return 0
        if area > 100:
            return min(1, len(self.resolution_levels) - 1)
        return len(self.resolution_levels) - 1

    def analyze_scale_transitions(self, bounds: Bbox) -> pd.DataFrame:
        level_cells = self.populate_region(bounds)
        transition_data: list[dict[str, float | int]] = []

        for i in range(len(self.resolution_levels) - 1):
            parent_precision = self.resolution_levels[i]
            child_precision = self.resolution_levels[i + 1]

            parent_cells = level_cells[parent_precision]
            child_cells = level_cells[child_precision]

            parent_count = len(parent_cells)
            child_count = len(child_cells)

            if parent_count > 0:
                subdivision_ratio = child_count / parent_count
                area_ratio = (
                    self.grids[child_precision].area_km2
                    / self.grids[parent_precision].area_km2
                )
                transition_data.append(
                    {
                        "from_precision": parent_precision,
                        "to_precision": child_precision,
                        "from_level": i,
                        "to_level": i + 1,
                        "parent_cells": parent_count,
                        "child_cells": child_count,
                        "subdivision_ratio": subdivision_ratio,
                        "area_ratio": area_ratio,
                        "from_area_km2": self.grids[parent_precision].area_km2,
                        "to_area_km2": self.grids[child_precision].area_km2,
                    }
                )

        return pd.DataFrame(transition_data)

    def aggregate_to_level(
        self, data: gpd.GeoDataFrame, target_level: int, aggregation_func: str = "sum"
    ) -> gpd.GeoDataFrame:
        if target_level >= len(self.resolution_levels):
            raise ValueError(f"Invalid target level: {target_level}")

        target_precision = self.resolution_levels[target_level]
        target_grid = self.grids[target_precision]

        bounds = data.total_bounds
        target_cells = list(
            target_grid.cells_in_bbox(
            (bounds[0], bounds[1], bounds[2], bounds[3])
        )
        )

        numeric_columns = data.select_dtypes(include=[np.number]).columns
        numeric_columns = [col for col in numeric_columns if col != "geometry"]
        agg_func = aggregation_func if aggregation_func in {"sum", "mean", "max", "min"} else "sum"
        if not target_cells:
            return gpd.GeoDataFrame()

        target_polygons = [cell.polygon for cell in target_cells]
        target_gdf = gpd.GeoDataFrame(
            {
                "cell_id": [cell.id for cell in target_cells],
            },
            geometry=target_polygons,
            crs=data.crs,
        )
        target_gdf.index.name = "_target_idx"

        aggregated_data: list[dict[str, object]] = []
        try:
            joined = gpd.sjoin(target_gdf, data, how="inner", predicate="intersects")
        except Exception:
            joined = None

        if joined is not None:
            if joined.empty:
                return gpd.GeoDataFrame()
            if numeric_columns:
                grouped = joined.groupby(level=0, sort=False)
                aggregated_numeric = grouped[numeric_columns].agg(agg_func).sort_index()
                counts = grouped.size().sort_index()
                result = target_gdf.loc[aggregated_numeric.index].copy()
                result["contributing_cells"] = counts.astype(int).values
                for col in aggregated_numeric.columns:
                    result[col] = aggregated_numeric[col].values
                return result.reset_index(drop=True)

            counts = joined.groupby(level=0, sort=False).size().sort_index()
            result = target_gdf.loc[counts.index].copy()
            result["contributing_cells"] = counts.astype(int).values
            return result.reset_index(drop=True)

        sindex = data.sindex
        for target_cell in target_cells:
            target_polygon = target_cell.polygon
            try:
                candidate_idx = sindex.query(target_polygon, predicate="intersects")
                intersecting_data = data.iloc[candidate_idx]
                if not intersecting_data.empty:
                    intersecting_mask = intersecting_data.geometry.intersects(
                        target_polygon
                    )
                    intersecting_data = intersecting_data[intersecting_mask]
            except Exception:
                intersecting_mask = data.geometry.intersects(target_polygon)
                intersecting_data = data[intersecting_mask]

            if len(intersecting_data) > 0:
                aggregated_row: dict[str, object] = {
                    "cell_id": target_cell.id,
                    "geometry": target_cell.polygon,
                }

                if numeric_columns:
                    aggregated_values = intersecting_data[numeric_columns].agg(agg_func)
                    aggregated_row.update(aggregated_values.to_dict())

                aggregated_row["contributing_cells"] = len(intersecting_data)
                aggregated_data.append(aggregated_row)

        if not aggregated_data:
            return gpd.GeoDataFrame()

        return gpd.GeoDataFrame(aggregated_data)

    def get_resolution_statistics(self) -> pd.DataFrame:
        stats_data = []
        for level_idx, precision in enumerate(self.resolution_levels):
            grid = self.grids[precision]
            level_info = self.levels[level_idx]
            stats_data.append(
                {
                    "level": level_idx,
                    "precision": precision,
                    "area_km2": grid.area_km2,
                    "cell_count": len(level_info.cells),
                    "grid_type": type(grid).__name__,
                }
            )
        return pd.DataFrame(stats_data)

    def create_quad_tree_structure(
        self, bounds: Bbox, max_depth: Optional[int] = None
    ) -> dict[str, object]:
        if max_depth is None:
            max_depth = len(self.resolution_levels) - 1

        root_precision = self.resolution_levels[0]
        root_cells = self.grids[root_precision].cells_in_bbox(bounds)

        tree: dict[str, object] = {
            "level": 0,
            "precision": root_precision,
            "cells": {},
            "children": {},
        }

        analyzer = GridRelationshipAnalyzer()

        def build_subtree(
            parent_cells: list[Cell],
            current_level: int,
            parent_node: dict[str, object],
        ) -> None:
            if current_level >= max_depth or current_level >= len(self.resolution_levels) - 1:
                return

            child_precision = self.resolution_levels[current_level + 1]
            child_grid = self.grids[child_precision]

            for parent_cell in parent_cells:
                parent_bounds = parent_cell.polygon.bounds
                potential_children = child_grid.cells_in_bbox(
                    (parent_bounds[0], parent_bounds[1], parent_bounds[2], parent_bounds[3])
                )
                actual_children = analyzer.find_contained_cells(
                    parent_cell, list(potential_children)
                )

                if actual_children:
                    child_node = {
                        "level": current_level + 1,
                        "precision": child_precision,
                        "cells": {str(child.id): child for child in actual_children},
                        "children": {},
                    }
                    parent_node["children"][str(parent_cell.id)] = child_node
                    build_subtree(actual_children, current_level + 1, child_node)

        tree["cells"] = {str(cell.id): cell for cell in root_cells}
        build_subtree(list(root_cells), 0, tree)

        return tree


def _resolve_grid_factory(
    grid_factory: Callable[[int], GridProtocol] | GridProtocol,
) -> Callable[[int], GridProtocol]:
    if callable(grid_factory):
        return grid_factory

    grid = grid_factory
    name = getattr(grid, "name", None)
    if name is None:
        raise ValueError("Grid factory must be callable or a GridProtocol instance.")

    if name == "h3":
        from .grids import H3Grid

        return lambda precision: H3Grid(precision=precision)
    if name == "quadkey":
        from .grids import QuadkeyGrid

        return lambda precision: QuadkeyGrid(precision=precision)
    if name == "s2":
        from .grids import S2Grid

        return lambda precision: S2Grid(precision=precision)
    if name == "slippy":
        from .grids import SlippyGrid

        return lambda precision: SlippyGrid(precision=precision)

    grid_cls = grid.__class__
    return lambda precision: grid_cls(precision=precision)


def create_multiresolution_grid(
    grid_factory: Callable[[int], GridProtocol] | GridProtocol, levels: list[int]
) -> MultiResolutionGrid:
    """Create a multi-resolution grid."""
    return MultiResolutionGrid(_resolve_grid_factory(grid_factory), levels)


def get_hierarchical_cells(
    grid: MultiResolutionGrid, point: Point, max_levels: Optional[int] = None
) -> dict[int, Cell]:
    """Get cells containing a point at all resolution levels."""
    return grid.get_hierarchical_cells(point, max_levels)


def create_adaptive_grid(
    grid_factory: Callable[[int], GridProtocol] | GridProtocol,
    bounds: Bbox,
    levels: list[int],
    detail_function: Optional[Callable[[Cell], int]] = None,
) -> gpd.GeoDataFrame:
    """Create an adaptive resolution grid."""
    multi_grid = MultiResolutionGrid(_resolve_grid_factory(grid_factory), levels)
    return multi_grid.create_level_of_detail_view(bounds, detail_function)
