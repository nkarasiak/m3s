"""
Tests for grid cell relationship analysis.
"""

import pandas as pd
from shapely.geometry import Polygon

from m3s.base import GridCell
from m3s.relationships import (
    GridRelationshipAnalyzer,
    RelationshipType,
    analyze_relationship,
    create_adjacency_matrix,
    is_adjacent,
)


class TestGridRelationshipAnalyzer:
    """Test relationship analysis functionality."""

    def test_initialization(self):
        """Test analyzer initialization."""
        analyzer = GridRelationshipAnalyzer()
        assert analyzer.tolerance == 1e-9

        # Test custom tolerance
        custom_analyzer = GridRelationshipAnalyzer(tolerance=1e-6)
        assert custom_analyzer.tolerance == 1e-6

    def test_analyze_relationship_equals(self):
        """Test relationship analysis for equal cells."""
        analyzer = GridRelationshipAnalyzer()

        # Create identical cells
        polygon = Polygon([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)])
        cell1 = GridCell("test1", polygon, 5)
        cell2 = GridCell("test2", polygon, 5)

        relationship = analyzer.analyze_relationship(cell1, cell2)
        assert relationship == RelationshipType.EQUALS

    def test_analyze_relationship_contains(self):
        """Test relationship analysis for containment."""
        analyzer = GridRelationshipAnalyzer()

        # Create container and contained cells
        large_polygon = Polygon([(0, 0), (2, 0), (2, 2), (0, 2), (0, 0)])
        small_polygon = Polygon(
            [(0.5, 0.5), (1.5, 0.5), (1.5, 1.5), (0.5, 1.5), (0.5, 0.5)]
        )

        large_cell = GridCell("large", large_polygon, 3)
        small_cell = GridCell("small", small_polygon, 5)

        relationship = analyzer.analyze_relationship(large_cell, small_cell)
        assert relationship == RelationshipType.CONTAINS

    def test_analyze_relationship_touches(self):
        """Test relationship analysis for touching cells."""
        analyzer = GridRelationshipAnalyzer()

        # Create touching cells
        cell1_polygon = Polygon([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)])
        cell2_polygon = Polygon([(1, 0), (2, 0), (2, 1), (1, 1), (1, 0)])

        cell1 = GridCell("cell1", cell1_polygon, 5)
        cell2 = GridCell("cell2", cell2_polygon, 5)

        relationship = analyzer.analyze_relationship(cell1, cell2)
        assert relationship == RelationshipType.TOUCHES

    def test_analyze_relationship_disjoint(self):
        """Test relationship analysis for disjoint cells."""
        analyzer = GridRelationshipAnalyzer()

        # Create disjoint cells
        cell1_polygon = Polygon([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)])
        cell2_polygon = Polygon([(2, 2), (3, 2), (3, 3), (2, 3), (2, 2)])

        cell1 = GridCell("cell1", cell1_polygon, 5)
        cell2 = GridCell("cell2", cell2_polygon, 5)

        relationship = analyzer.analyze_relationship(cell1, cell2)
        assert relationship == RelationshipType.DISJOINT

    def test_get_all_relationships(self):
        """Test getting all relationships between two cells."""
        analyzer = GridRelationshipAnalyzer()

        # Create touching cells
        cell1_polygon = Polygon([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)])
        cell2_polygon = Polygon([(1, 0), (2, 0), (2, 1), (1, 1), (1, 0)])

        cell1 = GridCell("cell1", cell1_polygon, 5)
        cell2 = GridCell("cell2", cell2_polygon, 5)

        relationships = analyzer.get_all_relationships(cell1, cell2)

        assert isinstance(relationships, dict)
        assert "touches" in relationships
        assert "adjacent" in relationships
        assert relationships["touches"] is True
        assert relationships["adjacent"] is True
        assert relationships["contains"] is False

    def test_is_adjacent(self):
        """Test adjacency checking."""
        analyzer = GridRelationshipAnalyzer()

        # Create adjacent cells
        cell1_polygon = Polygon([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)])
        cell2_polygon = Polygon([(1, 0), (2, 0), (2, 1), (1, 1), (1, 0)])

        cell1 = GridCell("cell1", cell1_polygon, 5)
        cell2 = GridCell("cell2", cell2_polygon, 5)

        assert analyzer.is_adjacent(cell1, cell2)

    def test_find_contained_cells(self):
        """Test finding contained cells."""
        analyzer = GridRelationshipAnalyzer()

        # Create container and potential contained cells
        container_polygon = Polygon([(0, 0), (3, 0), (3, 3), (0, 3), (0, 0)])
        container_cell = GridCell("container", container_polygon, 3)

        # Small cells, some inside, some outside
        cells = [
            GridCell(
                "inside1",
                Polygon([(0.5, 0.5), (1.5, 0.5), (1.5, 1.5), (0.5, 1.5), (0.5, 0.5)]),
                5,
            ),
            GridCell(
                "inside2",
                Polygon([(1.5, 1.5), (2.5, 1.5), (2.5, 2.5), (1.5, 2.5), (1.5, 1.5)]),
                5,
            ),
            GridCell("outside", Polygon([(4, 4), (5, 4), (5, 5), (4, 5), (4, 4)]), 5),
        ]

        contained = analyzer.find_contained_cells(container_cell, cells)
        assert len(contained) == 2
        assert all(cell.identifier.startswith("inside") for cell in contained)

    def test_create_relationship_matrix(self):
        """Test creating relationship matrix."""
        analyzer = GridRelationshipAnalyzer()

        # Create test cells
        cells = [
            GridCell("cell1", Polygon([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)]), 5),
            GridCell("cell2", Polygon([(1, 0), (2, 0), (2, 1), (1, 1), (1, 0)]), 5),
            GridCell("cell3", Polygon([(0, 1), (1, 1), (1, 2), (0, 2), (0, 1)]), 5),
        ]

        matrix = analyzer.create_relationship_matrix(cells)

        assert isinstance(matrix, pd.DataFrame)
        assert matrix.shape == (3, 3)
        assert list(matrix.index) == [cell.identifier for cell in cells]
        assert list(matrix.columns) == [cell.identifier for cell in cells]

        # Diagonal should be 'equals'
        for i in range(len(cells)):
            assert matrix.iloc[i, i] == RelationshipType.EQUALS.value

    def test_create_adjacency_matrix(self):
        """Test creating adjacency matrix."""
        analyzer = GridRelationshipAnalyzer()

        # Create adjacent cells
        cells = [
            GridCell("cell1", Polygon([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)]), 5),
            GridCell("cell2", Polygon([(1, 0), (2, 0), (2, 1), (1, 1), (1, 0)]), 5),
            GridCell(
                "cell3", Polygon([(2, 2), (3, 2), (3, 3), (2, 3), (2, 2)]), 5
            ),  # Not adjacent
        ]

        matrix = analyzer.create_adjacency_matrix(cells)

        assert isinstance(matrix, pd.DataFrame)
        assert matrix.shape == (3, 3)
        assert pd.api.types.is_integer_dtype(matrix.dtypes.iloc[0])

        # Check adjacency
        assert matrix.loc["cell1", "cell2"] == 1  # Adjacent
        assert matrix.loc["cell2", "cell1"] == 1  # Symmetric
        assert matrix.loc["cell1", "cell3"] == 0  # Not adjacent

        # Diagonal should be 0 (cell not adjacent to itself)
        for i in range(len(cells)):
            assert matrix.iloc[i, i] == 0

    def test_get_topology_statistics(self):
        """Test topology statistics calculation."""
        analyzer = GridRelationshipAnalyzer()

        # Create test cells
        cells = [
            GridCell("cell1", Polygon([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)]), 5),
            GridCell("cell2", Polygon([(1, 0), (2, 0), (2, 1), (1, 1), (1, 0)]), 5),
            GridCell("cell3", Polygon([(0, 1), (1, 1), (1, 2), (0, 2), (0, 1)]), 5),
        ]

        stats = analyzer.get_topology_statistics(cells)

        assert isinstance(stats, dict)
        assert "total_cells" in stats
        assert "avg_neighbors" in stats
        assert "connectivity" in stats
        assert stats["total_cells"] == 3
        assert isinstance(stats["avg_neighbors"], float)

    def test_find_clusters(self):
        """Test finding cell clusters."""
        analyzer = GridRelationshipAnalyzer()

        # Create two separate clusters
        cluster1_cells = [
            GridCell("c1_1", Polygon([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)]), 5),
            GridCell("c1_2", Polygon([(1, 0), (2, 0), (2, 1), (1, 1), (1, 0)]), 5),
        ]

        cluster2_cells = [
            GridCell("c2_1", Polygon([(5, 5), (6, 5), (6, 6), (5, 6), (5, 5)]), 5),
            GridCell("c2_2", Polygon([(6, 5), (7, 5), (7, 6), (6, 6), (6, 5)]), 5),
        ]

        isolated_cell = [
            GridCell(
                "isolated",
                Polygon([(10, 10), (11, 10), (11, 11), (10, 11), (10, 10)]),
                5,
            )
        ]

        all_cells = cluster1_cells + cluster2_cells + isolated_cell

        clusters = analyzer.find_clusters(all_cells, min_cluster_size=2)

        assert len(clusters) == 2  # Two clusters, isolated cell filtered out
        assert all(len(cluster) >= 2 for cluster in clusters)

    def test_analyze_grid_coverage(self):
        """Test grid coverage analysis."""
        analyzer = GridRelationshipAnalyzer()

        # Create cells that cover part of a bounding box
        cells = [
            GridCell("cell1", Polygon([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)]), 5),
            GridCell("cell2", Polygon([(1, 0), (2, 0), (2, 1), (1, 1), (1, 0)]), 5),
        ]

        # Define bounding box larger than cells
        bounds = (0, 0, 3, 1)

        coverage = analyzer.analyze_grid_coverage(cells, bounds)

        assert isinstance(coverage, dict)
        assert "coverage_ratio" in coverage
        assert "overlap_ratio" in coverage
        assert 0 <= coverage["coverage_ratio"] <= 1
        assert coverage["overlap_ratio"] >= 0

    def test_convenience_functions(self):
        """Test convenience functions."""
        # Create test cells
        cell1 = GridCell("cell1", Polygon([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)]), 5)
        cell2 = GridCell("cell2", Polygon([(1, 0), (2, 0), (2, 1), (1, 1), (1, 0)]), 5)

        # Test convenience functions
        rel = analyze_relationship(cell1, cell2)
        assert isinstance(rel, RelationshipType)

        adj = is_adjacent(cell1, cell2)
        assert isinstance(adj, bool)

        matrix = create_adjacency_matrix([cell1, cell2])
        assert isinstance(matrix, pd.DataFrame)

    def test_empty_cell_list(self):
        """Test behavior with empty cell list."""
        analyzer = GridRelationshipAnalyzer()

        stats = analyzer.get_topology_statistics([])
        assert stats == {}

        clusters = analyzer.find_clusters([])
        assert clusters == []
