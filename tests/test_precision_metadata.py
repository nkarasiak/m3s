"""
Cross-grid precision-metadata invariants.

These tests lock the single source of truth introduced for precision bounds:
each grid class exposes ``MIN_PRECISION``/``MAX_PRECISION``/``DEFAULT_PRECISION``,
its constructor validates against them, and every consumer (``GridWrapper``,
``AreaCalculator``, ``PrecisionSelector``) derives its range from the class
rather than keeping a separate copy that can drift.
"""

import warnings

import pytest

import m3s
from m3s.api.precision import (
    _GRID_CLASSES,
    USE_CASE_PRESETS,
    AreaCalculator,
    PrecisionSelector,
)

# Public grid singletons -> their backing grid class.
SINGLETON_NAMES = [
    "A5",
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
    "EAQuad",
    "RHEALPix",
]


def _construct(cls, precision):
    """Construct a grid at ``precision``, silencing deprecation warnings."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return cls(precision=precision)


@pytest.mark.parametrize("name", list(_GRID_CLASSES))
def test_range_matches_constructor_validation(name):
    """(MIN, MAX) bounds exactly match what the constructor accepts/rejects."""
    cls = _GRID_CLASSES[name]
    lo, hi = cls.precision_range()
    assert (lo, hi) == (cls.MIN_PRECISION, cls.MAX_PRECISION)

    # Every in-range precision constructs.
    for p in range(lo, hi + 1):
        _construct(cls, p)

    # Just outside the range is rejected.
    with pytest.raises(ValueError):
        _construct(cls, lo - 1)
    with pytest.raises(ValueError):
        _construct(cls, hi + 1)


@pytest.mark.parametrize("name", SINGLETON_NAMES)
def test_wrapper_range_derives_from_class(name):
    """GridWrapper exposes the class range, and can build both extremes."""
    wrapper = getattr(m3s, name)
    cls = wrapper._grid_class
    assert wrapper._get_precision_range() == cls.precision_range()

    lo, hi = cls.precision_range()
    assert wrapper._get_grid(lo).precision == lo
    assert wrapper._get_grid(hi).precision == hi


@pytest.mark.parametrize("name", list(_GRID_CLASSES))
def test_default_precision_in_range(name):
    """The advertised default precision is within the valid range."""
    cls = _GRID_CLASSES[name]
    lo, hi = cls.precision_range()
    assert lo <= cls.DEFAULT_PRECISION <= hi


@pytest.mark.parametrize("name", list(_GRID_CLASSES))
def test_area_calculator_range_matches_class(name):
    """AreaCalculator derives its range from the grid class, not a copy."""
    calc = AreaCalculator(name)
    assert (calc.min_precision, calc.max_precision) == _GRID_CLASSES[
        name
    ].precision_range()
    # Area lookup works at both extremes without IndexError.
    calc.get_area(calc.min_precision)
    calc.get_area(calc.max_precision)


class TestEAQuadPrecisionAPIs:
    """Regression: EA-Quad precision APIs must not instantiate out-of-range."""

    def test_find_precision_for_area_no_crash(self):
        """Previously raised ValueError by constructing EAQuadGrid(11)."""
        # 0.3 km² is below the finest (1 km²) cell, so the search runs to the
        # end of the range -- the case that used to crash.
        assert m3s.EAQuad.find_precision_for_area(0.3) in range(0, 21)

    @pytest.mark.parametrize("target", [0.3, 1.0, 4000.0, 5_000_000.0])
    def test_find_precision_for_area_in_range(self, target):
        """Area-based selection stays within the valid precision range."""
        assert m3s.EAQuad.find_precision_for_area(target) in range(0, 21)

    def test_find_precision_in_range(self):
        """Geometry-based selection stays within the valid precision range."""
        from shapely.geometry import box

        assert m3s.EAQuad.find_precision(box(0, 0, 40, 40)) in range(0, 21)

    def test_area_calculator_eaquad(self):
        """AreaCalculator supports EA-Quad with its analytic cell areas."""
        calc = AreaCalculator("eaquad")
        assert (calc.min_precision, calc.max_precision) == (0, 20)
        assert calc.get_area(4) == 4096.0  # 64 km cells
        assert calc.get_area(10) == 1.0  # 1 km cells
        assert calc.get_area(20) == pytest.approx(9.5367431640625e-07)  # ~1 m

    def test_precision_selector_eaquad_for_area(self):
        """PrecisionSelector resolves an EA-Quad precision for a target area."""
        rec = PrecisionSelector("eaquad").for_area(4096.0)
        assert rec.precision == 4

    def test_precision_selector_eaquad_for_use_case(self):
        """EA-Quad is wired into the use-case presets."""
        rec = PrecisionSelector("eaquad").for_use_case("city")
        assert 0 <= rec.precision <= 20


USE_CASES = [
    "global",
    "continental",
    "country",
    "region",
    "city",
    "neighborhood",
    "street",
    "building",
    "room",
]


@pytest.mark.parametrize("name", [n for n in _GRID_CLASSES if n in USE_CASE_PRESETS])
@pytest.mark.parametrize("use_case", USE_CASES)
def test_for_use_case_clamped_to_range(name, use_case):
    """Use-case presets never resolve outside the grid's valid precision range.

    Some presets name a finer level than a coarse grid (PlusCode/Maidenhead/
    MGRS) supports; for_use_case must clamp rather than raise on get_area.
    """
    if use_case not in USE_CASE_PRESETS[name]:
        return
    sel = PrecisionSelector(name)
    lo, hi = sel.area_calculator.min_precision, sel.area_calculator.max_precision
    rec = sel.for_use_case(use_case)
    assert lo <= rec.precision <= hi
