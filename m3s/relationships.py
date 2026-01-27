"""Grid cell relationship analysis for M3S."""

from __future__ import annotations

from enum import Enum
from typing import Optional

import numpy as np
import pandas as pd
from shapely.geometry import Polygon
from shapely.ops import unary_union
from shapely.prepared import prep
from shapely.strtree import STRtree

from .core.cell import Cell
from .ops.area import polygon_area_km2


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
    """Analyze spatial relationships between grid cells."""

    def __init__(self, tolerance: float = 1e-9) -> None:
        self.tolerance = tolerance

    @staticmethod
    def _build_tree(cells: list[Cell]) -> tuple[STRtree, list[Polygon]]:
        polygons = [cell.polygon for cell in cells]
        return STRtree(polygons), polygons

    @staticmethod
    def _query_indices(
        tree: STRtree, polygons: list[Polygon], geometry: Polygon, predicate: str
    ) -> list[int]:
        try:
            return list(tree.query(geometry, predicate=predicate))
        except TypeError:
            candidates = tree.query(geometry)
            if predicate == "within":
                return [int(i) for i in candidates if polygons[int(i)].within(geometry)]
            if predicate == "intersects":
                return [int(i) for i in candidates if polygons[int(i)].intersects(geometry)]
            if predicate == "overlaps":
                return [int(i) for i in candidates if polygons[int(i)].overlaps(geometry)]
            if predicate == "touches":
                return [int(i) for i in candidates if polygons[int(i)].touches(geometry)]
            return [int(i) for i in candidates]

    def analyze_relationship(self, cell1: Cell, cell2: Cell) -> RelationshipType:
        geom1, geom2 = cell1.polygon, cell2.polygon
        if geom1.equals(geom2):
            return RelationshipType.EQUALS
        if geom1.contains(geom2):
            return RelationshipType.CONTAINS
        if geom1.within(geom2):
            return RelationshipType.WITHIN
        if geom1.overlaps(geom2):
            return RelationshipType.OVERLAPS
        if geom1.touches(geom2):
            return RelationshipType.TOUCHES
        if geom1.intersects(geom2):
            return RelationshipType.INTERSECTS
        return RelationshipType.DISJOINT

    def get_all_relationships(self, cell1: Cell, cell2: Cell) -> dict[str, bool]:
        geom1, geom2 = cell1.polygon, cell2.polygon
        relationships: dict[str, bool] = {}
        for rel_type in RelationshipType:
            method_name = rel_type.value
            if method_name == "adjacent":
                relationships[method_name] = self.is_adjacent(cell1, cell2)
            else:
                relationships[method_name] = getattr(geom1, method_name)(geom2)
        return relationships

    def is_adjacent(self, cell1: Cell, cell2: Cell) -> bool:
        return (
            cell1.polygon.touches(cell2.polygon)
            or cell1.polygon.intersects(cell2.polygon)
        ) and not cell1.polygon.overlaps(cell2.polygon)

    def find_contained_cells(self, container: Cell, cells: list[Cell]) -> list[Cell]:
        if not cells:
            return []
        tree, polygons = self._build_tree(cells)
        container_polygon = container.polygon
        prepared = prep(container_polygon)
        indices = self._query_indices(tree, polygons, container_polygon, "within")
        return [cells[i] for i in indices if prepared.contains(polygons[i])]

    def find_overlapping_cells(self, target: Cell, cells: list[Cell]) -> list[Cell]:
        if not cells:
            return []
        tree, polygons = self._build_tree(cells)
        target_polygon = target.polygon
        prepared = prep(target_polygon)
        indices = self._query_indices(tree, polygons, target_polygon, "intersects")
        return [cells[i] for i in indices if prepared.intersects(polygons[i])]

    def find_adjacent_cells(self, target: Cell, cells: list[Cell]) -> list[Cell]:
        if not cells:
            return []
        tree, polygons = self._build_tree(cells)
        target_polygon = target.polygon
        prepared = prep(target_polygon)
        indices = self._query_indices(tree, polygons, target_polygon, "intersects")
        return [
            cells[i]
            for i in indices
            if (prepared.touches(polygons[i]) or prepared.intersects(polygons[i]))
            and not prepared.overlaps(polygons[i])
        ]

    def create_relationship_matrix(self, cells: list[Cell]) -> pd.DataFrame:
        if not cells:
            return pd.DataFrame()
        tree, polygons = self._build_tree(cells)
        cell_ids = [cell.id for cell in cells]
        matrix_data: dict[str, list[str]] = {}
        n_cells = len(cells)
        for i, cell1 in enumerate(cells):
            relationships = [RelationshipType.DISJOINT.value] * n_cells
            relationships[i] = RelationshipType.EQUALS.value
            indices = self._query_indices(tree, polygons, polygons[i], "intersects")
            for j in indices:
                if i == j:
                    continue
                relationships[j] = self.analyze_relationship(cell1, cells[j]).value
            matrix_data[str(cell1.id)] = relationships
        return pd.DataFrame(matrix_data, index=cell_ids)

    def create_adjacency_matrix(self, cells: list[Cell]) -> pd.DataFrame:
        n_cells = len(cells)
        cell_ids = [cell.id for cell in cells]
        matrix = np.zeros((n_cells, n_cells), dtype=int)
        if n_cells == 0:
            return pd.DataFrame(matrix, index=cell_ids, columns=cell_ids)
        tree, polygons = self._build_tree(cells)
        for i, cell1 in enumerate(cells):
            indices = self._query_indices(tree, polygons, polygons[i], "intersects")
            for j in indices:
                if i != j and self.is_adjacent(cell1, cells[j]):
                    matrix[i][j] = 1
        return pd.DataFrame(matrix, index=cell_ids, columns=cell_ids)

    def get_topology_statistics(self, cells: list[Cell]) -> dict[str, int | float]:
        n_cells = len(cells)
        if n_cells == 0:
            return {}

        adjacency_matrix = self.create_adjacency_matrix(cells)
        adjacency_counts = adjacency_matrix.sum(axis=1)

        union_geom = unary_union([cell.polygon for cell in cells])
        total_area = sum(cell.area_km2 for cell in cells)
        union_area = polygon_area_km2(union_geom)

        return {
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

    def find_clusters(self, cells: list[Cell], min_cluster_size: int = 2) -> list[list[Cell]]:
        adjacency_dict = {cell.id: set() for cell in cells}
        cell_lookup = {cell.id: cell for cell in cells}
        if cells:
            tree, polygons = self._build_tree(cells)
            for i, cell1 in enumerate(cells):
                indices = self._query_indices(tree, polygons, polygons[i], "intersects")
                for j in indices:
                    if j <= i:
                        continue
                    cell2 = cells[j]
                    if self.is_adjacent(cell1, cell2):
                        adjacency_dict[cell1.id].add(cell2.id)
                        adjacency_dict[cell2.id].add(cell1.id)

        visited: set[object] = set()
        clusters: list[list[Cell]] = []

        def dfs(cell_id: object, current_cluster: list[object]) -> None:
            if cell_id in visited:
                return
            visited.add(cell_id)
            current_cluster.append(cell_id)
            for neighbor_id in adjacency_dict[cell_id]:
                if neighbor_id not in visited:
                    dfs(neighbor_id, current_cluster)

        for cell in cells:
            if cell.id not in visited:
                cluster: list[object] = []
                dfs(cell.id, cluster)
                if len(cluster) >= min_cluster_size:
                    clusters.append([cell_lookup[cell_id] for cell_id in cluster])

        return clusters

    def analyze_grid_coverage(
        self,
        cells: list[Cell],
        bounds: Optional[tuple[float, float, float, float]] = None,
    ) -> dict[str, float]:
        if not cells:
            return {"coverage_ratio": 0.0, "overlap_ratio": 0.0}

        union_geom = unary_union([cell.polygon for cell in cells])
        union_area = polygon_area_km2(union_geom)
        total_cell_area = sum(cell.area_km2 for cell in cells)

        if bounds is None:
            all_bounds = [cell.polygon.bounds for cell in cells]
            min_x = min(b[0] for b in all_bounds)
            min_y = min(b[1] for b in all_bounds)
            max_x = max(b[2] for b in all_bounds)
            max_y = max(b[3] for b in all_bounds)
            bounds = (min_x, min_y, max_x, max_y)

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
        bbox_area = polygon_area_km2(bbox_geom)

        coverage_ratio = union_area / bbox_area if bbox_area > 0 else 0
        overlap_ratio = (
            (total_cell_area - union_area) / total_cell_area
            if total_cell_area > 0
            else 0
        )

        return {
            "coverage_ratio": coverage_ratio,
            "overlap_ratio": overlap_ratio,
            "union_area_km2": union_area,
            "total_cell_area_km2": total_cell_area,
            "bbox_area_km2": bbox_area,
        }


_analyzer: Optional[GridRelationshipAnalyzer] = None


def get_analyzer() -> GridRelationshipAnalyzer:
    """Get or create the global analyzer instance."""
    global _analyzer
    if _analyzer is None:
        _analyzer = GridRelationshipAnalyzer()
    return _analyzer


def analyze_relationship(cell1: Cell, cell2: Cell) -> RelationshipType:
    """Analyze the primary spatial relationship between two cells."""
    return get_analyzer().analyze_relationship(cell1, cell2)


def is_adjacent(cell1: Cell, cell2: Cell) -> bool:
    """Check if two cells are adjacent."""
    return get_analyzer().is_adjacent(cell1, cell2)


def find_contained_cells(container: Cell, cells: list[Cell]) -> list[Cell]:
    """Find cells contained within a container cell."""
    return get_analyzer().find_contained_cells(container, cells)


def find_overlapping_cells(target: Cell, cells: list[Cell]) -> list[Cell]:
    """Find cells that overlap with a target cell."""
    return get_analyzer().find_overlapping_cells(target, cells)


def find_adjacent_cells(target: Cell, cells: list[Cell]) -> list[Cell]:
    """Find cells adjacent to a target cell."""
    return get_analyzer().find_adjacent_cells(target, cells)


def create_relationship_matrix(cells: list[Cell]) -> pd.DataFrame:
    """Create a relationship matrix for a collection of cells."""
    return get_analyzer().create_relationship_matrix(cells)


def create_adjacency_matrix(cells: list[Cell]) -> pd.DataFrame:
    """Create an adjacency matrix for a collection of cells."""
    return get_analyzer().create_adjacency_matrix(cells)


def find_cell_clusters(cells: list[Cell], min_cluster_size: int = 2) -> list[list[Cell]]:
    """Find clusters of connected cells."""
    return get_analyzer().find_clusters(cells, min_cluster_size)


def analyze_coverage(
    cells: list[Cell], bounds: Optional[tuple[float, float, float, float]] = None
) -> dict[str, float]:
    """Analyze how well cells cover a given area."""
    return get_analyzer().analyze_grid_coverage(cells, bounds)


analyzer = get_analyzer()
