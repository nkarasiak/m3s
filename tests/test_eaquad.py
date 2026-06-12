"""
Tests for the EA-Quad (Equal-Area Quadtree) grid implementation.
"""

import pytest
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union

from m3s import EAQuadGrid, list_grid_systems
from m3s.base import GridCell
from m3s.eaquad import _d2xy, _format_id, _ncols, _parse_id, _xy2d


class TestEAQuadInit:
    """Initialization and precision/size mapping."""

    def test_init_default(self):
        """Default grid is precision 4 (64 km cells)."""
        grid = EAQuadGrid()
        assert grid.precision == 4
        assert grid.size_km == 64

    def test_init_custom_precision(self):
        """Finest/coarsest precisions map to ~0.98 m / 1024 km."""
        assert EAQuadGrid(precision=10).size_km == 1
        assert EAQuadGrid(precision=0).size_km == 1024
        assert EAQuadGrid(precision=20).size_km == pytest.approx(2.0**-10)

    @pytest.mark.parametrize(
        "precision,size_km",
        [(0, 1024), (1, 512), (4, 64), (7, 8), (10, 1), (11, 0.5), (14, 0.0625)],
    )
    def test_precision_size_mapping(self, precision, size_km):
        """Precision maps to size_km = 2 ** (10 - precision)."""
        assert EAQuadGrid(precision=precision).size_km == size_km

    def test_init_invalid_precision(self):
        """Out-of-range precision raises ValueError."""
        with pytest.raises(ValueError, match="precision must be between 0 and 20"):
            EAQuadGrid(precision=-1)
        with pytest.raises(ValueError, match="precision must be between 0 and 20"):
            EAQuadGrid(precision=21)

    def test_area_km2_analytic(self):
        """Equal-area: cell area is exactly size_km ** 2."""
        assert EAQuadGrid(precision=7).area_km2 == 64.0
        assert EAQuadGrid(precision=10).area_km2 == 1.0
        assert EAQuadGrid(precision=0).area_km2 == 1024.0**2
        assert EAQuadGrid(precision=20).area_km2 == pytest.approx(2.0**-20)


class TestEAQuadIdentifiers:
    """Hex-token codec: Hilbert path + sentinel bit, S2-style."""

    def test_identifier_is_short_hex_token(self):
        """Identifiers are short lowercase hex tokens without trailing zeros."""
        for precision in (0, 4, 10, 20):
            cell = EAQuadGrid(precision).get_cell_from_point(40.7, -74.0)
            ident = cell.identifier
            assert 1 <= len(ident) <= 16
            assert set(ident) <= set("0123456789abcdef")
            assert not ident.endswith("0")

    def test_coarser_cells_have_shorter_tokens(self):
        """Token length grows with precision (~1 hex char per 2 levels)."""
        lengths = [
            len(EAQuadGrid(p).get_cell_from_point(40.7, -74.0).identifier)
            for p in (0, 4, 10, 20)
        ]
        assert lengths == sorted(lengths)
        assert lengths[0] < lengths[-1]

    def test_identifier_roundtrip(self):
        """Round-trip point -> identifier -> cell reproduces the cell."""
        grid = EAQuadGrid(precision=6)
        cell = grid.get_cell_from_point(48.85, 2.35)  # Paris
        again = grid.get_cell_from_identifier(cell.identifier)
        assert again.identifier == cell.identifier
        assert again.precision == cell.precision
        assert again.polygon.equals(cell.polygon)

    def test_codec_roundtrip(self):
        """_format_id and _parse_id are exact inverses."""
        for level, col, row in [(6, 0, 0), (10, 17, 5), (16, 12345, 4321)]:
            token = _format_id(level, col, row)
            assert _parse_id(token) == (level, col, row)

    def test_hilbert_is_hierarchical(self):
        """Parent Hilbert index is the child index shifted right by 2 bits."""
        for level in (7, 13, 26):
            for k in range(0, 50, 7):
                n = 1 << level
                x, y = k % n, (k * 977) % n
                assert _xy2d(level - 1, x // 2, y // 2) == _xy2d(level, x, y) >> 2
                assert _d2xy(level, _xy2d(level, x, y)) == (x, y)

    def test_parent_id_is_bit_prefix(self):
        """A parent's 64-bit path is a bit-prefix of its child's (S2 property)."""
        grid = EAQuadGrid(precision=6)
        cell = grid.get_cell_from_point(48.85, 2.35)
        parent = grid.get_parent(cell)
        level = 6 + 6
        child_bits = int(cell.identifier, 16) << (4 * (16 - len(cell.identifier)))
        parent_bits = int(parent.identifier, 16) << (4 * (16 - len(parent.identifier)))
        shift = 64 - 2 * (level - 1)
        assert parent_bits >> shift == child_bits >> shift

    def test_invalid_identifiers(self):
        """Non-hex strings, zero ids and bad levels raise."""
        grid = EAQuadGrid(precision=4)
        for bad in ["garbage", "XYZ", "", "0", "00", "f" * 17]:
            with pytest.raises(ValueError):
                grid.get_cell_from_identifier(bad)

    def test_identifier_to_precision(self):
        """Precision is recovered from the token's sentinel bit."""
        for precision in (0, 7, 10, 20):
            grid = EAQuadGrid(precision=precision)
            ident = grid.get_cell_from_point(10.0, 10.0).identifier
            assert grid.identifier_to_precision(ident) == precision
        assert EAQuadGrid().identifier_to_precision("garbage") is None


class TestEAQuadCells:
    """Point lookup."""

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

    def test_subkilometre_cells(self):
        """Sub-km precisions return small cells that still contain the point."""
        grid = EAQuadGrid(precision=16)  # ~15.6 m
        cell = grid.get_cell_from_point(48.8584, 2.2945)  # Eiffel Tower
        assert cell.precision == 16
        assert cell.polygon.buffer(1e-12).contains(Point(2.2945, 48.8584))
        assert cell.area_km2 == pytest.approx(0.000244140625, rel=0.05)


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
        """The finest level (~0.98 m) has no children."""
        grid = EAQuadGrid(precision=20)
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
        """A polar-row cell has fewer than 8 neighbours (latitude does not wrap)."""
        grid = EAQuadGrid(precision=2)  # 256 km
        cell = grid.get_cell_from_point(-89.9, -179.9)
        neighbors = grid.get_neighbors(cell)
        assert 0 < len(neighbors) < 8

    def test_neighbors_wrap_antimeridian(self):
        """Longitude wraps: east neighbour of the last column is a column-0 cell."""
        grid = EAQuadGrid(precision=2)  # 256 km
        east_cell = grid.get_cell_from_point(0.0, 180.0)
        level, col, row = _parse_id(east_cell.identifier)
        assert col == _ncols(level) - 1  # easternmost column

        neighbors = grid.get_neighbors(east_cell)
        ids = {n.identifier for n in neighbors}
        # east neighbour wraps to column 0 at the same row
        assert _format_id(level, 0, row) in ids
        # still <= 8, unique, excludes self
        assert len(neighbors) == len(ids) <= 8
        assert east_cell.identifier not in ids


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

    def test_high_latitude_valid(self):
        """Coverage is global to +/-90: high-latitude points return valid cells."""
        grid = EAQuadGrid(precision=2)
        for lat in (85.0, 88.0, 90.0, -90.0):
            cell = grid.get_cell_from_point(lat, 10.0)
            assert isinstance(cell, GridCell)
            assert cell.polygon.is_valid
            assert cell.polygon.area > 0

    def test_boundary_cell_clipped_with_exact_area(self):
        """Boundary cells are clipped; native_cell_area reports the true area."""
        grid = EAQuadGrid(precision=2)  # 256 km
        east_cell = grid.get_cell_from_point(0.0, 180.0)
        level, col, _ = _parse_id(east_cell.identifier)
        assert col == _ncols(level) - 1  # easternmost (partial) column

        # The clipped boundary cell is physically narrower than a full nominal
        # cell. EPSG:6933 x is linear in longitude, so the clipped cell's lon
        # span is smaller than an interior (full) cell's at the same row.
        e0, _, e1, _ = east_cell.polygon.bounds
        interior = grid.get_cell_from_point(0.0, 170.0)
        f0, _, f1, _ = interior.polygon.bounds
        assert (e1 - e0) < (f1 - f0)

        # The grid-level area_km2 stays nominal; native_cell_area is exact.
        assert grid.area_km2 == 256.0**2
        clipped = grid.native_cell_area(east_cell.identifier, "km^2")
        assert clipped < grid.area_km2
        # ... and matches the geodesic polygon area closely.
        assert clipped == pytest.approx(east_cell.area_km2, rel=0.03)
        # Interior cells report the nominal area exactly.
        assert grid.native_cell_area(interior.identifier, "km^2") == pytest.approx(
            grid.area_km2
        )
        # Unit conversions.
        assert grid.native_cell_area(east_cell.identifier, "m^2") == pytest.approx(
            clipped * 1e6
        )
        assert grid.native_cell_area(east_cell.identifier, "bogus") is None

    def test_registered(self):
        """The grid is discoverable via list_grid_systems."""
        assert "eaquad" in list_grid_systems()["system"].values
