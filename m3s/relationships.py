"""
Grid cell relationship analysis for M3S.

Provides functionality to analyze spatial relationships between grid cells,
including containment, overlap, adjacency, and topological operations.
"""

from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, Union

import numpy as np
import pandas as pd
from shapely.geometry import MultiPolygon, Polygon
from shapely.ops import unary_union

from .base import GridCell


class RelationshipType(Enum):
    """Enumeration of spatial relationship types."""

    CONTAINS = "contains"
    WITHIN = "within"
    OVERLAPS = "overlaps"
    TOUCHES = "touches"
    ADJACENT = "adjacent"
    DISJOINT = "disjoint"
    INTERSECTS = "intersects"
    EQUALS = "equals"


class GridRelationshipAnalyzer:
    """
    Analyzer for spatial relationships between grid cells.

    Provides methods to determine various spatial relationships between
    individual cells, cell collections, and across different grid systems.
    """

    def __init__(self, tolerance: float = 1e-9):
        """
        Initialize the relationship analyzer.

        Parameters
        ----------
        tolerance : float, optional
            Geometric tolerance for spatial operations, by default 1e-9
        """
        self.tolerance = tolerance

    def analyze_relationship(
        self, cell1: GridCell, cell2: GridCell
    ) -> RelationshipType:
        """
        Analyze the primary spatial relationship between two grid cells.

        Parameters
        ----------
        cell1 : GridCell
            First grid cell
        cell2 : GridCell
            Second grid cell

        Returns
        -------
        RelationshipType
            Primary spatial relationship
        """
        geom1, geom2 = cell1.polygon, cell2.polygon

        # Check in order of specificity
        if geom1.equals(geom2):
            return RelationshipType.EQUALS
        elif geom1.contains(geom2):
            return RelationshipType.CONTAINS
        elif geom1.within(geom2):
            return RelationshipType.WITHIN
        elif geom1.overlaps(geom2):
            return RelationshipType.OVERLAPS
        elif geom1.touches(geom2):
            return RelationshipType.TOUCHES
        elif geom1.intersects(geom2):
            return RelationshipType.INTERSECTS
        else:
            return RelationshipType.DISJOINT

    def get_all_relationships(
        self, cell1: GridCell, cell2: GridCell
    ) -> Dict[str, bool]:
        """
        Get all spatial relationships between two grid cells.

        Parameters
        ----------
        cell1 : GridCell
            First grid cell
        cell2 : GridCell
            Second grid cell

        Returns
        -------
        Dict[str, bool]
            Dictionary mapping relationship names to boolean values
        """
        geom1, geom2 = cell1.polygon, cell2.polygon

        relationships = {}
        for rel_type in RelationshipType:
            method_name = rel_type.value
            if method_name == "adjacent":
                # Custom adjacency check
                relationships[method_name] = self.is_adjacent(cell1, cell2)
            else:
                relationships[method_name] = getattr(geom1, method_name)(geom2)

        return relationships

    def is_adjacent(self, cell1: GridCell, cell2: GridCell) -> bool:
        """
        Check if two grid cells are adjacent (share an edge or vertex).

        Parameters
        ----------
        cell1 : GridCell
            First grid cell
        cell2 : GridCell
            Second grid cell

        Returns
        -------
        bool
            True if cells are adjacent
        """
        # Adjacent cells touch but don't overlap
        return (
            cell1.polygon.touches(cell2.polygon)
            or cell1.polygon.intersects(cell2.polygon)
        ) and not cell1.polygon.overlaps(cell2.polygon)

    def find_contained_cells(
        self, container: GridCell, cells: List[GridCell]
    ) -> List[GridCell]:
        """
        Find all cells that are contained within a container cell.

        Parameters
        ----------
        container : GridCell
            Container cell
        cells : List[GridCell]
            List of cells to check

        Returns
        -------
        List[GridCell]
            List of contained cells
        """
        contained = []
        for cell in cells:
            if container.polygon.contains(cell.polygon):
                contained.append(cell)
        return contained

    def find_overlapping_cells(
        self, target: GridCell, cells: List[GridCell]
    ) -> List[GridCell]:
        """
        Find all cells that overlap with a target cell.

        Parameters
        ----------
        target : GridCell
            Target cell
        cells : List[GridCell]
            List of cells to check

        Returns
        -------
        List[GridCell]
            List of overlapping cells
        """
        overlapping = []
        for cell in cells:
            if target.polygon.overlaps(cell.polygon) or target.polygon.intersects(
                cell.polygon
            ):
                overlapping.append(cell)
        return overlapping

    def find_adjacent_cells(
        self, target: GridCell, cells: List[GridCell]
    ) -> List[GridCell]:
        """
        Find all cells that are adjacent to a target cell.

        Parameters
        ----------
        target : GridCell
            Target cell
        cells : List[GridCell]
            List of cells to check

        Returns
        -------
        List[GridCell]
            List of adjacent cells
        """
        adjacent = []
        for cell in cells:
            if self.is_adjacent(target, cell):
                adjacent.append(cell)
        return adjacent

    def create_relationship_matrix(self, cells: List[GridCell]) -> pd.DataFrame:
        """
        Create a relationship matrix for a collection of cells.

        Parameters
        ----------
        cells : List[GridCell]
            List of grid cells

        Returns
        -------
        pd.DataFrame
            Matrix showing relationships between all cell pairs
        """
        len(cells)
        cell_ids = [cell.identifier for cell in cells]

        # Initialize matrix with relationship types
        matrix_data = {}

        for i, cell1 in enumerate(cells):
            relationships = []
            for j, cell2 in enumerate(cells):
                if i == j:
                    relationships.append(RelationshipType.EQUALS.value)
                else:
                    rel = self.analyze_relationship(cell1, cell2)
                    relationships.append(rel.value)
            matrix_data[cell1.identifier] = relationships

        df = pd.DataFrame(matrix_data, index=cell_ids)
        return df

    def create_adjacency_matrix(self, cells: List[GridCell]) -> pd.DataFrame:
        """
        Create an adjacency matrix for a collection of cells.

        Parameters
        ----------
        cells : List[GridCell]
            List of grid cells

        Returns
        -------
        pd.DataFrame
            Binary adjacency matrix
        """
        n_cells = len(cells)
        cell_ids = [cell.identifier for cell in cells]

        matrix = np.zeros((n_cells, n_cells), dtype=int)

        for i, cell1 in enumerate(cells):
            for j, cell2 in enumerate(cells):
                if i != j and self.is_adjacent(cell1, cell2):
                    matrix[i][j] = 1

        df = pd.DataFrame(matrix, index=cell_ids, columns=cell_ids)
        return df

    def get_topology_statistics(
        self, cells: List[GridCell]
    ) -> Dict[str, Union[int, float]]:
        """
        Calculate topological statistics for a collection of cells.

        Parameters
        ----------
        cells : List[GridCell]
            List of grid cells

        Returns
        -------
        Dict[str, Union[int, float]]
            Dictionary of topology statistics
        """
        n_cells = len(cells)
        if n_cells == 0:
            return {}

        adjacency_matrix = self.create_adjacency_matrix(cells)
        adjacency_counts = adjacency_matrix.sum(axis=1)

        # Calculate union and coverage
        union_geom = unary_union([cell.polygon for cell in cells])
        total_area = sum(cell.area_km2 for cell in cells)
        union_area = self._calculate_area_km2(union_geom)

        stats = {
            "total_cells": n_cells,
            "total_area_km2": total_area,
            "union_area_km2": union_area,
            "overlap_ratio": (
                (total_area - union_area) / total_area if total_area > 0 else 0
            ),
            "avg_neighbors": float(adjacency_counts.mean()),
            "max_neighbors": int(adjacency_counts.max()),
            "min_neighbors": int(adjacency_counts.min()),
            "isolated_cells": int((adjacency_counts == 0).sum()),
            "connectivity": (
                float(adjacency_counts.sum()) / (n_cells * (n_cells - 1))
                if n_cells > 1
                else 0
            ),
        }

        return stats

    def _calculate_area_km2(self, geometry: Union[Polygon, MultiPolygon]) -> float:
        """
        Calculate area of a geometry in square kilometers.

        Parameters
        ----------
        geometry : Polygon or MultiPolygon
            Geometry to calculate area for

        Returns
        -------
        float
            Area in square kilometers
        """
        # Simple approximation - in practice would use proper projection
        bounds = geometry.bounds
        lat_center = (bounds[1] + bounds[3]) / 2

        # Rough conversion factor at given latitude
        deg_to_km = 111.32  # km per degree at equator
        lat_correction = np.cos(np.radians(lat_center))

        # Convert area from square degrees to square kilometers
        area_deg2 = geometry.area
        area_km2 = area_deg2 * (deg_to_km**2) * lat_correction

        return area_km2

    def find_clusters(
        self, cells: List[GridCell], min_cluster_size: int = 2
    ) -> List[List[GridCell]]:
        """
        Find clusters of connected (adjacent) cells.

        Parameters
        ----------
        cells : List[GridCell]
            List of grid cells
        min_cluster_size : int, optional
            Minimum cluster size, by default 2

        Returns
        -------
        List[List[GridCell]]
            List of cell clusters
        """
        # Build adjacency graph
        adjacency_dict: Dict[str, Set[str]] = {cell.identifier: set() for cell in cells}
        cell_lookup = {cell.identifier: cell for cell in cells}

        for i, cell1 in enumerate(cells):
            for _j, cell2 in enumerate(cells[i + 1 :], i + 1):
                if self.is_adjacent(cell1, cell2):
                    adjacency_dict[cell1.identifier].add(cell2.identifier)
                    adjacency_dict[cell2.identifier].add(cell1.identifier)

        # Find connected components using DFS
        visited = set()
        clusters = []

        def dfs(cell_id: str, current_cluster: List[str]):
            if cell_id in visited:
                return
            visited.add(cell_id)
            current_cluster.append(cell_id)

            for neighbor_id in adjacency_dict[cell_id]:
                if neighbor_id not in visited:
                    dfs(neighbor_id, current_cluster)

        for cell in cells:
            if cell.identifier not in visited:
                cluster: List[str] = []
                dfs(cell.identifier, cluster)
                if len(cluster) >= min_cluster_size:
                    clusters.append([cell_lookup[cell_id] for cell_id in cluster])

        return clusters

    def analyze_grid_coverage(
        self,
        cells: List[GridCell],
        bounds: Optional[Tuple[float, float, float, float]] = None,
    ) -> Dict[str, float]:
        """
        Analyze how well cells cover a given area.

        Parameters
        ----------
        cells : List[GridCell]
            List of grid cells
        bounds : Tuple[float, float, float, float], optional
            Bounding box as (min_lon, min_lat, max_lon, max_lat)
            If None, uses cells' bounding box

        Returns
        -------
        Dict[str, float]
            Coverage statistics
        """
        if not cells:
            return {"coverage_ratio": 0.0, "overlap_ratio": 0.0}

        # Calculate union of all cells
        union_geom = unary_union([cell.polygon for cell in cells])
        union_area = self._calculate_area_km2(union_geom)

        # Calculate total area of individual cells
        total_cell_area = sum(self._calculate_area_km2(cell.polygon) for cell in cells)

        if bounds is None:
            # Use cells' bounding box
            all_bounds = [cell.polygon.bounds for cell in cells]
            min_x = min(b[0] for b in all_bounds)
            min_y = min(b[1] for b in all_bounds)
            max_x = max(b[2] for b in all_bounds)
            max_y = max(b[3] for b in all_bounds)
            bounds = (min_x, min_y, max_x, max_y)

        # Create bounding box polygon
        min_lon, min_lat, max_lon, max_lat = bounds
        bbox_geom = Polygon(
            [
                (min_lon, min_lat),
                (max_lon, min_lat),
                (max_lon, max_lat),
                (min_lon, max_lat),
                (min_lon, min_lat),
            ]
        )

        bbox_area = self._calculate_area_km2(bbox_geom)

        # Calculate coverage and overlap ratios
        coverage_ratio = union_area / bbox_area if bbox_area > 0 else 0
        overlap_ratio = (
            (total_cell_area - union_area) / total_cell_area
            if total_cell_area > 0
            else 0
        )
        overlap_ratio = max(0.0, overlap_ratio)

        return {
            "coverage_ratio": coverage_ratio,
            "overlap_ratio": overlap_ratio,
            "union_area_km2": union_area,
            "total_cell_area_km2": total_cell_area,
            "bbox_area_km2": bbox_area,
        }


# Global analyzer instance
analyzer = GridRelationshipAnalyzer()


# Convenience functions
def analyze_relationship(cell1: GridCell, cell2: GridCell) -> RelationshipType:
    """Analyze the primary spatial relationship between two cells."""
    return analyzer.analyze_relationship(cell1, cell2)


def is_adjacent(cell1: GridCell, cell2: GridCell) -> bool:
    """Check if two cells are adjacent."""
    return analyzer.is_adjacent(cell1, cell2)


def find_contained_cells(container: GridCell, cells: List[GridCell]) -> List[GridCell]:
    """Find cells contained within a container cell."""
    return analyzer.find_contained_cells(container, cells)


def find_overlapping_cells(target: GridCell, cells: List[GridCell]) -> List[GridCell]:
    """Find cells that overlap with a target cell."""
    return analyzer.find_overlapping_cells(target, cells)


def find_adjacent_cells(target: GridCell, cells: List[GridCell]) -> List[GridCell]:
    """Find cells adjacent to a target cell."""
    return analyzer.find_adjacent_cells(target, cells)


def create_relationship_matrix(cells: List[GridCell]) -> pd.DataFrame:
    """Create a relationship matrix for a collection of cells."""
    return analyzer.create_relationship_matrix(cells)


def create_adjacency_matrix(cells: List[GridCell]) -> pd.DataFrame:
    """Create an adjacency matrix for a collection of cells."""
    return analyzer.create_adjacency_matrix(cells)


def find_cell_clusters(
    cells: List[GridCell], min_cluster_size: int = 2
) -> List[List[GridCell]]:
    """Find clusters of connected cells."""
    return analyzer.find_clusters(cells, min_cluster_size)


def analyze_coverage(
    cells: List[GridCell], bounds: Optional[Tuple[float, float, float, float]] = None
) -> Dict[str, float]:
    """Analyze how well cells cover a given area."""
    return analyzer.analyze_grid_coverage(cells, bounds)
