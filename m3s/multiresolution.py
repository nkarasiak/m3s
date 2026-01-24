"""
Multi-resolution grid operations for M3S.

Provides functionality for working with multiple resolution levels simultaneously,
including hierarchical operations, level-of-detail analysis, and adaptive gridding.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import Point

from .base import BaseGrid, GridCell
from .relationships import GridRelationshipAnalyzer


@dataclass
class ResolutionLevel:
    """
    Represents a resolution level in a multi-resolution grid.

    Attributes
    ----------
    level : int
        Resolution level identifier
    precision : int
        Grid precision/resolution parameter
    area_km2 : float
        Typical cell area at this level
    cells : List[GridCell]
        Grid cells at this resolution level
    """

    level: int
    precision: int
    area_km2: float
    cells: List[GridCell]


class MultiResolutionGrid:
    """
    Multi-resolution grid supporting hierarchical operations across different detail levels.

    Enables analysis and operations that span multiple resolution levels,
    including adaptive gridding and level-of-detail processing.
    """

    def __init__(self, grid_system: BaseGrid, resolution_levels: List[int]):
        """
        Initialize multi-resolution grid.

        Parameters
        ----------
        grid_system : BaseGrid
            Base grid system to use
        resolution_levels : List[int]
            List of precision/resolution levels to support
        """
        self.grid_system = grid_system
        self.resolution_levels = sorted(resolution_levels)
        self.grids = {}
        self.levels = {}

        # Create grid instances for each resolution level
        for level_idx, precision in enumerate(self.resolution_levels):
            grid_copy = type(grid_system).__new__(type(grid_system))
            grid_copy.__dict__.update(grid_system.__dict__)
            grid_copy.precision = precision

            self.grids[precision] = grid_copy
            self.levels[level_idx] = ResolutionLevel(
                level=level_idx,
                precision=precision,
                area_km2=grid_copy.area_km2,
                cells=[],
            )

    def populate_region(
        self,
        bounds: Tuple[float, float, float, float],
        adaptive: bool = False,
        density_threshold: Optional[float] = None,
    ) -> Dict[int, List[GridCell]]:
        """
        Populate all resolution levels with cells for a given region.

        Parameters
        ----------
        bounds : Tuple[float, float, float, float]
            Bounding box as (min_lon, min_lat, max_lon, max_lat)
        adaptive : bool, optional
            Whether to use adaptive resolution selection, by default False
        density_threshold : float, optional
            Density threshold for adaptive gridding, by default None

        Returns
        -------
        Dict[int, List[GridCell]]
            Dictionary mapping resolution levels to cell lists
        """
        min_lon, min_lat, max_lon, max_lat = bounds
        result = {}

        for precision, grid in self.grids.items():
            cells = grid.get_cells_in_bbox(min_lat, min_lon, max_lat, max_lon)

            if adaptive and density_threshold is not None:
                cells = self._apply_adaptive_filtering(cells, density_threshold)

            result[precision] = cells

            # Update level storage
            level_idx = self.resolution_levels.index(precision)
            self.levels[level_idx].cells = cells

        return result

    def _apply_adaptive_filtering(
        self, cells: List[GridCell], density_threshold: float
    ) -> List[GridCell]:
        """
        Apply adaptive filtering based on density threshold.

        Parameters
        ----------
        cells : List[GridCell]
            Input cells
        density_threshold : float
            Density threshold

        Returns
        -------
        List[GridCell]
            Filtered cells
        """
        # Simple density-based filtering - can be enhanced with more sophisticated methods
        if len(cells) <= density_threshold:
            return cells

        # Sample cells based on density threshold
        step = max(1, len(cells) // int(density_threshold))
        return cells[::step]

    def get_hierarchical_cells(
        self, point: Point, max_levels: Optional[int] = None
    ) -> Dict[int, GridCell]:
        """
        Get cells containing a point at all resolution levels.

        Parameters
        ----------
        point : Point
            Point to query
        max_levels : int, optional
            Maximum number of levels to return

        Returns
        -------
        Dict[int, GridCell]
            Dictionary mapping resolution levels to cells
        """
        lat, lon = point.y, point.x
        result = {}

        levels_to_process = self.resolution_levels
        if max_levels is not None:
            levels_to_process = levels_to_process[:max_levels]

        for precision in levels_to_process:
            grid = self.grids[precision]
            cell = grid.get_cell_from_point(lat, lon)
            result[precision] = cell

        return result

    def get_parent_child_relationships(
        self, bounds: Tuple[float, float, float, float]
    ) -> Dict[str, List[str]]:
        """
        Analyze parent-child relationships between resolution levels.

        Parameters
        ----------
        bounds : Tuple[float, float, float, float]
            Bounding box to analyze

        Returns
        -------
        Dict[str, List[str]]
            Dictionary mapping parent cell IDs to lists of child cell IDs
        """
        relationships = {}
        analyzer = GridRelationshipAnalyzer()

        # Populate all levels for the region
        level_cells = self.populate_region(bounds)

        # Analyze relationships between consecutive levels
        for i in range(len(self.resolution_levels) - 1):
            parent_precision = self.resolution_levels[i]
            child_precision = self.resolution_levels[i + 1]

            parent_cells = level_cells[parent_precision]
            child_cells = level_cells[child_precision]

            for parent_cell in parent_cells:
                children = analyzer.find_contained_cells(parent_cell, child_cells)
                if children:
                    relationships[parent_cell.identifier] = [
                        child.identifier for child in children
                    ]

        return relationships

    def create_level_of_detail_view(
        self,
        bounds: Tuple[float, float, float, float],
        detail_function: callable = None,
    ) -> gpd.GeoDataFrame:
        """
        Create a level-of-detail view with adaptive resolution selection.

        Parameters
        ----------
        bounds : Tuple[float, float, float, float]
            Bounding box
        detail_function : callable, optional
            Function to determine appropriate detail level for each area

        Returns
        -------
        gpd.GeoDataFrame
            GeoDataFrame with adaptive resolution cells
        """
        if detail_function is None:
            detail_function = self._default_detail_function

        # Start with coarsest resolution
        base_precision = self.resolution_levels[0]
        base_cells = self.grids[base_precision].get_cells_in_bbox(*bounds)

        selected_cells = []

        for base_cell in base_cells:
            # Determine appropriate detail level for this cell
            detail_level = detail_function(base_cell)

            if detail_level < len(self.resolution_levels):
                target_precision = self.resolution_levels[detail_level]
                if target_precision == base_precision:
                    selected_cells.append(base_cell)
                else:
                    # Get finer resolution cells for this area
                    cell_bounds = base_cell.polygon.bounds
                    fine_cells = self.grids[target_precision].get_cells_in_bbox(
                        cell_bounds[1], cell_bounds[0], cell_bounds[3], cell_bounds[2]
                    )

                    # Filter to cells that actually intersect with base cell
                    for fine_cell in fine_cells:
                        if base_cell.polygon.intersects(fine_cell.polygon):
                            selected_cells.append(fine_cell)
            else:
                selected_cells.append(base_cell)

        # Convert to GeoDataFrame
        if not selected_cells:
            return gpd.GeoDataFrame()

        data = []
        for cell in selected_cells:
            data.append(
                {
                    "cell_id": cell.identifier,
                    "precision": cell.precision,
                    "area_km2": cell.area_km2,
                    "geometry": cell.polygon,
                }
            )

        gdf = gpd.GeoDataFrame(data)
        return gdf

    def _default_detail_function(self, cell: GridCell) -> int:
        """
        Default function for determining detail level.

        Parameters
        ----------
        cell : GridCell
            Grid cell to evaluate

        Returns
        -------
        int
            Detail level index
        """
        # Simple area-based decision
        area = cell.area_km2

        if area > 1000:  # Large areas get coarse resolution
            return 0
        elif area > 100:  # Medium areas get medium resolution
            return min(1, len(self.resolution_levels) - 1)
        else:  # Small areas get fine resolution
            return len(self.resolution_levels) - 1

    def analyze_scale_transitions(
        self, bounds: Tuple[float, float, float, float]
    ) -> pd.DataFrame:
        """
        Analyze how data transitions between different scale levels.

        Parameters
        ----------
        bounds : Tuple[float, float, float, float]
            Bounding box to analyze

        Returns
        -------
        pd.DataFrame
            Analysis of scale transitions
        """
        level_cells = self.populate_region(bounds)
        transition_data = []

        for i in range(len(self.resolution_levels) - 1):
            parent_precision = self.resolution_levels[i]
            child_precision = self.resolution_levels[i + 1]

            parent_cells = level_cells[parent_precision]
            child_cells = level_cells[child_precision]

            # Calculate transition metrics
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
        """
        Aggregate data from finer to coarser resolution level.

        Parameters
        ----------
        data : gpd.GeoDataFrame
            Input data with grid cells
        target_level : int
            Target resolution level index
        aggregation_func : str, optional
            Aggregation function ('sum', 'mean', 'max', 'min'), by default 'sum'

        Returns
        -------
        gpd.GeoDataFrame
            Aggregated data
        """
        if target_level >= len(self.resolution_levels):
            raise ValueError(f"Invalid target level: {target_level}")

        target_precision = self.resolution_levels[target_level]
        target_grid = self.grids[target_precision]

        # Get target cells for the data extent
        bounds = data.total_bounds
        target_cells = target_grid.get_cells_in_bbox(
            bounds[1], bounds[0], bounds[3], bounds[2]
        )

        aggregated_data = []
        GridRelationshipAnalyzer()

        for target_cell in target_cells:
            # Find data cells that intersect with this target cell
            intersecting_mask = data.geometry.intersects(target_cell.polygon)
            intersecting_data = data[intersecting_mask]

            if len(intersecting_data) > 0:
                # Aggregate numeric columns
                numeric_columns = intersecting_data.select_dtypes(
                    include=[np.number]
                ).columns
                numeric_columns = [col for col in numeric_columns if col != "geometry"]

                aggregated_row = {
                    "cell_id": target_cell.identifier,
                    "geometry": target_cell.polygon,
                }

                for col in numeric_columns:
                    if aggregation_func == "sum":
                        aggregated_row[col] = intersecting_data[col].sum()
                    elif aggregation_func == "mean":
                        aggregated_row[col] = intersecting_data[col].mean()
                    elif aggregation_func == "max":
                        aggregated_row[col] = intersecting_data[col].max()
                    elif aggregation_func == "min":
                        aggregated_row[col] = intersecting_data[col].min()
                    else:
                        aggregated_row[col] = intersecting_data[
                            col
                        ].sum()  # Default to sum

                # Add count of contributing cells
                aggregated_row["contributing_cells"] = len(intersecting_data)
                aggregated_data.append(aggregated_row)

        if not aggregated_data:
            return gpd.GeoDataFrame()

        result_gdf = gpd.GeoDataFrame(aggregated_data)
        return result_gdf

    def get_resolution_statistics(self) -> pd.DataFrame:
        """
        Get statistics about all resolution levels.

        Returns
        -------
        pd.DataFrame
            Statistics for each resolution level
        """
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
        self, bounds: Tuple[float, float, float, float], max_depth: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Create a quad-tree-like hierarchical structure.

        Parameters
        ----------
        bounds : Tuple[float, float, float, float]
            Bounding box
        max_depth : int, optional
            Maximum tree depth

        Returns
        -------
        Dict[str, Any]
            Hierarchical tree structure
        """
        if max_depth is None:
            max_depth = len(self.resolution_levels) - 1

        # Start with coarsest level
        root_precision = self.resolution_levels[0]
        root_cells = self.grids[root_precision].get_cells_in_bbox(*bounds)

        tree = {"level": 0, "precision": root_precision, "cells": {}, "children": {}}

        analyzer = GridRelationshipAnalyzer()

        def build_subtree(
            parent_cells: List[GridCell],
            current_level: int,
            parent_node: Dict[str, Any],
        ):
            if (
                current_level >= max_depth
                or current_level >= len(self.resolution_levels) - 1
            ):
                return

            child_precision = self.resolution_levels[current_level + 1]
            child_grid = self.grids[child_precision]

            for parent_cell in parent_cells:
                parent_bounds = parent_cell.polygon.bounds
                potential_children = child_grid.get_cells_in_bbox(
                    parent_bounds[1],
                    parent_bounds[0],
                    parent_bounds[3],
                    parent_bounds[2],
                )

                # Find children actually contained in parent
                actual_children = analyzer.find_contained_cells(
                    parent_cell, potential_children
                )

                if actual_children:
                    child_node = {
                        "level": current_level + 1,
                        "precision": child_precision,
                        "cells": {child.identifier: child for child in actual_children},
                        "children": {},
                    }

                    parent_node["children"][parent_cell.identifier] = child_node

                    # Recursively build subtree
                    build_subtree(actual_children, current_level + 1, child_node)

        # Build the tree
        tree["cells"] = {cell.identifier: cell for cell in root_cells}
        build_subtree(root_cells, 0, tree)

        return tree


# Convenience functions
def create_multiresolution_grid(
    grid_system: BaseGrid, levels: List[int]
) -> MultiResolutionGrid:
    """Create a multi-resolution grid."""
    return MultiResolutionGrid(grid_system, levels)


def get_hierarchical_cells(
    grid: MultiResolutionGrid, point: Point, max_levels: Optional[int] = None
) -> Dict[int, GridCell]:
    """Get cells containing a point at all resolution levels."""
    return grid.get_hierarchical_cells(point, max_levels)


def create_adaptive_grid(
    grid_system: BaseGrid,
    bounds: Tuple[float, float, float, float],
    levels: List[int],
    detail_function: callable = None,
) -> gpd.GeoDataFrame:
    """Create an adaptive resolution grid."""
    multi_grid = MultiResolutionGrid(grid_system, levels)
    return multi_grid.create_level_of_detail_view(bounds, detail_function)
