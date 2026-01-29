"""
Tests for What3Words grid implementation.
"""

import pytest
from shapely.geometry import Point

from m3s.base import GridCell
from m3s.what3words import What3WordsGrid


class TestWhat3WordsGrid:
    """Test What3Words grid functionality."""

    def test_initialization(self):
        """Test grid initialization."""
        grid = What3WordsGrid()
        assert grid.precision == 1
        assert grid.area_km2 == 0.000009  # 9 square meters converted to km²

    def test_invalid_precision(self):
        """Test that invalid precision raises error."""
        with pytest.raises(ValueError):
            What3WordsGrid(precision=2)

    def test_get_cell_from_point(self):
        """Test getting cell from point."""
        grid = What3WordsGrid()
        cell = grid.get_cell_from_point(40.7128, -74.0060)  # NYC coordinates

        assert isinstance(cell, GridCell)
        assert cell.identifier.startswith("w3w.")
        assert cell.precision == 1
        assert cell.polygon.contains(Point(-74.0060, 40.7128))

    def test_get_cell_from_identifier(self):
        """Test getting cell from identifier."""
        grid = What3WordsGrid()

        # This should work with any w3w.* identifier
        cell = grid.get_cell_from_identifier("w3w.test.example.demo")
        assert isinstance(cell, GridCell)
        assert cell.precision == 1

    def test_invalid_identifier(self):
        """Test invalid identifier raises error."""
        grid = What3WordsGrid()
        with pytest.raises(ValueError):
            grid.get_cell_from_identifier("invalid.identifier")

    def test_get_neighbors(self):
        """Test neighbor finding."""
        grid = What3WordsGrid()
        cell = grid.get_cell_from_point(0.0, 0.0)
        neighbors = grid.get_neighbors(cell)

        # Should have 8 neighbors (Moore neighborhood)
        assert len(neighbors) == 8

        # All neighbors should be GridCell instances
        for neighbor in neighbors:
            assert isinstance(neighbor, GridCell)
            assert neighbor.precision == 1

    def test_get_cells_in_bbox(self):
        """Test getting cells in bounding box."""
        grid = What3WordsGrid()

        # Small bounding box around NYC
        cells = grid.get_cells_in_bbox(40.71, -74.01, 40.72, -74.00)

        assert len(cells) > 0
        for cell in cells:
            assert isinstance(cell, GridCell)
            assert cell.precision == 1

    def test_intersects_with_geodataframe(self):
        """Test intersection with GeoDataFrame."""
        import geopandas as gpd
        from shapely.geometry import Point

        grid = What3WordsGrid()

        # Create test GeoDataFrame
        gdf = gpd.GeoDataFrame(
            {"name": ["point1", "point2"], "value": [10, 20]},
            geometry=[Point(-74.0060, 40.7128), Point(-118.2437, 34.0522)],
        )
        gdf.crs = "EPSG:4326"

        result = grid.intersects(gdf)

        assert len(result) >= len(gdf)  # May have multiple cells per point
        assert "cell_id" in result.columns
        assert "utm" in result.columns
        assert all(result["cell_id"].str.startswith("w3w."))

    def test_consistent_cell_generation(self):
        """Test that same coordinates always generate same cell."""
        grid = What3WordsGrid()

        lat, lon = 40.7128, -74.0060
        cell1 = grid.get_cell_from_point(lat, lon)
        cell2 = grid.get_cell_from_point(lat, lon)

        assert cell1.identifier == cell2.identifier
        assert cell1.polygon.equals(cell2.polygon)

    def test_cell_area_calculation(self):
        """Test cell area calculation."""
        grid = What3WordsGrid()
        cell = grid.get_cell_from_point(0.0, 0.0)

        # Area should be approximately 9 square meters (0.000009 km²)
        assert abs(cell.area_km2 - 0.000009) < 0.000001

    def test_grid_coordinates_conversion(self):
        """Test internal grid coordinate conversion methods."""
        grid = What3WordsGrid()

        # Test coordinate conversion
        lat, lon = 40.7128, -74.0060
        x, y = grid._lat_lon_to_grid_coords(lat, lon)

        assert isinstance(x, int)
        assert isinstance(y, int)

        # Test bounds calculation
        bounds = grid._grid_coords_to_bounds(x, y)
        assert len(bounds) == 4
        assert bounds[0] <= lon <= bounds[2]  # lon within bounds
        assert bounds[1] <= lat <= bounds[3]  # lat within bounds
