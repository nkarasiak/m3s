"""
Tests for the h3-py vocabulary layer (m3s.api.h3_verbs.H3VerbsMixin).

Covers three contracts:

1. Exact parity with the h3 library for the H3 backend (strong oracle, since
   H3Grid delegates to the same C library).
2. Cross-backend behaviour of the Tier-1 verbs on every singleton (object
   types, round-trips, validity, area units).
3. Capability boundaries: backends that cannot serve a verb raise
   ``NotImplementedError``.
"""

import h3
import pytest

import m3s
from m3s.api.grid_collection import GridCellCollection
from m3s.base import GridCell

# (lat, lng) sample points, h3-native order.
PARIS = (48.8566, 2.3522)
NYC = (40.7128, -74.0060)

ALL_SINGLETONS = [
    "Geohash",
    "MGRS",
    "H3",
    "S2",
    "Quadkey",
    "Slippy",
    "CSquares",
    "GARS",
    "Maidenhead",
    "PlusCode",
]

HIERARCHICAL = ["H3", "S2", "Quadkey", "Slippy", "Geohash", "PlusCode", "CSquares"]
NON_HIERARCHICAL = [
    "MGRS",
    "GARS",
    "Maidenhead",
]


# ----------------------------------------------------------------------
# 1. H3 parity (exact oracle)
# ----------------------------------------------------------------------


@pytest.mark.parametrize("lat,lng", [PARIS, NYC])
@pytest.mark.parametrize("res", [5, 7, 9, 11])
def test_h3_latlng_to_cell_parity(lat, lng, res):
    """latlng_to_cell returns a GridCell whose id matches the h3 library."""
    cell = m3s.H3.latlng_to_cell(lat, lng, res)
    assert isinstance(cell, GridCell)
    assert cell.id == h3.latlng_to_cell(lat, lng, res)


@pytest.mark.parametrize("res", [4, 8, 12])
def test_h3_inspection_parity(res):
    """Inspection verbs (center, boundary, resolution, validity) match h3."""
    cell = m3s.H3.latlng_to_cell(*PARIS, res)
    cid = cell.id
    assert m3s.H3.cell_to_latlng(cell) == h3.cell_to_latlng(cid)
    # Boundary geometry now comes from the shared Rust core (h3o), not the h3
    # Python lib, so it matches to ~1e-13 rather than byte-exact (same
    # deliberate re-baseline as cell area, ADR 0001 §3).
    boundary = m3s.H3.cell_to_boundary(cell)
    expected = h3.cell_to_boundary(cid)
    assert len(boundary) == len(expected)
    for (lat_, lng_), (elat, elng) in zip(boundary, expected, strict=True):
        assert lat_ == pytest.approx(elat) and lng_ == pytest.approx(elng)
    assert m3s.H3.get_resolution(cell) == h3.get_resolution(cid) == res
    assert m3s.H3.is_valid_cell(cid) is True
    assert m3s.H3.is_valid_cell("not-a-cell") is False


@pytest.mark.parametrize("unit", ["km^2", "m^2", "rads^2"])
def test_h3_cell_area_parity(unit):
    """cell_area matches h3 across all area units."""
    cell = m3s.H3.latlng_to_cell(*NYC, 9)
    assert m3s.H3.cell_area(cell, unit) == pytest.approx(
        h3.cell_area(cell.id, unit=unit)
    )


def test_h3_hierarchy_parity():
    """cell_to_parent/children and children_size match h3."""
    cell = m3s.H3.latlng_to_cell(*PARIS, 9)
    parent = m3s.H3.cell_to_parent(cell, 7)
    assert isinstance(parent, GridCell)
    assert parent.id == h3.cell_to_parent(cell.id, 7)

    children = m3s.H3.cell_to_children(cell, 11)
    assert isinstance(children, GridCellCollection)
    assert set(children.to_ids()) == set(h3.cell_to_children(cell.id, 11))
    assert m3s.H3.cell_to_children_size(cell, 11) == h3.cell_to_children_size(
        cell.id, 11
    )


def test_h3_traversal_membership_parity():
    """grid_disk/grid_ring membership matches h3."""
    cell = m3s.H3.latlng_to_cell(*PARIS, 9)
    assert set(m3s.H3.grid_disk(cell, 2).to_ids()) == set(h3.grid_disk(cell.id, 2))
    assert set(m3s.H3.grid_ring(cell, 1).to_ids()) == set(h3.grid_ring(cell.id, 1))


def test_h3_compact_roundtrip_parity():
    """compact_cells/uncompact_cells match h3 and round-trip."""
    res = 8
    cell = m3s.H3.latlng_to_cell(*PARIS, 7)
    children = m3s.H3.cell_to_children(cell, res)
    compacted = m3s.H3.compact_cells(children)
    assert set(compacted.to_ids()) == set(h3.compact_cells(children.to_ids()))
    expanded = m3s.H3.uncompact_cells(compacted, res)
    assert set(expanded.to_ids()) == set(children.to_ids())


def test_h3_great_circle_distance_parity():
    """great_circle_distance matches h3 across all units."""
    for unit in ("km", "m", "rads"):
        assert m3s.H3.great_circle_distance(PARIS, NYC, unit) == pytest.approx(
            h3.great_circle_distance(PARIS, NYC, unit=unit)
        )


# ----------------------------------------------------------------------
# 2. Cross-backend Tier-1 behaviour
# ----------------------------------------------------------------------


@pytest.mark.parametrize("name", ALL_SINGLETONS)
def test_tier1_object_types_and_validity(name):
    """Tier-1 verbs return objects and accept GridCell or id on every backend."""
    grid = getattr(m3s, name)
    res = grid._default_precision
    cell = grid.latlng_to_cell(*PARIS, res)
    assert isinstance(cell, GridCell)

    # Accepts both a GridCell and a bare id string.
    assert grid.get_resolution(cell) == grid.get_resolution(cell.id) == res
    assert grid.is_valid_cell(cell) is True
    assert grid.is_valid_cell("!!not-valid!!") is False

    lat, lng = grid.cell_to_latlng(cell)
    assert -90 <= lat <= 90 and -180 <= lng <= 180

    boundary = grid.cell_to_boundary(cell)
    assert len(boundary) >= 3
    # open ring: first vertex not repeated at the end
    assert boundary[0] != boundary[-1]


@pytest.mark.parametrize("name", ALL_SINGLETONS)
def test_tier1_area_units(name):
    """cell_area unit conversion is consistent and rejects unknown units."""
    grid = getattr(m3s, name)
    cell = grid.latlng_to_cell(*PARIS, grid._default_precision)
    km2 = grid.cell_area(cell, "km^2")
    m2 = grid.cell_area(cell, "m^2")
    assert m2 == pytest.approx(km2 * 1_000_000, rel=1e-9)
    with pytest.raises(ValueError):
        grid.cell_area(cell, "furlongs")


@pytest.mark.parametrize(
    "name", ["Geohash", "S2", "Quadkey", "Slippy", "Maidenhead", "GARS", "CSquares"]
)
def test_tier1_id_string_roundtrip(name):
    """id-string path resolves the right precision (round-trips to same cell)."""
    grid = getattr(m3s, name)
    cell = grid.latlng_to_cell(*PARIS, grid._default_precision)
    res = grid.get_resolution(cell.id)
    assert res == grid._default_precision
    lat, lng = grid.cell_to_latlng(cell.id)
    assert grid.latlng_to_cell(lat, lng, res).id == cell.id


# ----------------------------------------------------------------------
# 3. Capability boundaries
# ----------------------------------------------------------------------


@pytest.mark.parametrize("name", NON_HIERARCHICAL)
def test_non_hierarchical_parent_children_raise(name):
    """Non-hierarchical backends raise on cell_to_parent/children."""
    grid = getattr(m3s, name)
    cell = grid.latlng_to_cell(*PARIS, grid._default_precision)
    with pytest.raises(NotImplementedError):
        grid.cell_to_parent(cell)
    with pytest.raises(NotImplementedError):
        grid.cell_to_children(cell)


@pytest.mark.parametrize("name", [n for n in ALL_SINGLETONS if n != "H3"])
def test_h3_only_verbs_raise_on_other_backends(name):
    """H3-only verbs raise NotImplementedError on non-H3 backends."""
    grid = getattr(m3s, name)
    cell = grid.latlng_to_cell(*PARIS, grid._default_precision)
    with pytest.raises(NotImplementedError):
        grid.is_pentagon(cell)
    with pytest.raises(NotImplementedError):
        grid.str_to_int(cell)
    with pytest.raises(NotImplementedError):
        grid.get_num_cells(1)


@pytest.mark.parametrize("name", HIERARCHICAL)
def test_hierarchical_parent_children_roundtrip(name):
    """Hierarchical backends round-trip a cell through children then parent."""
    grid = getattr(m3s, name)
    # Use a resolution with room for a finer level (CSquares' default is its max).
    lo, hi = grid._get_precision_range()
    res = max(lo, min(grid._default_precision, hi - 1))
    cell = grid.latlng_to_cell(*PARIS, res)
    children = grid.cell_to_children(cell, res + 1)
    assert isinstance(children, GridCellCollection)
    assert len(children) >= 1
    parent = grid.cell_to_parent(children[0], res)
    assert isinstance(parent, GridCell)
    assert parent.id == cell.id


def test_traversal_returns_collections():
    """Traversal verbs return GridCellCollections with correct membership."""
    cell = m3s.S2.latlng_to_cell(*PARIS, 12)
    disk = m3s.S2.grid_disk(cell, 1)
    assert isinstance(disk, GridCellCollection)
    assert cell.id in disk.to_ids()
    ring = m3s.S2.grid_ring(cell, 1)
    assert cell.id not in ring.to_ids()
    assert m3s.S2.are_neighbor_cells(cell, ring[0]) is True
