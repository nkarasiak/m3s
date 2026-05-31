"""
Tests for the EA-Quad (Equal-Area Quadtree) grid implementation.
"""

import pytest
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union

from m3s import EAQuadGrid, list_grid_systems
from m3s.base import GridCell


class TestEAQuadInit:
    """Initialization and precision/size mapping."""

    def test_init_default(self):
        """Default grid is precision 4 (64 km cells)."""
        grid = EAQuadGrid()
        assert grid.precision == 4
        assert grid.size_km == 64

    def test_init_custom_precision(self):
        """Finest/coarsest precisions map to 1 km / 1024 km."""
        assert EAQuadGrid(precision=10).size_km == 1
        assert EAQuadGrid(precision=0).size_km == 1024

    @pytest.mark.parametrize(
        "precision,size_km",
        [(0, 1024), (1, 512), (4, 64), (7, 8), (9, 2), (10, 1)],
    )
    def test_precision_size_mapping(self, precision, size_km):
        """Precision maps to size_km = 2 ** (10 - precision)."""
        assert EAQuadGrid(precision=precision).size_km == size_km

    def test_init_invalid_precision(self):
        """Out-of-range precision raises ValueError."""
        with pytest.raises(ValueError, match="precision must be between 0 and 10"):
            EAQuadGrid(precision=-1)
        with pytest.raises(ValueError, match="precision must be between 0 and 10"):
            EAQuadGrid(precision=11)

    def test_area_km2_analytic(self):
        """Equal-area: cell area is exactly size_km ** 2."""
        assert EAQuadGrid(precision=7).area_km2 == 64.0
        assert EAQuadGrid(precision=10).area_km2 == 1.0
        assert EAQuadGrid(precision=0).area_km2 == 1024.0**2


class TestEAQuadCells:
    """Point lookup, identifiers and round-tripping."""

    def test_get_cell_from_point_inside(self):
        """The returned cell polygon contains the query point."""
        grid = EAQuadGrid(precision=4)
        for lat, lon in [(40.7, -74.0), (0.0, 0.0), (-33.9, 151.2), (60.0, 10.0)]:
            cell = grid.get_cell_from_point(lat, lon)
            assert isinstance(cell, GridCell)
            assert cell.precision == 4
            assert cell.polygon.buffer(1e-9).contains(Point(lon, lat))

    def test_get_cell_from_point_invalid(self):
        """Out-of-range coordinates raise ValueError."""
        grid = EAQuadGrid(precision=4)
        with pytest.raises(ValueError, match="Latitude"):
            grid.get_cell_from_point(95.0, 0.0)
        with pytest.raises(ValueError, match="Longitude"):
            grid.get_cell_from_point(0.0, 200.0)

    def test_identifier_roundtrip(self):
        """Round-trip point -> identifier -> cell reproduces the cell."""
        grid = EAQuadGrid(precision=6)
        cell = grid.get_cell_from_point(48.85, 2.35)  # Paris
        again = grid.get_cell_from_identifier(cell.identifier)
        assert again.identifier == cell.identifier
        assert again.precision == cell.precision
        assert again.polygon.equals(cell.polygon)

    def test_identifier_format(self):
        """Identifiers encode the cell size in km as a prefix."""
        cell = EAQuadGrid(precision=10).get_cell_from_point(0.0, 0.0)
        assert cell.identifier.startswith("1kmE")
        cell64 = EAQuadGrid(precision=4).get_cell_from_point(0.0, 0.0)
        assert cell64.identifier.startswith("64kmE")

    def test_invalid_identifiers(self):
        """Malformed, non-power-of-two, or misaligned identifiers raise."""
        grid = EAQuadGrid(precision=4)
        for bad in ["garbage", "3kmE0N0", "8kmE5N0", "8kmE0N5"]:
            with pytest.raises(ValueError):
                grid.get_cell_from_identifier(bad)

    def test_identifier_to_precision(self):
        """Precision is derivable from the identifier's size."""
        grid = EAQuadGrid(precision=4)
        assert grid.identifier_to_precision("8kmE16N8") == 7
        assert grid.identifier_to_precision("1024kmE0N0") == 0
        assert grid.identifier_to_precision("garbage") is None


class TestEAQuadHierarchy:
    """Exact quadtree containment."""

    def test_exact_nesting(self):
        """The 4 children exactly tile the parent and lie within it."""
        grid = EAQuadGrid(precision=5)  # 32 km parent
        parent = grid.get_cell_from_point(40.0, -74.0)
        children = grid.get_children(parent)

        assert len(children) == 4
        assert all(c.precision == parent.precision + 1 for c in children)

        for child in children:
            assert parent.polygon.buffer(1e-7).contains(child.polygon)

        union = unary_union([c.polygon for c in children])
        assert union.symmetric_difference(parent.polygon).area < 1e-9

    def test_parent_child_roundtrip(self):
        """A cell's parent contains it and lists it among its children."""
        grid = EAQuadGrid(precision=6)
        cell = grid.get_cell_from_point(35.0, 139.0)  # Tokyo
        parent = grid.get_parent(cell)
        assert parent.precision == cell.precision - 1
        assert parent.polygon.buffer(1e-7).contains(cell.polygon)
        child_ids = {c.identifier for c in grid.get_children(parent)}
        assert cell.identifier in child_ids

    def test_children_finest_empty(self):
        """The finest level (1 km) has no children."""
        grid = EAQuadGrid(precision=10)
        cell = grid.get_cell_from_point(0.0, 0.0)
        assert grid.get_children(cell) == []

    def test_parent_coarsest_raises(self):
        """The coarsest level (1024 km) has no parent."""
        grid = EAQuadGrid(precision=0)
        cell = grid.get_cell_from_point(0.0, 0.0)
        with pytest.raises(ValueError, match="no parent"):
            grid.get_parent(cell)


class TestEAQuadEqualArea:
    """Cells have equal ground area regardless of latitude."""

    def test_equal_area_across_latitudes(self):
        """An 8 km cell measures ~64 km^2 at both the equator and 60N."""
        grid = EAQuadGrid(precision=7)
        cell_eq = grid.get_cell_from_point(0.0, 0.0)
        cell_60 = grid.get_cell_from_point(60.0, 10.0)
        assert cell_eq.area_km2 == pytest.approx(64.0, rel=0.03)
        assert cell_60.area_km2 == pytest.approx(64.0, rel=0.03)
        assert cell_eq.area_km2 == pytest.approx(cell_60.area_km2, rel=0.03)


class TestEAQuadNeighbors:
    """Neighbour queries."""

    def test_neighbors_interior(self):
        """An interior cell has 8 unique neighbours, excluding itself."""
        grid = EAQuadGrid(precision=4)
        cell = grid.get_cell_from_point(40.0, -74.0)
        neighbors = grid.get_neighbors(cell)
        assert len(neighbors) == 8
        ids = {n.identifier for n in neighbors}
        assert len(ids) == 8
        assert cell.identifier not in ids

    def test_neighbors_edge_fewer(self):
        """A cell at a domain corner has fewer than 8 neighbours (no wrap)."""
        grid = EAQuadGrid(precision=2)  # 256 km
        cell = grid.get_cell_from_point(-89.9, -179.9)
        neighbors = grid.get_neighbors(cell)
        assert 0 < len(neighbors) < 8


class TestEAQuadBbox:
    """Bounding-box queries."""

    def test_get_cells_in_bbox(self):
        """All returned cells intersect the requested bounding box."""
        grid = EAQuadGrid(precision=4)
        min_lat, min_lon, max_lat, max_lon = 40.0, -74.5, 41.0, -73.5
        cells = grid.get_cells_in_bbox(min_lat, min_lon, max_lat, max_lon)
        assert len(cells) > 0
        bbox = Polygon(
            [
                (min_lon, min_lat),
                (max_lon, min_lat),
                (max_lon, max_lat),
                (min_lon, max_lat),
                (min_lon, min_lat),
            ]
        )
        assert all(c.polygon.intersects(bbox) for c in cells)

    def test_bbox_cell_cap(self):
        """A world-sized box at 1 km exceeds the cell cap and raises."""
        grid = EAQuadGrid(precision=10)
        with pytest.raises(ValueError, match="coarser precision"):
            grid.get_cells_in_bbox(-89.0, -179.0, 89.0, 179.0)


class TestEAQuadEdges:
    """Edge cases and registration."""

    def test_poles_and_dateline(self):
        """Points at the poles and the dateline return valid cells."""
        grid = EAQuadGrid(precision=2)
        for lat, lon in [(89.9, 179.9), (-89.9, -179.9), (0.0, 180.0), (90.0, 0.0)]:
            cell = grid.get_cell_from_point(lat, lon)
            assert isinstance(cell, GridCell)
            assert cell.polygon.is_valid
            assert cell.polygon.area > 0

    def test_registered(self):
        """The grid is discoverable via list_grid_systems."""
        assert "eaquad" in list_grid_systems()["system"].values
