"""
Tests for the rHEALPix DGGS grid implementation.

The interop cases were generated with the ``rhealpixdggs`` reference library
(``WGS84_003``: WGS84 ellipsoid, N_side=3, north/south square 0) so the suite
pins identifier compatibility without depending on that package at test time.
"""

import pytest
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union

from m3s import RHEALPixGrid, list_grid_systems
from m3s.base import GridCell

# ((lat, lon), resolution, SUID) frozen from rhealpixdggs WGS84_003.
RHEALPIXDGGS_CASES = [
    ((40.7128, -74.006), 5, "P01127"),
    ((51.5074, -0.1278), 3, "N226"),
    ((-33.8688, 151.2093), 7, "R8607062"),
    ((0.0, 0.0), 1, "Q3"),
    ((-23.5505, -46.6333), 4, "P7413"),
    ((78.9, 11.9), 6, "N423275"),
    ((-85.0, 100.0), 5, "S44636"),
    ((90.0, 0.0), 2, "N44"),
    ((41.0, 10.0), 5, "Q01006"),
    ((45.0, 10.0), 5, "N21273"),
]


class TestRHEALPixInit:
    """Initialization and precision metadata."""

    def test_init_default(self):
        """Default grid is resolution 5 (~1440 km^2 cells)."""
        grid = RHEALPixGrid()
        assert grid.precision == 5

    def test_init_invalid_precision(self):
        """Out-of-range precision raises ValueError."""
        with pytest.raises(ValueError, match="precision must be between 0 and 15"):
            RHEALPixGrid(precision=-1)
        with pytest.raises(ValueError, match="precision must be between 0 and 15"):
            RHEALPixGrid(precision=16)

    def test_area_km2_analytic(self):
        """Equal-area: one sixth of the Earth at resolution 0, /9 per level."""
        earth_km2 = 4 * 3.141592653589793 * 6371.0072**2  # authalic sphere
        assert RHEALPixGrid(0).area_km2 == pytest.approx(earth_km2 / 6, rel=1e-4)
        assert RHEALPixGrid(3).area_km2 == pytest.approx(
            RHEALPixGrid(0).area_km2 / 9**3
        )


class TestRHEALPixInterop:
    """Identifier compatibility with the rhealpixdggs reference library."""

    @pytest.mark.parametrize("point,res,suid", RHEALPIXDGGS_CASES)
    def test_matches_rhealpixdggs(self, point, res, suid):
        """cell_from_point reproduces the reference library's SUIDs."""
        lat, lon = point
        cell = RHEALPixGrid(res).get_cell_from_point(lat, lon)
        assert cell.identifier == suid
        assert cell.precision == res


class TestRHEALPixCells:
    """Point lookup, identifiers and round-tripping."""

    def test_get_cell_from_point_inside(self):
        """The returned cell polygon contains the query point (equatorial band)."""
        grid = RHEALPixGrid(precision=4)
        for lat, lon in [(40.7, -74.0), (0.0, 0.0), (-33.9, 151.2), (20.0, 77.0)]:
            cell = grid.get_cell_from_point(lat, lon)
            assert isinstance(cell, GridCell)
            assert cell.precision == 4
            assert cell.polygon.buffer(1e-9).contains(Point(lon, lat))

    def test_get_cell_from_point_invalid(self):
        """Out-of-range coordinates raise ValueError."""
        grid = RHEALPixGrid(precision=4)
        with pytest.raises(ValueError, match="Latitude"):
            grid.get_cell_from_point(95.0, 0.0)
        with pytest.raises(ValueError, match="Longitude"):
            grid.get_cell_from_point(0.0, 200.0)

    def test_identifier_roundtrip(self):
        """Round-trip point -> identifier -> cell reproduces the cell."""
        grid = RHEALPixGrid(precision=6)
        cell = grid.get_cell_from_point(48.85, 2.35)  # Paris
        again = grid.get_cell_from_identifier(cell.identifier)
        assert again.identifier == cell.identifier
        assert again.precision == cell.precision
        assert again.polygon.equals(cell.polygon)

    def test_identifier_format(self):
        """Identifiers are a face letter plus one digit 0-8 per resolution."""
        cell = RHEALPixGrid(precision=5).get_cell_from_point(10.0, 10.0)
        assert len(cell.identifier) == 6
        assert cell.identifier[0] in set("NOPQRS")
        assert set(cell.identifier[1:]) <= set("012345678")

    def test_identifier_prefix_is_parent(self):
        """Dropping the last character yields the parent's identifier."""
        grid = RHEALPixGrid(precision=6)
        cell = grid.get_cell_from_point(48.85, 2.35)
        parent = grid.get_parent(cell)
        assert cell.identifier[:-1] == parent.identifier

    def test_invalid_identifiers(self):
        """Bad face letters, digits and lengths raise."""
        grid = RHEALPixGrid(precision=4)
        for bad in ["garbage", "X12", "N9", "", "N" + "0" * 16]:
            with pytest.raises(ValueError):
                grid.get_cell_from_identifier(bad)

    def test_identifier_to_precision(self):
        """Resolution equals the digit count of the identifier."""
        grid = RHEALPixGrid(precision=7)
        ident = grid.get_cell_from_point(0.0, 0.0).identifier
        assert grid.identifier_to_precision(ident) == 7
        assert grid.identifier_to_precision("N") == 0
        assert grid.identifier_to_precision("garbage") is None


class TestRHEALPixHierarchy:
    """Exact aperture-9 containment."""

    def test_exact_nesting(self):
        """The 9 children exactly tile the parent (equatorial band)."""
        grid = RHEALPixGrid(precision=3)
        parent = grid.get_cell_from_point(20.0, -74.0)
        children = grid.get_children(parent)

        assert len(children) == 9
        assert all(c.precision == parent.precision + 1 for c in children)
        assert [c.identifier for c in children] == [
            parent.identifier + str(d) for d in range(9)
        ]

        for child in children:
            assert parent.polygon.buffer(1e-7).contains(child.polygon)

        union = unary_union([c.polygon for c in children])
        assert union.symmetric_difference(parent.polygon).area < 1e-9

    def test_parent_child_roundtrip(self):
        """A cell's parent contains it and lists it among its children."""
        grid = RHEALPixGrid(precision=6)
        cell = grid.get_cell_from_point(35.0, 139.0)  # Tokyo
        parent = grid.get_parent(cell)
        assert parent.precision == cell.precision - 1
        assert parent.polygon.buffer(1e-7).contains(cell.polygon)
        child_ids = {c.identifier for c in grid.get_children(parent)}
        assert cell.identifier in child_ids

    def test_children_finest_empty(self):
        """The finest resolution (15) has no children."""
        grid = RHEALPixGrid(precision=15)
        cell = grid.get_cell_from_point(0.0, 0.0)
        assert grid.get_children(cell) == []

    def test_parent_coarsest_raises(self):
        """Resolution 0 faces have no parent."""
        grid = RHEALPixGrid(precision=0)
        cell = grid.get_cell_from_point(0.0, 0.0)
        with pytest.raises(ValueError, match="no parent"):
            grid.get_parent(cell)


class TestRHEALPixEqualArea:
    """Cells have equal ground area regardless of latitude."""

    def test_equal_area_across_latitudes(self):
        """Geodesic polygon areas match the analytic value at all latitudes."""
        grid = RHEALPixGrid(precision=5)
        for lat, lon in [(0.0, 0.0), (38.0, 10.0), (60.0, 10.0), (-50.0, -70.0)]:
            cell = grid.get_cell_from_point(lat, lon)
            assert cell.area_km2 == pytest.approx(grid.area_km2, rel=0.03)

    def test_native_cell_area(self):
        """native_cell_area returns the exact analytic area in each unit."""
        grid = RHEALPixGrid(precision=5)
        ident = grid.get_cell_from_point(10.0, 10.0).identifier
        assert grid.native_cell_area(ident, "km^2") == grid.area_km2
        assert grid.native_cell_area(ident, "m^2") == pytest.approx(grid.area_km2 * 1e6)
        assert grid.native_cell_area(ident, "bogus") is None


class TestRHEALPixNeighbors:
    """Neighbour queries."""

    def test_neighbors_interior(self):
        """An interior cell has 8 unique neighbours, excluding itself."""
        grid = RHEALPixGrid(precision=4)
        for lat, lon in [(20.0, -74.0), (45.0, 7.0)]:  # equatorial + polar square
            cell = grid.get_cell_from_point(lat, lon)
            neighbors = grid.get_neighbors(cell)
            ids = {n.identifier for n in neighbors}
            assert len(neighbors) == len(ids) == 8
            assert cell.identifier not in ids

    def test_neighbors_share_boundary(self):
        """Edge neighbours touch the cell (equatorial band)."""
        grid = RHEALPixGrid(precision=4)
        cell = grid.get_cell_from_point(20.0, -74.0)
        touching = sum(
            1
            for n in grid.get_neighbors(cell)
            if n.polygon.buffer(1e-9).intersects(cell.polygon)
        )
        assert touching == 8


class TestRHEALPixBbox:
    """Bounding-box queries."""

    def test_get_cells_in_bbox(self):
        """All returned cells intersect the box and cover its sample points."""
        grid = RHEALPixGrid(precision=5)
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
        # Cells of interior probe points are present.
        ids = {c.identifier for c in cells}
        for lat, lon in [(40.5, -74.0), (40.1, -74.4), (40.9, -73.6)]:
            assert grid.get_cell_from_point(lat, lon).identifier in ids

    def test_bbox_cell_cap(self):
        """A world-sized box at a fine resolution exceeds the cap and raises."""
        grid = RHEALPixGrid(precision=10)
        with pytest.raises(ValueError, match="coarser precision"):
            grid.get_cells_in_bbox(-89.0, -179.0, 89.0, 179.0)


class TestRHEALPixEdges:
    """Edge cases and registration."""

    def test_poles_and_dateline(self):
        """Points at the poles and the dateline return valid cells."""
        grid = RHEALPixGrid(precision=2)
        for lat, lon in [(89.9, 179.9), (-89.9, -179.9), (0.0, 180.0), (90.0, 0.0)]:
            cell = grid.get_cell_from_point(lat, lon)
            assert isinstance(cell, GridCell)
            assert cell.precision == 2

    def test_pole_cell_is_centre_child(self):
        """The pole sits in the centre child of the polar face at every level."""
        for res in (1, 2, 3):
            cell = RHEALPixGrid(res).get_cell_from_point(90.0, 0.0)
            assert cell.identifier == "N" + "4" * res
            cell = RHEALPixGrid(res).get_cell_from_point(-90.0, 0.0)
            assert cell.identifier == "S" + "4" * res

    def test_registered(self):
        """The grid is discoverable via list_grid_systems."""
        assert "rhealpix" in list_grid_systems()["system"].values
