"""
Tests for GridWrapper API.
"""

import geopandas as gpd
from shapely.geometry import Point, Polygon

import m3s
from m3s.base import GridCell


class TestGridWrapper:
    """Test GridWrapper functionality."""

    def test_singleton_access(self):
        """Test that grid singletons are accessible."""
        assert hasattr(m3s, "Geohash")
        assert hasattr(m3s, "H3")
        assert hasattr(m3s, "MGRS")
        assert hasattr(m3s, "S2")

    def test_from_point_tuple(self):
        """Test from_geometry with point tuple."""
        cell = m3s.Geohash.from_geometry((-74.0, 40.7))
        assert isinstance(cell, GridCell)
        assert cell.identifier is not None
        assert cell.precision == 5  # Default precision

    def test_from_point_explicit(self):
        """Test from_point method."""
        cell = m3s.Geohash.from_point(-74.0, 40.7)
        assert isinstance(cell, GridCell)
        assert cell.identifier is not None

    def test_from_shapely_point(self):
        """Test from_geometry with Shapely Point."""
        point = Point(-74.0, 40.7)
        cell = m3s.Geohash.from_geometry(point)
        assert isinstance(cell, GridCell)

    def test_from_bbox_tuple(self):
        """Test from_geometry with bbox tuple."""
        cells = m3s.H3.from_geometry((-74.02, 40.70, -74.01, 40.71))
        assert isinstance(cells, m3s.GridCellCollection)
        assert len(cells) > 0

    def test_from_bbox_explicit(self):
        """Test from_bbox method."""
        cells = m3s.H3.from_bbox((-74.02, 40.70, -74.01, 40.71))
        assert isinstance(cells, m3s.GridCellCollection)
        assert len(cells) > 0

    def test_from_polygon(self):
        """Test from_geometry with Polygon."""
        polygon = Polygon(
            [(-74.02, 40.70), (-74.01, 40.70), (-74.01, 40.71), (-74.02, 40.71)]
        )
        cells = m3s.Geohash.from_geometry(polygon)
        assert isinstance(cells, m3s.GridCellCollection)
        assert len(cells) > 0

    def test_from_polygon_explicit(self):
        """Test from_polygon method."""
        polygon = Polygon(
            [(-74.02, 40.70), (-74.01, 40.70), (-74.01, 40.71), (-74.02, 40.71)]
        )
        cells = m3s.Geohash.from_polygon(polygon)
        assert isinstance(cells, m3s.GridCellCollection)
        assert len(cells) > 0

    def test_from_geodataframe(self):
        """Test from_geometry with GeoDataFrame."""
        polygon = Polygon(
            [(-74.02, 40.70), (-74.01, 40.70), (-74.01, 40.71), (-74.02, 40.71)]
        )
        gdf = gpd.GeoDataFrame({"geometry": [polygon]}, crs="EPSG:4326")
        cells = m3s.H3.from_geometry(gdf)
        assert isinstance(cells, m3s.GridCellCollection)
        assert len(cells) > 0

    def test_with_precision(self):
        """Test with_precision method."""
        cells = m3s.Geohash.with_precision(7).from_geometry(
            (-74.02, 40.70, -74.01, 40.71)
        )
        assert isinstance(cells, m3s.GridCellCollection)
        assert all(c.precision == 7 for c in cells.cells)

    def test_precision_in_method(self):
        """Test precision parameter in from_geometry."""
        cell = m3s.H3.from_geometry((-74.0, 40.7), precision=9)
        assert cell.precision == 9

    def test_neighbors(self):
        """Test neighbors method."""
        cell = m3s.Geohash.from_geometry((-74.0, 40.7))
        neighbors = m3s.Geohash.neighbors(cell, depth=1)
        assert isinstance(neighbors, m3s.GridCellCollection)
        assert len(neighbors) > 1  # Cell + neighbors


class TestGridCellCollection:
    """Test GridCellCollection functionality."""

    def test_to_gdf(self):
        """Test conversion to GeoDataFrame."""
        cells = m3s.Geohash.from_geometry((-74.02, 40.70, -74.01, 40.71))
        gdf = cells.to_gdf()
        assert isinstance(gdf, gpd.GeoDataFrame)
        assert len(gdf) == len(cells)
        assert "cell_id" in gdf.columns
        assert "precision" in gdf.columns

    def test_to_ids(self):
        """Test conversion to ID list."""
        cells = m3s.H3.from_geometry((-74.02, 40.70, -74.01, 40.71))
        ids = cells.to_ids()
        assert isinstance(ids, list)
        assert len(ids) == len(cells)
        assert all(isinstance(id, str) for id in ids)

    def test_to_polygons(self):
        """Test conversion to polygon list."""
        cells = m3s.Geohash.from_geometry((-74.02, 40.70, -74.01, 40.71))
        polygons = cells.to_polygons()
        assert isinstance(polygons, list)
        assert len(polygons) == len(cells)

    def test_filter(self):
        """Test filtering cells."""
        cells = m3s.H3.from_geometry((-74.02, 40.70, -74.01, 40.71))
        filtered = cells.filter(lambda c: c.area_km2 > 1.0)
        assert isinstance(filtered, m3s.GridCellCollection)
        assert len(filtered) <= len(cells)

    def test_map(self):
        """Test mapping function over cells."""
        cells = m3s.Geohash.from_geometry((-74.02, 40.70, -74.01, 40.71))
        areas = cells.map(lambda c: c.area_km2)
        assert isinstance(areas, list)
        assert len(areas) == len(cells)

    def test_total_area(self):
        """Test total area property."""
        cells = m3s.H3.from_geometry((-74.02, 40.70, -74.01, 40.71))
        total_area = cells.total_area_km2
        assert isinstance(total_area, float)
        assert total_area > 0

    def test_bounds(self):
        """Test bounds property."""
        cells = m3s.Geohash.from_geometry((-74.02, 40.70, -74.01, 40.71))
        bounds = cells.bounds
        assert isinstance(bounds, tuple)
        assert len(bounds) == 4

    def test_len(self):
        """Test __len__ method."""
        cells = m3s.H3.from_geometry((-74.02, 40.70, -74.01, 40.71))
        assert len(cells) > 0

    def test_iter(self):
        """Test __iter__ method."""
        cells = m3s.Geohash.from_geometry((-74.02, 40.70, -74.01, 40.71))
        for cell in cells:
            assert isinstance(cell, GridCell)

    def test_getitem(self):
        """Test __getitem__ method."""
        cells = m3s.H3.from_geometry((-74.0, 40.7, -73.9, 40.8))
        first_cell = cells[0]
        assert isinstance(first_cell, GridCell)

        # Test slicing
        slice_cells = cells[0:2]
        assert isinstance(slice_cells, m3s.GridCellCollection)
        assert len(slice_cells) == 2


class TestPrecisionFinder:
    """Test PrecisionFinder functionality."""

    def test_find_precision_for_area(self):
        """Test finding precision for target area."""
        precision = m3s.Geohash.find_precision_for_area(target_km2=10.0)
        assert isinstance(precision, int)
        assert precision > 0

    def test_find_precision_for_use_case(self):
        """Test finding precision for use case."""
        precision = m3s.H3.find_precision_for_use_case("neighborhood")
        assert isinstance(precision, int)
        assert precision > 0

        precision_city = m3s.Geohash.find_precision_for_use_case("city")
        assert isinstance(precision_city, int)

    def test_find_precision_auto(self):
        """Test auto precision finding."""
        polygon = Polygon(
            [(-74.001, 40.700), (-73.999, 40.700), (-73.999, 40.701), (-74.001, 40.701)]
        )
        precision = m3s.Geohash.find_precision(polygon, method="auto")
        assert isinstance(precision, int)
        assert precision > 0

    def test_find_precision_target_count(self):
        """Test precision finding with target count."""
        polygon = Polygon(
            [(-74.001, 40.700), (-73.999, 40.700), (-73.999, 40.701), (-74.001, 40.701)]
        )
        precision = m3s.H3.find_precision(polygon, method=100)
        assert isinstance(precision, int)
        assert precision > 0


class TestGridCellEnhancements:
    """Test GridCell convenience properties."""

    def test_id_property(self):
        """Test id property (alias for identifier)."""
        cell = m3s.Geohash.from_geometry((-74.0, 40.7))
        assert cell.id == cell.identifier

    def test_bounds_property(self):
        """Test bounds property."""
        cell = m3s.Geohash.from_geometry((-74.0, 40.7))
        bounds = cell.bounds
        assert isinstance(bounds, tuple)
        assert len(bounds) == 4

    def test_centroid_property(self):
        """Test centroid property."""
        cell = m3s.Geohash.from_geometry((-74.0, 40.7))
        centroid = cell.centroid
        assert isinstance(centroid, tuple)
        assert len(centroid) == 2
        assert isinstance(centroid[0], float)  # lon
        assert isinstance(centroid[1], float)  # lat

    def test_geometry_property(self):
        """Test geometry property (alias for polygon)."""
        cell = m3s.Geohash.from_geometry((-74.0, 40.7))
        assert cell.geometry == cell.polygon

    def test_to_dict(self):
        """Test to_dict method."""
        cell = m3s.Geohash.from_geometry((-74.0, 40.7))
        d = cell.to_dict()
        assert isinstance(d, dict)
        assert "id" in d
        assert "precision" in d
        assert "area_km2" in d
        assert "centroid" in d

    def test_to_geojson(self):
        """Test to_geojson method."""
        cell = m3s.Geohash.from_geometry((-74.0, 40.7))
        geojson = cell.to_geojson()
        assert isinstance(geojson, dict)
        assert geojson["type"] == "Feature"
        assert "geometry" in geojson
        assert "properties" in geojson


class TestCrossGridConversion:
    """Test cross-grid conversion methods."""

    def test_to_h3(self):
        """Test conversion to H3."""
        cells = m3s.Geohash.from_geometry((-74.02, 40.70, -74.01, 40.71))
        h3_cells = cells.to_h3()
        assert isinstance(h3_cells, m3s.GridCellCollection)
        assert len(h3_cells) > 0

    def test_to_geohash(self):
        """Test conversion to Geohash."""
        cells = m3s.H3.from_geometry((-74.02, 40.70, -74.01, 40.71))
        geohash_cells = cells.to_geohash()
        assert isinstance(geohash_cells, m3s.GridCellCollection)
        assert len(geohash_cells) > 0

    def test_conversion_methods(self):
        """Test conversion method parameter."""
        cells = m3s.Geohash.from_geometry((-74.0, 40.7, -73.9, 40.8))

        # Centroid method (default)
        h3_centroid = cells.to_h3(method="centroid")
        assert len(h3_centroid) > 0

        # Overlap method
        h3_overlap = cells.to_h3(method="overlap")
        assert len(h3_overlap) > 0


class TestBackwardCompatibility:
    """Test that old API still works."""

    def test_old_api_still_works(self):
        """Test that old grid instantiation still works."""
        from m3s import GeohashGrid

        grid = GeohashGrid(precision=5)
        cell = grid.get_cell_from_point(40.7, -74.0)
        assert isinstance(cell, GridCell)
        assert cell.identifier is not None

    def test_old_and_new_api_compatible(self):
        """Test that old and new API produce same results."""
        from m3s import GeohashGrid

        # Old API
        grid = GeohashGrid(precision=5)
        old_cell = grid.get_cell_from_point(40.7, -74.0)

        # New API
        new_cell = m3s.Geohash.from_geometry((-74.0, 40.7))

        # Should produce same cell
        assert old_cell.identifier == new_cell.identifier


class TestAxisOrder:
    """Lock in GIS-native (lon, lat) axis order across the M3S API."""

    def test_centroid_is_lon_lat(self):
        """Centroid returns (lon, lat) matching shapely x, y."""
        cell = m3s.Geohash.from_point(-74.0, 40.7)
        c = cell.polygon.centroid
        assert cell.centroid == (c.x, c.y)
        # NYC: lon negative, lat positive
        assert cell.centroid[0] < 0
        assert cell.centroid[1] > 0

    def test_bounds_is_lon_first(self):
        """Bounds returns (min_lon, min_lat, max_lon, max_lat)."""
        cell = m3s.Geohash.from_point(-74.0, 40.7)
        assert cell.bounds == cell.polygon.bounds

    def test_bbox_bounds_round_trip(self):
        """from_bbox(collection.bounds) uses the same axis order as bounds.

        Feeding a collection's own bounds back into from_bbox must re-select
        those cells (a superset, since each cell's bounds may extend past the
        original query). Before the lon-first fix this mixed lat/lon and
        queried the wrong region, dropping the originals entirely.
        """
        cells = m3s.Geohash.from_geometry((-74.02, 40.70, -74.01, 40.71))
        again = m3s.Geohash.from_bbox(cells.bounds)
        assert set(cells.to_ids()).issubset(set(again.to_ids()))

    def test_point_matches_shapely_point(self):
        """A (lon, lat) tuple and the equivalent shapely Point agree."""
        from shapely.geometry import Point

        tuple_cell = m3s.Geohash.from_geometry((-74.0, 40.7))
        point_cell = m3s.Geohash.from_geometry(Point(-74.0, 40.7))
        assert tuple_cell.identifier == point_cell.identifier


class TestContractAndInference:
    """Lock in C3 (from_id) and H3 (hierarchy contract) fixes."""

    def test_from_id_roundtrip(self):
        """from_id parses an identifier back to an equivalent cell."""
        cell = m3s.Geohash.from_point(-74.0, 40.7)
        parsed = m3s.Geohash.from_id(cell.identifier)
        assert parsed.identifier == cell.identifier

    def test_coarsen_unsupported_raises(self):
        """Non-hierarchical grids raise NotImplementedError on coarsen."""
        import pytest

        # MGRS has no get_parent, so coarsen is unsupported. (Geohash, being
        # natively hierarchical, now *does* support coarsen.)
        cells = m3s.MGRS.from_geometry((-74.02, 40.70, -74.01, 40.71))
        with pytest.raises(NotImplementedError):
            cells.coarsen(1)
