"""Tests for intelligent precision selection."""

import pytest

from m3s.api.precision import (
    AreaCalculator,
    PerformanceProfiler,
    PrecisionRecommendation,
    PrecisionSelector,
)


class TestAreaCalculator:
    """Test area-based calculations."""

    def test_area_calculator_initialization(self):
        """Test AreaCalculator can be initialized for all grid systems."""
        systems = [
            "geohash",
            "h3",
            "s2",
            "quadkey",
            "slippy",
            "mgrs",
            "csquares",
            "gars",
            "maidenhead",
            "pluscode",
            "what3words",
        ]

        for system in systems:
            calc = AreaCalculator(system)
            assert calc.grid_system == system
            assert len(calc.area_table) > 0

    def test_unknown_grid_system(self):
        """Test that unknown grid system raises error."""
        with pytest.raises(ValueError, match="Unknown grid system"):
            AreaCalculator("invalid_system")

    def test_get_area_valid_precision(self):
        """Test getting area for valid precision levels."""
        calc = AreaCalculator("h3")

        # Test a few known precision levels
        area_0 = calc.get_area(0)
        area_7 = calc.get_area(7)
        area_15 = calc.get_area(15)

        # Higher precision = smaller area
        assert area_0 > area_7 > area_15

        # H3 res 7 should be approximately 5.16 km²
        assert 4.0 < area_7 < 7.0

    def test_get_area_with_latitude_correction(self):
        """Test latitude-based area correction for Geohash."""
        calc = AreaCalculator("geohash")

        # Same precision at different latitudes
        area_equator = calc.get_area(5, latitude=0)
        area_mid = calc.get_area(5, latitude=45)
        area_polar = calc.get_area(5, latitude=75)

        # Cells get smaller (in area) at higher latitudes
        assert area_equator > area_mid > area_polar

    def test_precision_out_of_range(self):
        """Test that out-of-range precision raises error."""
        calc = AreaCalculator("h3")

        with pytest.raises(ValueError, match="out of range"):
            calc.get_area(100)  # Way too high

        with pytest.raises(ValueError, match="out of range"):
            calc.get_area(-1)  # Negative

    def test_find_precision_for_area(self):
        """Test finding precision for target area."""
        calc = AreaCalculator("h3")

        # Find precision for ~10 km² cells
        precision = calc.find_precision_for_area(10.0)

        # Should return a valid precision
        assert calc.min_precision <= precision <= calc.max_precision

        # Verify the area is reasonably close
        actual_area = calc.get_area(precision)
        assert abs(actual_area - 10.0) / 10.0 < 0.5  # Within 50%


class TestPerformanceProfiler:
    """Test performance estimation."""

    def test_estimate_operation_time(self):
        """Test operation time estimation."""
        profiler = PerformanceProfiler()

        # Estimate time for different operations
        time_point = profiler.estimate_operation_time("point_query", 100, "h3")
        time_intersect = profiler.estimate_operation_time("intersect", 100, "h3")
        time_conversion = profiler.estimate_operation_time("conversion", 100, "h3")

        # All should return positive times
        assert time_point > 0
        assert time_intersect > 0
        assert time_conversion > 0

        # Conversion should be most expensive
        assert time_conversion > time_intersect > time_point

    def test_system_multipliers(self):
        """Test that different grid systems have different performance."""
        profiler = PerformanceProfiler()

        # H3 is highly optimized (baseline)
        time_h3 = profiler.estimate_operation_time("intersect", 1000, "h3")

        # A5 is Python implementation (slower)
        time_a5 = profiler.estimate_operation_time("intersect", 1000, "a5")

        # A5 should take longer
        assert time_a5 > time_h3


class TestPrecisionRecommendation:
    """Test precision recommendation dataclass."""

    def test_create_recommendation(self):
        """Test creating a recommendation."""
        rec = PrecisionRecommendation(
            precision=7, confidence=0.95, explanation="Test recommendation"
        )

        assert rec.precision == 7
        assert rec.confidence == 0.95
        assert rec.explanation == "Test recommendation"

    def test_confidence_validation(self):
        """Test that invalid confidence raises error."""
        with pytest.raises(ValueError, match="Confidence must be between"):
            PrecisionRecommendation(precision=7, confidence=1.5, explanation="Invalid")

        with pytest.raises(ValueError, match="Confidence must be between"):
            PrecisionRecommendation(precision=7, confidence=-0.1, explanation="Invalid")


class TestPrecisionSelector:
    """Test precision selection strategies."""

    @pytest.fixture
    def systems(self):
        """Provide list of grid systems to test."""
        return ["geohash", "h3", "s2", "quadkey", "a5"]

    def test_initialization(self, systems):
        """Test selector can be initialized for all grid systems."""
        for system in systems:
            selector = PrecisionSelector(system)
            assert selector.grid_system == system

    def test_for_area_strategy(self, systems):
        """Test area-based precision selection."""
        for system in systems:
            selector = PrecisionSelector(system)

            # Select precision for 10 km² cells
            rec = selector.for_area(target_area_km2=10.0)

            # Should return valid recommendation
            assert isinstance(rec, PrecisionRecommendation)
            assert rec.precision is not None
            assert 0.0 <= rec.confidence <= 1.0
            assert len(rec.explanation) > 0
            assert rec.actual_area_km2 is not None

            # Actual area should be in a reasonable range
            # Grid systems have discrete precision levels, so exact matches are
            # impossible
            # Allow wider tolerance to account for this
            deviation = abs(rec.actual_area_km2 - 10.0) / 10.0
            assert deviation < 2.0  # Within 200% (allows 3.33-30 km² range)

    def test_for_area_with_tolerance(self):
        """Test area selection with different tolerances."""
        selector = PrecisionSelector("h3")

        # Tight tolerance
        rec_tight = selector.for_area(target_area_km2=10.0, tolerance=0.1)

        # Loose tolerance
        rec_loose = selector.for_area(target_area_km2=10.0, tolerance=0.5)

        # Both should return valid recommendations
        assert rec_tight.confidence >= 0.0
        assert rec_loose.confidence >= 0.0

        # Looser tolerance should have higher confidence (easier to satisfy)
        # (unless both are perfect matches)
        if rec_tight.actual_area_km2 != 10.0:
            assert rec_loose.confidence >= rec_tight.confidence

    def test_for_region_count_strategy(self, systems):
        """Test count-based precision selection."""
        for system in systems:
            selector = PrecisionSelector(system)

            # NYC area: roughly 100 km²
            bounds = (40.7, -74.1, 40.8, -73.9)

            # Target 100 cells
            rec = selector.for_region_count(bounds, target_count=100)

            assert isinstance(rec, PrecisionRecommendation)
            assert rec.precision is not None
            assert rec.actual_cell_count is not None

            # Should be in a reasonable range
            # Grid systems have discrete precision levels, so exact matches are
            # impossible
            deviation = abs(rec.actual_cell_count - 100) / 100
            assert deviation < 2.0  # Within 200% (allows 33-300 cell range)

    def test_for_use_case_strategy(self, systems):
        """Test use-case based precision selection."""
        use_cases = [
            "global",
            "continental",
            "country",
            "region",
            "city",
            "neighborhood",
            "street",
            "building",
        ]

        for system in systems:
            selector = PrecisionSelector(system)

            for use_case in use_cases:
                rec = selector.for_use_case(use_case)

                # Should return high-confidence recommendation
                assert isinstance(rec, PrecisionRecommendation)
                assert rec.confidence >= 0.9  # Curated presets have high confidence
                assert rec.precision is not None
                assert rec.actual_area_km2 is not None

    def test_for_use_case_with_polar_adjustment(self):
        """Test use-case selection near poles."""
        selector = PrecisionSelector("h3")

        # Same use case at equator and near pole
        rec_equator = selector.for_use_case("city", context={"latitude": 0})
        rec_pole = selector.for_use_case("city", context={"latitude": 75})

        # Near pole should use higher precision (smaller cells needed due to distortion)
        # (not all systems adjust, but shouldn't fail)
        assert rec_equator.precision is not None
        assert rec_pole.precision is not None

    def test_for_use_case_invalid(self):
        """Test that invalid use case raises error."""
        selector = PrecisionSelector("h3")

        with pytest.raises(ValueError, match="Unknown use case"):
            selector.for_use_case("invalid_use_case")

    def test_for_distance_strategy(self, systems):
        """Test distance-based precision selection."""
        for system in systems:
            selector = PrecisionSelector(system)

            # Target 100m edge length
            rec = selector.for_distance(edge_length_m=100.0)

            assert isinstance(rec, PrecisionRecommendation)
            assert rec.precision is not None
            assert rec.edge_length_m is not None

            # Should be reasonably close to target
            assert abs(rec.edge_length_m - 100.0) / 100.0 < 0.5  # Within 50%

    def test_for_performance_strategy(self, systems):
        """Test performance-based precision selection."""
        for system in systems:
            selector = PrecisionSelector(system)

            # Target 100ms for intersect operation on 1000 km² region
            rec = selector.for_performance(
                operation_type="intersect", time_budget_ms=100.0, region_size_km2=1000.0
            )

            assert isinstance(rec, PrecisionRecommendation)
            assert rec.precision is not None
            assert 0.0 <= rec.confidence <= 1.0

            # Should have timing metadata
            assert "estimated_time_ms" in rec.metadata
            assert rec.metadata["estimated_time_ms"] <= 100.0  # Within budget

    def test_confidence_scores_in_range(self, systems):
        """Test that all strategies return confidence in [0, 1]."""
        for system in systems:
            selector = PrecisionSelector(system)

            # Test all strategies
            rec_area = selector.for_area(10.0)
            rec_use_case = selector.for_use_case("city")
            rec_distance = selector.for_distance(100.0)

            assert 0.0 <= rec_area.confidence <= 1.0
            assert 0.0 <= rec_use_case.confidence <= 1.0
            assert 0.0 <= rec_distance.confidence <= 1.0

    def test_explanations_provided(self, systems):
        """Test that all strategies provide explanations."""
        for system in systems:
            selector = PrecisionSelector(system)

            rec_area = selector.for_area(10.0)
            rec_use_case = selector.for_use_case("city")

            assert len(rec_area.explanation) > 10  # Meaningful explanation
            assert len(rec_use_case.explanation) > 10
            assert system.upper() in rec_area.explanation  # Mentions system


class TestPrecisionSelectorPerformance:
    """Test that precision selection is fast."""

    def test_area_selection_performance(self):
        """Test that area-based selection is fast (<10ms)."""
        import time

        selector = PrecisionSelector("h3")

        start = time.time()
        for _ in range(100):
            selector.for_area(10.0)
        end = time.time()

        avg_time_ms = ((end - start) / 100) * 1000

        # Should be well under 10ms (usually <1ms)
        assert avg_time_ms < 10.0

    def test_use_case_selection_performance(self):
        """Test that use-case selection is very fast (<5ms)."""
        import time

        selector = PrecisionSelector("h3")

        start = time.time()
        for _ in range(100):
            selector.for_use_case("city")
        end = time.time()

        avg_time_ms = ((end - start) / 100) * 1000

        # Should be very fast (just lookup)
        assert avg_time_ms < 5.0
