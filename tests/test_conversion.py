"""
Tests for grid conversion utilities.
"""

import pandas as pd
import pytest

from m3s.base import GridCell
from m3s.conversion import (
    GridConverter,
    convert_cell,
    convert_cells,
    get_equivalent_precision,
)
from m3s.geohash import GeohashGrid
from m3s.h3 import H3Grid


class TestGridConverter:
    """Test grid conversion functionality."""

    def test_initialization(self):
        """Test converter initialization."""
        converter = GridConverter()
        assert len(converter.GRID_SYSTEMS) > 0
        assert "geohash" in converter.GRID_SYSTEMS
        assert "h3" in converter.GRID_SYSTEMS

    def test_get_grid(self):
        """Test getting grid instances."""
        converter = GridConverter()

        # Test with default precision
        geohash_grid = converter._get_grid("geohash")
        assert isinstance(geohash_grid, GeohashGrid)
        assert geohash_grid.precision == 5  # default

        # Test with custom precision
        h3_grid = converter._get_grid("h3", 8)
        assert isinstance(h3_grid, H3Grid)
        assert h3_grid.resolution == 8

    def test_get_grid_invalid_system(self):
        """Test error for invalid grid system."""
        converter = GridConverter()
        with pytest.raises(ValueError):
            converter._get_grid("invalid_system")

    def test_convert_cell_centroid_method(self):
        """Test cell conversion using centroid method."""
        converter = GridConverter()

        # Create a source cell
        geohash_grid = GeohashGrid(precision=5)
        source_cell = geohash_grid.get_cell_from_point(40.7128, -74.0060)

        # Convert to H3
        target_cell = converter.convert_cell(source_cell, "h3", method="centroid")
        assert isinstance(target_cell, GridCell)
        assert target_cell.precision == 7  # default H3 resolution

    def test_convert_cell_overlap_method(self):
        """Test cell conversion using overlap method."""
        converter = GridConverter()

        # Create a source cell
        geohash_grid = GeohashGrid(precision=5)
        source_cell = geohash_grid.get_cell_from_point(40.7128, -74.0060)

        # Convert to H3 with overlap method
        target_cells = converter.convert_cell(source_cell, "h3", method="overlap")
        assert isinstance(target_cells, list)
        assert len(target_cells) > 0
        assert all(isinstance(cell, GridCell) for cell in target_cells)

    def test_convert_cells_batch(self):
        """Test batch conversion of cells."""
        converter = GridConverter()

        # Create source cells
        geohash_grid = GeohashGrid(precision=5)
        source_cells = [
            geohash_grid.get_cell_from_point(40.7128, -74.0060),
            geohash_grid.get_cell_from_point(34.0522, -118.2437),
        ]

        # Convert batch
        results = converter.convert_cells_batch(source_cells, "h3")
        assert len(results) == len(source_cells)
        assert all(isinstance(result, GridCell) for result in results)

    def test_create_conversion_table(self):
        """Test creation of conversion table."""
        converter = GridConverter()

        # Small bounding box
        bounds = (-74.01, 40.71, -74.00, 40.72)

        table = converter.create_conversion_table("geohash", "h3", bounds)
        assert isinstance(table, pd.DataFrame)
        assert "source_system" in table.columns
        assert "target_system" in table.columns
        assert "source_id" in table.columns
        assert "target_id" in table.columns
        assert len(table) > 0

    def test_get_equivalent_precision(self):
        """Test finding equivalent precision between systems."""
        converter = GridConverter()

        # Find H3 equivalent for Geohash precision 5
        equivalent = converter.get_equivalent_precision("geohash", 5, "h3")
        assert isinstance(equivalent, int)
        assert equivalent > 0

    def test_get_system_info(self):
        """Test getting system information."""
        converter = GridConverter()

        info_df = converter.get_system_info()
        assert isinstance(info_df, pd.DataFrame)
        assert "system" in info_df.columns
        assert "default_precision" in info_df.columns
        assert "default_area_km2" in info_df.columns
        assert len(info_df) > 0

    def test_convenience_functions(self):
        """Test convenience functions."""
        # Create test cell
        geohash_grid = GeohashGrid(precision=5)
        cell = geohash_grid.get_cell_from_point(40.7128, -74.0060)

        # Test single cell conversion
        result = convert_cell(cell, "h3")
        assert isinstance(result, GridCell)

        # Test batch conversion
        results = convert_cells([cell], "h3")
        assert len(results) == 1
        assert isinstance(results[0], GridCell)

        # Test equivalent precision
        equiv = get_equivalent_precision("geohash", 5, "h3")
        assert isinstance(equiv, int)

    def test_invalid_conversion_method(self):
        """Test error for invalid conversion method."""
        converter = GridConverter()

        geohash_grid = GeohashGrid(precision=5)
        cell = geohash_grid.get_cell_from_point(40.7128, -74.0060)

        with pytest.raises(ValueError):
            converter.convert_cell(cell, "h3", method="invalid_method")

    def test_caching_behavior(self):
        """Test that grid instances are cached."""
        converter = GridConverter()

        # Get same grid twice
        grid1 = converter._get_grid("geohash", 5)
        grid2 = converter._get_grid("geohash", 5)

        # Should be the same instance (cached)
        assert grid1 is grid2

    def test_different_precision_not_cached(self):
        """Test that different precisions create different instances."""
        converter = GridConverter()

        # Get grids with different precisions
        grid1 = converter._get_grid("geohash", 5)
        grid2 = converter._get_grid("geohash", 6)

        # Should be different instances
        assert grid1 is not grid2
        assert grid1.precision != grid2.precision
