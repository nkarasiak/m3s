"""
Tests for multi-resolution grid operations.
"""

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import Point, Polygon

from m3s.base import GridCell
from m3s.geohash import GeohashGrid
from m3s.multiresolution import (
    MultiResolutionGrid,
    create_multiresolution_grid,
)


class TestMultiResolutionGrid:
    """Test multi-resolution grid functionality."""

    def test_initialization(self):
        """Test multi-resolution grid initialization."""
        base_grid = GeohashGrid(precision=5)
        levels = [3, 5, 7]

        multi_grid = MultiResolutionGrid(base_grid, levels)

        assert multi_grid.resolution_levels == [3, 5, 7]
        assert len(multi_grid.grids) == 3
        assert len(multi_grid.levels) == 3

        # Check that grids have correct precisions
        assert multi_grid.grids[3].precision == 3
        assert multi_grid.grids[5].precision == 5
        assert multi_grid.grids[7].precision == 7

    def test_populate_region(self):
        """Test populating region with cells."""
        base_grid = GeohashGrid(precision=5)
        levels = [4, 5, 6]

        multi_grid = MultiResolutionGrid(base_grid, levels)

        # Small bounding box around NYC
        bounds = (-74.01, 40.71, -74.00, 40.72)
        result = multi_grid.populate_region(bounds)

        assert isinstance(result, dict)
        assert len(result) == 3

        for precision in levels:
            assert precision in result
            assert isinstance(result[precision], list)
            assert len(result[precision]) > 0
            assert all(isinstance(cell, GridCell) for cell in result[precision])

    def test_get_hierarchical_cells(self):
        """Test getting hierarchical cells for a point."""
        base_grid = GeohashGrid(precision=5)
        levels = [4, 5, 6]

        multi_grid = MultiResolutionGrid(base_grid, levels)

        point = Point(-74.0060, 40.7128)  # NYC
        hierarchical_cells = multi_grid.get_hierarchical_cells(point)

        assert isinstance(hierarchical_cells, dict)
        assert len(hierarchical_cells) == 3

        for precision in levels:
            assert precision in hierarchical_cells
            cell = hierarchical_cells[precision]
            assert isinstance(cell, GridCell)
            assert cell.precision == precision
            assert cell.polygon.contains(point)

    def test_get_hierarchical_cells_max_levels(self):
        """Test getting hierarchical cells with max_levels limit."""
        base_grid = GeohashGrid(precision=5)
        levels = [4, 5, 6, 7]

        multi_grid = MultiResolutionGrid(base_grid, levels)

        point = Point(-74.0060, 40.7128)
        hierarchical_cells = multi_grid.get_hierarchical_cells(point, max_levels=2)

        assert len(hierarchical_cells) == 2
        assert 4 in hierarchical_cells
        assert 5 in hierarchical_cells
        assert 6 not in hierarchical_cells

    def test_get_parent_child_relationships(self):
        """Test parent-child relationship analysis."""
        base_grid = GeohashGrid(precision=5)
        levels = [4, 5]  # Two levels for simpler testing

        multi_grid = MultiResolutionGrid(base_grid, levels)

        # Small bounding box
        bounds = (-74.01, 40.71, -74.00, 40.72)
        relationships = multi_grid.get_parent_child_relationships(bounds)

        assert isinstance(relationships, dict)
        # Should have some parent-child relationships
        if relationships:  # May be empty for very small regions
            for parent_id, children_ids in relationships.items():
                assert isinstance(parent_id, str)
                assert isinstance(children_ids, list)
                assert all(isinstance(child_id, str) for child_id in children_ids)

    def test_create_level_of_detail_view(self):
        """Test creating level-of-detail view."""
        base_grid = GeohashGrid(precision=5)
        levels = [4, 5, 6]

        multi_grid = MultiResolutionGrid(base_grid, levels)

        bounds = (-74.01, 40.71, -74.00, 40.72)
        lod_view = multi_grid.create_level_of_detail_view(bounds)

        assert isinstance(lod_view, gpd.GeoDataFrame)
        if len(lod_view) > 0:  # May be empty for small regions
            assert "cell_id" in lod_view.columns
            assert "precision" in lod_view.columns
            assert "area_km2" in lod_view.columns
            assert "geometry" in lod_view.columns

    def test_analyze_scale_transitions(self):
        """Test scale transition analysis."""
        base_grid = GeohashGrid(precision=5)
        levels = [4, 5, 6]

        multi_grid = MultiResolutionGrid(base_grid, levels)

        bounds = (-74.01, 40.71, -74.00, 40.72)
        transitions = multi_grid.analyze_scale_transitions(bounds)

        assert isinstance(transitions, pd.DataFrame)
        expected_cols = [
            "from_precision",
            "to_precision",
            "from_level",
            "to_level",
            "subdivision_ratio",
            "area_ratio",
        ]
        for col in expected_cols:
            assert col in transitions.columns

    def test_aggregate_to_level(self):
        """Test aggregating data to coarser level."""
        base_grid = GeohashGrid(precision=5)
        levels = [4, 5, 6]

        multi_grid = MultiResolutionGrid(base_grid, levels)

        # Create test data with fine resolution cells
        fine_cells = multi_grid.grids[6].get_cells_in_bbox(40.71, -74.01, 40.72, -74.00)

        if fine_cells:  # Only test if we have cells
            data_rows = []
            for i, cell in enumerate(fine_cells[:5]):  # Limit for testing
                data_rows.append(
                    {
                        "cell_id": cell.identifier,
                        "value": i + 1,
                        "geometry": cell.polygon,
                    }
                )

            test_data = gpd.GeoDataFrame(data_rows)
            test_data.crs = "EPSG:4326"

            # Aggregate to coarser level
            aggregated = multi_grid.aggregate_to_level(
                test_data, target_level=0
            )  # Level 0 = precision 4

            assert isinstance(aggregated, gpd.GeoDataFrame)
            if len(aggregated) > 0:
                assert "cell_id" in aggregated.columns
                assert "value" in aggregated.columns
                assert "contributing_cells" in aggregated.columns

    def test_get_resolution_statistics(self):
        """Test getting resolution statistics."""
        base_grid = GeohashGrid(precision=5)
        levels = [4, 5, 6]

        multi_grid = MultiResolutionGrid(base_grid, levels)

        stats = multi_grid.get_resolution_statistics()

        assert isinstance(stats, pd.DataFrame)
        assert len(stats) == 3
        assert "level" in stats.columns
        assert "precision" in stats.columns
        assert "area_km2" in stats.columns
        assert "grid_type" in stats.columns

        # Check that areas decrease with increasing precision
        areas = stats.sort_values("level")["area_km2"].values
        assert areas[0] > areas[1] > areas[2]  # Coarser levels have larger areas

    def test_create_quad_tree_structure(self):
        """Test creating quad-tree structure."""
        base_grid = GeohashGrid(precision=5)
        levels = [4, 5]  # Two levels for simpler testing

        multi_grid = MultiResolutionGrid(base_grid, levels)

        bounds = (-74.01, 40.71, -74.00, 40.72)
        tree = multi_grid.create_quad_tree_structure(bounds)

        assert isinstance(tree, dict)
        assert "level" in tree
        assert "precision" in tree
        assert "cells" in tree
        assert "children" in tree
        assert tree["level"] == 0
        assert tree["precision"] == 4  # Coarsest level

    def test_adaptive_filtering(self):
        """Test adaptive filtering functionality."""
        base_grid = GeohashGrid(precision=5)
        levels = [4, 5, 6]

        multi_grid = MultiResolutionGrid(base_grid, levels)

        # Create test cells
        test_cells = []
        for i in range(10):
            polygon = Polygon([(i, 0), (i + 1, 0), (i + 1, 1), (i, 1), (i, 0)])
            test_cells.append(GridCell(f"cell_{i}", polygon, 5))

        # Apply adaptive filtering
        filtered = multi_grid._apply_adaptive_filtering(test_cells, density_threshold=5)

        assert len(filtered) <= len(test_cells)
        assert len(filtered) <= 5  # Should respect threshold

    def test_default_detail_function(self):
        """Test default detail function."""
        base_grid = GeohashGrid(precision=5)
        levels = [4, 5, 6]

        multi_grid = MultiResolutionGrid(base_grid, levels)

        # Create test cells with different areas
        large_cell = GridCell(
            "large", Polygon([(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)]), 3
        )
        medium_cell = GridCell(
            "medium", Polygon([(0, 0), (5, 0), (5, 5), (0, 5), (0, 0)]), 4
        )
        small_cell = GridCell(
            "small", Polygon([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)]), 5
        )

        # Test detail function
        large_detail = multi_grid._default_detail_function(large_cell)
        medium_detail = multi_grid._default_detail_function(medium_cell)
        small_detail = multi_grid._default_detail_function(small_cell)

        assert isinstance(large_detail, int)
        assert isinstance(medium_detail, int)
        assert isinstance(small_detail, int)
        assert large_detail <= medium_detail <= small_detail

    def test_convenience_functions(self):
        """Test convenience functions."""
        base_grid = GeohashGrid(precision=5)
        levels = [4, 5, 6]

        # Test create_multiresolution_grid
        multi_grid = create_multiresolution_grid(base_grid, levels)
        assert isinstance(multi_grid, MultiResolutionGrid)

        # Test get_hierarchical_cells convenience function
        from m3s.multiresolution import get_hierarchical_cells

        point = Point(-74.0060, 40.7128)
        hierarchical = get_hierarchical_cells(multi_grid, point)
        assert isinstance(hierarchical, dict)

    def test_empty_bounds(self):
        """Test behavior with empty bounds."""
        base_grid = GeohashGrid(precision=5)
        levels = [4, 5, 6]

        multi_grid = MultiResolutionGrid(base_grid, levels)

        # Very small bounds that might not contain any cells
        bounds = (-74.00001, 40.71001, -74.00000, 40.71000)
        result = multi_grid.populate_region(bounds)

        # Should still return dict with all levels, even if empty
        assert isinstance(result, dict)
        assert len(result) == 3
        for precision in levels:
            assert precision in result
            assert isinstance(result[precision], list)

    def test_invalid_target_level(self):
        """Test error handling for invalid target level."""
        base_grid = GeohashGrid(precision=5)
        levels = [4, 5, 6]

        multi_grid = MultiResolutionGrid(base_grid, levels)

        # Create dummy data
        test_data = gpd.GeoDataFrame(
            {"value": [1], "geometry": [Point(0, 0).buffer(0.1)]}
        )

        with pytest.raises(ValueError):
            multi_grid.aggregate_to_level(test_data, target_level=10)  # Invalid level
