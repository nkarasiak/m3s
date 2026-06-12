"""Tests for ergonomic API additions and removal of deprecated aliases."""

import pytest
from shapely.geometry import Polygon

import m3s
from m3s import H3Grid, QuadkeyGrid, S2Grid, SlippyGrid
from m3s.api.grid_collection import GridCellCollection

POLY = Polygon([(2.30, 48.84), (2.40, 48.84), (2.40, 48.94), (2.30, 48.94)])


# --- grid() / grids() factory -------------------------------------------------


def test_grids_lists_all_systems():
    """grids() returns all 13 system names, sorted."""
    names = m3s.grids()
    assert names == sorted(names)
    for expected in ("h3", "geohash", "s2", "eaquad", "rhealpix", "mgrs", "a5"):
        assert expected in names
    assert len(names) == 13


def test_grid_returns_wrapper_and_is_case_insensitive():
    """grid() is case-insensitive and returns the shared singleton wrapper."""
    g_lower = m3s.grid("h3")
    g_upper = m3s.grid("H3")
    assert g_lower is g_upper
    cell = g_lower.from_geometry((2.35, 48.85), precision=7)
    assert cell.precision == 7


def test_grid_precision_binding():
    """grid(name, precision=) returns a wrapper bound to that precision."""
    g = m3s.grid("h3", precision=9)
    cell = g.from_geometry((2.35, 48.85))
    assert cell.precision == 9


def test_grid_unknown_raises():
    """grid() raises ValueError for an unknown system name."""
    with pytest.raises(ValueError, match="Unknown grid system"):
        m3s.grid("not-a-grid")


# --- from_ids round-trip ------------------------------------------------------


def test_from_ids_round_trip():
    """from_ids() rebuilds a wrapper-aware collection from identifiers."""
    cells = m3s.H3.from_geometry(POLY, precision=8)
    restored = m3s.H3.from_ids(cells.to_ids())
    assert set(restored.ids) == set(cells.ids)
    assert len(restored.neighbors()) >= len(restored)


# --- persistence: to_geojson / save ------------------------------------------


def test_to_geojson_feature_collection():
    """to_geojson() returns a FeatureCollection with one feature per cell."""
    cells = m3s.H3.from_geometry(POLY, precision=8)
    gj = cells.to_geojson()
    assert gj["type"] == "FeatureCollection"
    assert len(gj["features"]) == len(cells)
    assert gj["features"][0]["type"] == "Feature"


def test_save_round_trip(tmp_path):
    """save() writes a GeoJSON file that reloads to the same cell ids."""
    gpd = pytest.importorskip("geopandas")
    cells = m3s.H3.from_geometry(POLY, precision=8)
    out = tmp_path / "cells.geojson"
    cells.save(str(out))
    assert out.exists()
    reloaded = gpd.read_file(out)
    assert set(reloaded["cell_id"]) == set(cells.ids)


# --- collection set-ops -------------------------------------------------------


def test_collection_add_dedup_and_unique():
    """Adding collections de-duplicates by identifier."""
    cells = m3s.H3.from_geometry(POLY, precision=8)
    combined = cells[:3] + cells[2:5]  # overlap at index 2
    assert len(combined) == 5
    assert len(combined.unique()) == len(combined)


def test_collection_contains_and_ids():
    """Membership works by GridCell or id; ids mirrors to_ids()."""
    cells = m3s.H3.from_geometry(POLY, precision=8)
    first = cells[0]
    assert first in cells
    assert first.id in cells
    assert cells.ids == cells.to_ids()


def test_collection_dissolve():
    """dissolve() merges cell polygons into one geometry."""
    cells = m3s.H3.from_geometry(POLY, precision=8)
    merged = cells.dissolve()
    assert merged.area > 0
    assert merged.area <= sum(c.polygon.area for c in cells) + 1e-9


def test_empty_collection_dissolve():
    """dissolve() on an empty collection returns an empty geometry."""
    assert GridCellCollection([]).dissolve().is_empty


# --- GridCell.area units ------------------------------------------------------


def test_area_units():
    """area() converts km2 to m2/ha/mi2 with the documented factors."""
    cell = m3s.H3.from_geometry((2.35, 48.85), precision=8)
    assert cell.area("km2") == pytest.approx(cell.area_km2)
    assert cell.area("m2") == pytest.approx(cell.area_km2 * 1_000_000)
    assert cell.area("ha") == pytest.approx(cell.area_km2 * 100)
    assert cell.area("mi2") == pytest.approx(cell.area_km2 * 0.3861021585424458)


def test_area_invalid_unit():
    """area() raises ValueError for an unrecognised unit."""
    cell = m3s.H3.from_geometry((2.35, 48.85), precision=8)
    with pytest.raises(ValueError, match="Unknown area unit"):
        cell.area("furlong2")


# --- neighbors include_self ---------------------------------------------------


def test_neighbors_include_self_toggle():
    """include_self controls whether the origin cell is in the result."""
    cell = m3s.H3.from_geometry((2.35, 48.85), precision=8)
    with_self = m3s.H3.neighbors(cell, include_self=True)
    without_self = m3s.H3.neighbors(cell, include_self=False)
    assert cell.id in with_self.ids
    assert cell.id not in without_self.ids
    assert len(without_self) == len(with_self) - 1


# --- viz delegates (skip if optional deps missing) ----------------------------


def test_explore_returns_map():
    """explore() delegates to GeoPandas and returns a folium.Map."""
    folium = pytest.importorskip("folium")
    pytest.importorskip("matplotlib")
    pytest.importorskip("mapclassify")
    cells = m3s.H3.from_geometry(POLY, precision=8)
    fmap = cells.explore()
    assert isinstance(fmap, folium.Map)


def test_plot_returns_axes():
    """plot() delegates to GeoPandas and returns a matplotlib Axes."""
    plt = pytest.importorskip("matplotlib.pyplot")
    cells = m3s.H3.from_geometry(POLY, precision=8)
    ax = cells.plot()
    assert ax is not None
    plt.close("all")


# --- deprecated aliases removed ----------------------------------------------


def test_deprecated_aliases_removed():
    """The old resolution=/level=/zoom= keywords are gone (raise TypeError)."""
    with pytest.raises(TypeError):
        H3Grid(resolution=7)
    with pytest.raises(TypeError):
        S2Grid(level=10)
    with pytest.raises(TypeError):
        QuadkeyGrid(level=12)
    with pytest.raises(TypeError):
        SlippyGrid(zoom=12)


def test_repr_uses_precision():
    """Grid reprs report the standardized precision keyword."""
    assert "precision=5" in repr(S2Grid(5))
    assert "precision=12" in repr(QuadkeyGrid(12))
    assert "precision=12" in repr(SlippyGrid(12))
