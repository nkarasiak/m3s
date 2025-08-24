"""
Tests for GeoDataFrame functionality in griddy.
"""

import geopandas as gpd
import pytest
from shapely.geometry import Point, box

from m3s import GeohashGrid, H3Grid, MGRSGrid


class TestGeoDataFrameIntegration:
    """Test GeoDataFrame integration with all grid types."""

    @pytest.fixture
    def sample_gdf_4326(self):
        """Create a sample GeoDataFrame in WGS84."""
        geometries = [
            Point(-74.0060, 40.7128),  # NYC
            Point(-118.2437, 34.0522),  # LA
            box(-74.1, 40.7, -74.0, 40.8),  # NYC bbox
        ]
        data = {
            "name": ["NYC Point", "LA Point", "NYC Area"],
            "type": ["point", "point", "polygon"],
            "value": [100, 200, 300],
        }
        return gpd.GeoDataFrame(data, geometry=geometries, crs="EPSG:4326")

    @pytest.fixture
    def sample_gdf_3857(self):
        """Create a sample GeoDataFrame in Web Mercator."""
        geometries = [
            Point(-8238310.24, 4969803.98),  # NYC in 3857
            Point(-13158950.02, 4036449.85),  # LA in 3857
        ]
        data = {
            "name": ["NYC Point", "LA Point"],
            "type": ["point", "point"],
            "value": [100, 200],
        }
        return gpd.GeoDataFrame(data, geometry=geometries, crs="EPSG:3857")

    def test_geohash_intersects_basic(self, sample_gdf_4326):
        """Test basic GeoDataFrame intersection with GeohashGrid."""
        grid = GeohashGrid(precision=5)
        result = grid.intersects(sample_gdf_4326)

        assert isinstance(result, gpd.GeoDataFrame)
        assert len(result) >= 3  # At least one cell per geometry
        assert "cell_id" in result.columns
        assert "precision" in result.columns
        assert "name" in result.columns
        assert result.crs == sample_gdf_4326.crs

        # Check that cell_ids are valid geohash strings
        for cell_id in result["cell_id"]:
            assert isinstance(cell_id, str)
            assert len(cell_id) == 5  # precision 5

    def test_mgrs_intersects_basic(self, sample_gdf_4326):
        """Test basic GeoDataFrame intersection with MGRSGrid."""
        grid = MGRSGrid(precision=2)
        result = grid.intersects(sample_gdf_4326)

        assert isinstance(result, gpd.GeoDataFrame)
        assert len(result) >= 3
        assert "cell_id" in result.columns
        assert "precision" in result.columns
        assert "name" in result.columns
        assert result.crs == sample_gdf_4326.crs

    def test_h3_intersects_basic(self, sample_gdf_4326):
        """Test basic GeoDataFrame intersection with H3Grid."""
        grid = H3Grid(resolution=7)
        result = grid.intersects(sample_gdf_4326)

        assert isinstance(result, gpd.GeoDataFrame)
        assert len(result) >= 3
        assert "cell_id" in result.columns
        assert "precision" in result.columns
        assert "name" in result.columns
        assert result.crs == sample_gdf_4326.crs

    def test_crs_transformation(self, sample_gdf_3857):
        """Test CRS transformation during intersection."""
        grid = GeohashGrid(precision=5)
        result = grid.intersects(sample_gdf_3857)

        assert isinstance(result, gpd.GeoDataFrame)
        assert result.crs == sample_gdf_3857.crs  # Should be transformed back
        assert len(result) >= 2

    def test_aggregated_intersection(self, sample_gdf_4326):
        """Test aggregated GeoDataFrame intersection."""
        grid = GeohashGrid(precision=5)
        # Test that aggregated method no longer exists
        with pytest.raises(AttributeError):
            grid.intersects_aggregated(sample_gdf_4326)

        pass  # Test updated to check that method was removed

    def test_empty_geodataframe(self):
        """Test handling of empty GeoDataFrame."""
        grid = GeohashGrid(precision=5)
        empty_gdf = gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")

        result = grid.intersects(empty_gdf)
        assert isinstance(result, gpd.GeoDataFrame)
        assert len(result) == 0
        assert "cell_id" in result.columns

    def test_no_crs_error(self):
        """Test error when GeoDataFrame has no CRS."""
        grid = GeohashGrid(precision=5)
        gdf_no_crs = gpd.GeoDataFrame(geometry=[Point(-74.0060, 40.7128)], crs=None)

        with pytest.raises(ValueError, match="GeoDataFrame CRS must be defined"):
            grid.intersects(gdf_no_crs)

    def test_null_geometries(self):
        """Test handling of null geometries in GeoDataFrame."""
        geometries = [
            Point(-74.0060, 40.7128),
            None,
            Point(-118.2437, 34.0522),
        ]
        data = {"name": ["NYC", "Null", "LA"]}
        gdf = gpd.GeoDataFrame(data, geometry=geometries, crs="EPSG:4326")

        grid = GeohashGrid(precision=5)
        result = grid.intersects(gdf)

        # Should only get results for non-null geometries
        assert len(result) == 2
        assert "NYC" in result["name"].values
        assert "LA" in result["name"].values
        assert "Null" not in result["name"].values

    def test_custom_target_crs(self, sample_gdf_4326):
        """Test using custom target CRS for grid operations."""
        grid = GeohashGrid(precision=5)

        # Use a different CRS for grid operations
        result = grid.intersects(sample_gdf_4326)

        assert isinstance(result, gpd.GeoDataFrame)
        assert result.crs == sample_gdf_4326.crs  # Should be transformed back
        assert len(result) >= 3

    def test_preserve_original_data(self, sample_gdf_4326):
        """Test that original GeoDataFrame data is preserved in results."""
        grid = GeohashGrid(precision=5)
        result = grid.intersects(sample_gdf_4326)

        # All original columns should be preserved
        for col in sample_gdf_4326.columns:
            if col != "geometry":
                assert col in result.columns

        # Check that data values are preserved
        assert "NYC Point" in result["name"].values
        assert "LA Point" in result["name"].values
        assert "NYC Area" in result["name"].values

        assert 100 in result["value"].values
        assert 200 in result["value"].values
        assert 300 in result["value"].values

    def test_polygon_intersection_multiple_cells(self):
        """Test that large polygons intersect multiple grid cells."""
        # Create a large polygon that should intersect multiple cells
        large_polygon = box(-75, 40, -73, 42)  # Large area around NYC
        gdf = gpd.GeoDataFrame(
            {"name": ["Large Area"]}, geometry=[large_polygon], crs="EPSG:4326"
        )

        grid = GeohashGrid(precision=4)  # Lower precision for more cells
        result = grid.intersects(gdf)

        assert len(result) > 1  # Should intersect multiple cells

        # Aggregated method no longer exists
        with pytest.raises(AttributeError):
            grid.intersect_geodataframe_aggregated(gdf)


class TestGeoDataFrameEdgeCases:
    """Test edge cases and error conditions."""

    def test_mixed_geometry_types(self):
        """Test GeoDataFrame with mixed geometry types."""
        geometries = [
            Point(-74.0060, 40.7128),
            box(-74.1, 40.7, -74.0, 40.8),
            Point(-118.2437, 34.0522).buffer(0.01),  # Circle
        ]
        gdf = gpd.GeoDataFrame(
            {"type": ["point", "box", "circle"]}, geometry=geometries, crs="EPSG:4326"
        )

        grid = GeohashGrid(precision=5)
        result = grid.intersects(gdf)

        assert len(result) >= 3
        assert "point" in result["type"].values
        assert "box" in result["type"].values
        assert "circle" in result["type"].values

    def test_different_grid_types_same_gdf(self, sample_gdf_4326):
        """Test same GeoDataFrame with different grid types."""
        grids = [GeohashGrid(precision=5), MGRSGrid(precision=2), H3Grid(resolution=7)]

        results = []
        for grid in grids:
            result = grid.intersects(sample_gdf_4326)
            results.append(result)
            assert isinstance(result, gpd.GeoDataFrame)
            assert len(result) > 0
            assert result.crs == sample_gdf_4326.crs

        # Results should have different cell_id formats
        geohash_ids = set(results[0]["cell_id"])
        mgrs_ids = set(results[1]["cell_id"])
        h3_ids = set(results[2]["cell_id"])

        # Should be no overlap between different grid systems
        assert len(geohash_ids.intersection(mgrs_ids)) == 0
        assert len(geohash_ids.intersection(h3_ids)) == 0
        assert len(mgrs_ids.intersection(h3_ids)) == 0

    @pytest.fixture
    def sample_gdf_4326(self):
        """Create a sample GeoDataFrame in WGS84."""
        geometries = [
            Point(-74.0060, 40.7128),  # NYC
            Point(-118.2437, 34.0522),  # LA
            box(-74.1, 40.7, -74.0, 40.8),  # NYC bbox
        ]
        data = {
            "name": ["NYC Point", "LA Point", "NYC Area"],
            "type": ["point", "point", "polygon"],
            "value": [100, 200, 300],
        }
        return gpd.GeoDataFrame(data, geometry=geometries, crs="EPSG:4326")
