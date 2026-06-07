"""ADR 0001 §3: the core owns a geodesic area formula (replacing per-cell UTM).

Validate it against H3's trusted spherical ``cell_area`` (both are spherical, so
they should agree closely) and sanity-check geohash areas. This is the area
re-baseline reference; old UTM-planar numbers are intentionally not used.
"""

import h3
import m3s_core as mc
import pytest


@pytest.mark.parametrize("precision", [0, 5, 9])
def test_geodesic_area_matches_h3_spherical(precision):
    # An H3 cell near London; compare core geodesic area to h3.cell_area.
    cid, ring, _ = mc.h3_cell_from_point(51.5074, -0.1278, precision)
    core = mc.geodesic_area_km2(ring)
    native = h3.cell_area(cid, unit="km^2")
    assert core == pytest.approx(native, rel=0.02)


def test_geohash_area_positive_and_decreasing():
    areas = [
        mc.geodesic_area_km2(mc.gh_cell_from_point(48.85, 2.35, p)[1])
        for p in (2, 5, 8)
    ]
    assert all(a > 0 for a in areas)
    assert areas[0] > areas[1] > areas[2]
