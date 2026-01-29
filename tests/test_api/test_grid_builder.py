"""Tests for GridBuilder fluent interface."""

import pytest
from shapely.geometry import Point, Polygon, box

from m3s.api.builder import GridBuilder
from m3s.api.precision import PrecisionSelector
from m3s.api.results import GridQueryResult
from m3s.base import GridCell


class TestGridBuilderBasics:
    """Test basic GridBuilder functionality."""

    def test_for_system(self):
        """Test grid system selection."""
        builder = GridBuilder.for_system("h3")
        assert builder._grid_system == "h3"

    def test_with_precision(self):
        """Test explicit precision setting."""
        builder = GridBuilder.for_system("h3").with_precision(7)
        assert builder._precision == 7

    def test_with_auto_precision_recommendation(self):
        """Test automatic precision from recommendation."""
        selector = PrecisionSelector("h3")
        rec = selector.for_use_case("city")

        builder = GridBuilder.for_system("h3").with_auto_precision(rec)

        assert builder._precision == rec.precision
        assert "precision_recommendation" in builder._metadata

    def test_with_auto_precision_selector(self):
        """Test automatic precision from selector (uses default)."""
        selector = PrecisionSelector("h3")

        builder = GridBuilder.for_system("h3").with_auto_precision(selector)

        # Should have set a precision (default to 'city')
        assert builder._precision is not None

    def test_method_chaining(self):
        """Test that methods return builder for chaining."""
        result = (
            GridBuilder.for_system("geohash")
            .with_precision(5)
            .at_point(40.7128, -74.0060)
        )

        assert isinstance(result, GridBuilder)


class TestGridBuilderSinglePointQueries:
    """Test single point query operations."""

    def test_at_point_basic(self):
        """Test basic single point query."""
        result = (
            GridBuilder.for_system("geohash")
            .with_precision(5)
            .at_point(40.7128, -74.0060)
            .execute()
        )

        assert isinstance(result, GridQueryResult)
        assert len(result) == 1

        cell = result.single
        assert isinstance(cell, GridCell)
        assert cell.identifier is not None
        assert cell.precision == 5

    def test_at_point_multiple_systems(self):
        """Test point query works for different grid systems."""
        systems = ["geohash", "h3", "s2", "quadkey"]
        lat, lon = 40.7128, -74.0060

        for system in systems:
            result = (
                GridBuilder.for_system(system).with_precision(7).at_point(lat, lon).execute()
            )

            assert len(result) == 1
            cell = result.single
            assert cell.identifier is not None


class TestGridBuilderBatchQueries:
    """Test batch query operations."""

    def test_at_points_list(self):
        """Test querying multiple points from list."""
        points = [(40.7128, -74.0060), (34.0522, -118.2437), (51.5074, -0.1278)]

        result = (
            GridBuilder.for_system("h3").with_precision(7).at_points(points).execute()
        )

        assert len(result) == 3
        assert all(isinstance(cell, GridCell) for cell in result.many)

    def test_in_bbox(self):
        """Test bounding box query."""
        result = (
            GridBuilder.for_system("geohash")
            .with_precision(5)
            .in_bbox(40.7, -74.1, 40.8, -73.9)
            .execute()
        )

        # Should return multiple cells
        assert len(result) > 1
        assert all(cell.precision == 5 for cell in result.many)

    def test_in_polygon(self):
        """Test polygon query."""
        # Small square polygon
        polygon = box(-74.1, 40.7, -73.9, 40.8)

        result = (
            GridBuilder.for_system("h3").with_precision(7).in_polygon(polygon).execute()
        )

        # Should return cells
        assert len(result) > 0


class TestGridBuilderNeighborOperations:
    """Test neighbor finding operations."""

    def test_find_neighbors_depth_1(self):
        """Test finding immediate neighbors."""
        result = (
            GridBuilder.for_system("h3")
            .with_precision(7)
            .at_point(40.7128, -74.0060)
            .find_neighbors(depth=1)
            .execute()
        )

        # Should include original cell + neighbors
        assert len(result) > 1  # At least the cell + some neighbors

    def test_find_neighbors_depth_2(self):
        """Test finding neighbors of neighbors."""
        result = (
            GridBuilder.for_system("h3")
            .with_precision(7)
            .at_point(40.7128, -74.0060)
            .find_neighbors(depth=2)
            .execute()
        )

        # Depth 2 should include more cells than depth 1
        # (original + ring1 + ring2)
        assert len(result) > 7  # Typical hexagon has 6 neighbors


class TestGridBuilderHierarchyOperations:
    """Test parent/child hierarchy operations."""

    @pytest.mark.skip(reason="Needs get_children/get_parent implementation in base grids")
    def test_with_children(self):
        """Test getting children at finer precision."""
        result = (
            GridBuilder.for_system("h3")
            .with_precision(5)
            .at_point(40.7128, -74.0060)
            .with_children(child_precision=6)
            .execute()
        )

        # Should have multiple children
        assert len(result) > 1
        # All children should have precision 6
        assert all(cell.precision == 6 for cell in result.many)

    @pytest.mark.skip(reason="Needs get_parent implementation in base grids")
    def test_with_parent(self):
        """Test getting parent at coarser precision."""
        result = (
            GridBuilder.for_system("h3")
            .with_precision(7)
            .at_point(40.7128, -74.0060)
            .with_parent(parent_precision=6)
            .execute()
        )

        # Should have single parent
        assert len(result) == 1
        assert result.single.precision == 6


class TestGridBuilderConversion:
    """Test grid conversion operations."""

    @pytest.mark.skip(reason="Needs working convert_cell function")
    def test_convert_to_different_system(self):
        """Test converting to different grid system."""
        result = (
            GridBuilder.for_system("geohash")
            .with_precision(5)
            .at_point(40.7128, -74.0060)
            .convert_to("h3", method="centroid")
            .execute()
        )

        # Result should be H3 cells
        assert len(result) >= 1
        # IDs should be H3 format
        for cell in result.many:
            assert isinstance(cell.identifier, (str, int))


class TestGridBuilderFilteringAndLimiting:
    """Test filtering and limiting operations."""

    def test_filter_by_area(self):
        """Test filtering cells by area."""
        result = (
            GridBuilder.for_system("geohash")
            .with_precision(5)
            .in_bbox(40.7, -74.1, 40.8, -73.9)
            .filter(lambda cell: cell.area_km2 > 1.0)
            .execute()
        )

        # All cells should meet filter criteria
        assert all(cell.area_km2 > 1.0 for cell in result.many)

    def test_limit_results(self):
        """Test limiting number of results."""
        result = (
            GridBuilder.for_system("h3")
            .with_precision(7)
            .in_bbox(40.7, -74.1, 40.8, -73.9)
            .limit(5)
            .execute()
        )

        # Should have at most 5 results
        assert len(result) <= 5


class TestGridBuilderErrorHandling:
    """Test error handling and validation."""

    def test_execute_without_system(self):
        """Test that execute fails without grid system."""
        builder = GridBuilder()

        with pytest.raises(ValueError, match="Grid system not set"):
            builder.with_precision(5).at_point(40.7, -74.0).execute()

    def test_execute_without_precision(self):
        """Test that execute fails without precision."""
        builder = GridBuilder.for_system("h3")

        with pytest.raises(ValueError, match="Precision not set"):
            builder.at_point(40.7, -74.0).execute()

    def test_execute_without_operations(self):
        """Test that execute fails without operations."""
        builder = GridBuilder.for_system("h3").with_precision(7)

        with pytest.raises(ValueError, match="No operations specified"):
            builder.execute()

    def test_unknown_grid_system(self):
        """Test that unknown grid system raises error."""
        with pytest.raises(ValueError, match="Unknown grid system"):
            (
                GridBuilder.for_system("invalid_system")
                .with_precision(5)
                .at_point(40.7, -74.0)
                .execute()
            )


class TestGridBuilderComplexWorkflows:
    """Test complex multi-step workflows."""

    def test_point_then_neighbors_then_filter(self):
        """Test chaining point query, neighbors, and filtering."""
        result = (
            GridBuilder.for_system("h3")
            .with_precision(7)
            .at_point(40.7128, -74.0060)
            .find_neighbors(depth=1)
            .filter(lambda cell: cell.area_km2 < 10.0)
            .execute()
        )

        # Should have filtered neighbors
        assert len(result) >= 1
        assert all(cell.area_km2 < 10.0 for cell in result.many)

    def test_bbox_then_limit_then_to_geodataframe(self):
        """Test bbox query with limit and GeoDataFrame conversion."""
        result = (
            GridBuilder.for_system("geohash")
            .with_precision(5)
            .in_bbox(40.7, -74.1, 40.8, -73.9)
            .limit(10)
            .execute()
        )

        gdf = result.to_geodataframe()

        assert len(gdf) == len(result)
        assert len(gdf) <= 10
        assert "identifier" in gdf.columns
        assert "precision" in gdf.columns
        assert "geometry" in gdf.columns

    def test_intelligent_precision_workflow(self):
        """Test complete workflow with intelligent precision selection."""
        # Select precision intelligently
        selector = PrecisionSelector("h3")
        rec = selector.for_use_case("neighborhood")

        # Use in fluent query
        result = (
            GridBuilder.for_system("h3")
            .with_auto_precision(rec)
            .at_point(40.7128, -74.0060)
            .find_neighbors()
            .execute()
        )

        # Should have cells at recommended precision
        assert all(cell.precision == rec.precision for cell in result.many)

        # Metadata should include recommendation info
        assert "precision_recommendation" in result.metadata


class TestGridBuilderIntegration:
    """Integration tests with real grid systems."""

    def test_h3_complete_workflow(self):
        """Test complete H3 workflow."""
        result = (
            GridBuilder.for_system("h3")
            .with_precision(7)
            .at_point(40.7128, -74.0060)  # NYC
            .execute()
        )

        cell = result.single
        assert cell.identifier is not None
        assert 5.0 < cell.area_km2 < 6.0  # H3 res 7 is ~5.16 km²

    def test_geohash_complete_workflow(self):
        """Test complete Geohash workflow."""
        result = (
            GridBuilder.for_system("geohash")
            .with_precision(5)
            .at_point(51.5074, -0.1278)  # London
            .execute()
        )

        cell = result.single
        assert isinstance(cell.identifier, str)
        assert len(cell.identifier) == 5  # Precision 5 = 5 characters

    def test_s2_complete_workflow(self):
        """Test complete S2 workflow."""
        result = (
            GridBuilder.for_system("s2").with_precision(10).at_point(35.6762, 139.6503).execute()
        )  # Tokyo

        cell = result.single
        assert cell.identifier is not None
        assert cell.precision == 10
