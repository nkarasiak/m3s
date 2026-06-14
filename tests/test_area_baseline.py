"""
Golden baseline for nominal cell area (``Grid.area_km2``).

After the area-model unification, nominal area has a single source: the shared
core, via geodesic sampling at the canonical latitude (45°) for most grids, and
an exact analytic/core value for the equal-area grids (a5, rhealpix, eaquad) and
the approximately-equal-area s2. These values were deliberately re-baselined off
the former hand-maintained per-grid tables (which disagreed with each other —
e.g. geohash precision 5 was listed as both 4892 and 2.443 km²).

This freezes the re-baselined numbers so any future change to the sampler, the
canonical latitude, or an override is caught. Regenerate intentionally if the
area model changes on purpose.
"""

import pytest

from m3s.api.precision import AreaCalculator
from m3s.registry import GRID_CLASSES

# grid -> {precision: expected area_km2}. Frozen 2026-06-14.
BASELINE = {
    "a5": {0: 42505468.73161993, 15: 0.03166904205949599, 30: 2.9494093786455684e-11},
    "geohash": {1: 9337177.355316484, 6: 0.5276068960331464, 12: 4.913958026469439e-10},
    "mgrs": {0: 9986.045648171466, 2: 0.9985769511754701, 5: 9.985760055709467e-07},
    "h3": {0: 4099709.359748919, 7: 5.148941050244729, 15: 8.931923941682307e-07},
    "quadkey": {
        1: 127041098.56155221,
        12: 47.76268265419974,
        23: 1.1385875545223104e-05,
    },
    "s2": {0: 85012000.0, 15: 0.07917359471321106, 30: 7.373615606987016e-11},
    "slippy": {
        0: 508164394.24620885,
        11: 190.84362759779003,
        22: 4.554352628187403e-05,
    },
    "csquares": {1: 873182.0184811564, 3: 8666.174570521893, 5: 87.35278740761427},
    "gars": {1: 2176.1634821641073, 2: 545.2381887267194, 3: 60.6704979260537},
    "maidenhead": {1: 1746364.0369623129, 2: 17332.349141043785, 4: 0.3035623228904166},
    "pluscode": {
        1: 3769464.813814779,
        4: 0.05464223147231803,
        7: 8.538110098736088e-10,
    },
    "eaquad": {0: 1048576.0, 10: 1.0, 20: 9.5367431640625e-07},
    "rhealpix": {0: 85010936.9540148, 7: 17.77367508633545, 15: 4.1289265880054957e-07},
}


@pytest.mark.parametrize(
    ("name", "precision", "expected"),
    [(name, p, area) for name, table in BASELINE.items() for p, area in table.items()],
)
def test_area_km2_baseline(name: str, precision: int, expected: float) -> None:
    """``Grid.area_km2`` matches the frozen re-baselined value."""
    grid = GRID_CLASSES[name](precision=precision)
    assert grid.area_km2 == pytest.approx(expected, rel=1e-9)


@pytest.mark.parametrize(
    ("name", "precision", "_expected"),
    [(name, p, area) for name, table in BASELINE.items() for p, area in table.items()],
)
def test_areacalculator_matches_grid(
    name: str, precision: int, _expected: float
) -> None:
    """
    ``AreaCalculator`` and ``Grid.area_km2`` report the same nominal area.

    This is the anti-drift guarantee of the unified area model: precision
    selection and the grid object read the *same* single source, so they can
    never disagree (the failure mode the old dual tables had).
    """
    grid = GRID_CLASSES[name](precision=precision)
    calc_area = AreaCalculator(name).get_area(precision)
    assert calc_area == pytest.approx(grid.area_km2, rel=1e-12)
