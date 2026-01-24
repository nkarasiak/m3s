"""
A5 Compatibility Tests with Palmer's Library.

These tests validate that our A5 implementation matches Felix Palmer's
reference implementation (palmer_a5) for cell IDs and boundaries.

CRITICAL: Cell IDs must match exactly for our implementation to be correct.
"""

import math
import pytest

# Try to import Palmer's library
try:
    import a5 as palmer_a5

    PALMER_AVAILABLE = True
except ImportError:
    PALMER_AVAILABLE = False
    palmer_a5 = None

from m3s.a5.cell import cell_to_boundary, cell_to_lonlat, lonlat_to_cell
from m3s.a5.coordinates import CoordinateTransformer

RESOLUTIONS_7_PLUS = list(range(7, 30))


@pytest.mark.skipif(not PALMER_AVAILABLE, reason="Palmer's a5 library not installed")
class TestCellIDCompatibility:
    """Test that our cell IDs match Palmer's exactly."""

    def test_cell_id_resolution_0_nyc(self):
        """Test cell ID match for NYC at resolution 0."""
        lon, lat = -74.0060, 40.7128

        our_cell_id = lonlat_to_cell(lon, lat, 0)
        palmer_cell_id = palmer_a5.lonlat_to_cell(((lon, lat)), 0)

        assert our_cell_id == palmer_cell_id, (
            f"Cell ID mismatch at NYC res 0: "
            f"ours={our_cell_id:016x}, Palmer's={palmer_cell_id:016x}"
        )

    def test_cell_id_resolution_0_london(self):
        """Test cell ID match for London at resolution 0."""
        lon, lat = -0.1278, 51.5074

        our_cell_id = lonlat_to_cell(lon, lat, 0)
        palmer_cell_id = palmer_a5.lonlat_to_cell((lon, lat), 0)

        assert our_cell_id == palmer_cell_id, (
            f"Cell ID mismatch at London res 0: "
            f"ours={our_cell_id:016x}, Palmer's={palmer_cell_id:016x}"
        )

    def test_cell_id_resolution_0_equator(self):
        """Test cell ID match for equator at resolution 0."""
        lon, lat = 0.0, 0.0

        our_cell_id = lonlat_to_cell(lon, lat, 0)
        palmer_cell_id = palmer_a5.lonlat_to_cell((lon, lat), 0)

        assert our_cell_id == palmer_cell_id, (
            f"Cell ID mismatch at equator res 0: "
            f"ours={our_cell_id:016x}, Palmer's={palmer_cell_id:016x}"
        )

    def test_cell_id_resolution_0_north_pole(self):
        """Test cell ID match near north pole at resolution 0."""
        lon, lat = 0.0, 89.0

        our_cell_id = lonlat_to_cell(lon, lat, 0)
        palmer_cell_id = palmer_a5.lonlat_to_cell((lon, lat), 0)

        assert our_cell_id == palmer_cell_id, (
            f"Cell ID mismatch near north pole res 0: "
            f"ours={our_cell_id:016x}, Palmer's={palmer_cell_id:016x}"
        )

    def test_cell_id_resolution_0_south_pole(self):
        """Test cell ID match near south pole at resolution 0."""
        lon, lat = 0.0, -89.0

        our_cell_id = lonlat_to_cell(lon, lat, 0)
        palmer_cell_id = palmer_a5.lonlat_to_cell((lon, lat), 0)

        assert our_cell_id == palmer_cell_id, (
            f"Cell ID mismatch near south pole res 0: "
            f"ours={our_cell_id:016x}, Palmer's={palmer_cell_id:016x}"
        )

    def test_cell_id_resolution_1_nyc(self):
        """Test cell ID match for NYC at resolution 1."""
        lon, lat = -74.0060, 40.7128

        our_cell_id = lonlat_to_cell(lon, lat, 1)
        palmer_cell_id = palmer_a5.lonlat_to_cell((lon, lat), 1)

        assert our_cell_id == palmer_cell_id, (
            f"Cell ID mismatch at NYC res 1: "
            f"ours={our_cell_id:016x}, Palmer's={palmer_cell_id:016x}"
        )

    def test_cell_id_resolution_1_london(self):
        """Test cell ID match for London at resolution 1."""
        lon, lat = -0.1278, 51.5074

        our_cell_id = lonlat_to_cell(lon, lat, 1)
        palmer_cell_id = palmer_a5.lonlat_to_cell((lon, lat), 1)

        assert our_cell_id == palmer_cell_id, (
            f"Cell ID mismatch at London res 1: "
            f"ours={our_cell_id:016x}, Palmer's={palmer_cell_id:016x}"
        )

    def test_cell_id_resolution_1_global_coverage(self):
        """Test cell ID match across global locations at resolution 1."""
        test_coords = [
            (0.0, 0.0),  # Equator/Prime Meridian
            (90.0, 45.0),  # Mid-latitude
            (-90.0, -45.0),  # Southern hemisphere
            (179.0, 85.0),  # Near north pole, dateline
            (-179.0, -85.0),  # Near south pole, dateline
            (139.6503, 35.6762),  # Tokyo
            (-58.3816, -34.6037),  # Buenos Aires
            (151.2093, -33.8688),  # Sydney
        ]

        for lon, lat in test_coords:
            our_cell_id = lonlat_to_cell(lon, lat, 1)
            palmer_cell_id = palmer_a5.lonlat_to_cell((lon, lat), 1)

            assert our_cell_id == palmer_cell_id, (
                f"Cell ID mismatch at ({lat}, {lon}) res 1: "
                f"ours={our_cell_id:016x}, Palmer's={palmer_cell_id:016x}"
            )

    @pytest.mark.parametrize("resolution", [2, 3])
    def test_cell_id_resolution_2_3_sample_points(self, resolution):
        """Test cell ID match for a few points at resolution 2+."""
        test_coords = [
            (-74.0060, 40.7128),  # NYC
            (-0.1278, 51.5074),  # London
            (0.0, 0.0),  # Equator
            (179.0, 85.0),  # Near north pole, dateline
            (-179.0, -85.0),  # Near south pole, dateline
            (139.6503, 35.6762),  # Tokyo
            (-58.3816, -34.6037),  # Buenos Aires
            (151.2093, -33.8688),  # Sydney
        ]

        for lon, lat in test_coords:
            our_cell_id = lonlat_to_cell(lon, lat, resolution)
            palmer_cell_id = palmer_a5.lonlat_to_cell((lon, lat), resolution)

            assert our_cell_id == palmer_cell_id, (
                f"Cell ID mismatch at ({lat}, {lon}) res {resolution}: "
                f"ours={our_cell_id:016x}, Palmer's={palmer_cell_id:016x}"
            )

    def test_cell_id_resolution_4_sample_points(self):
        """Test cell ID match for a few points at resolution 4."""
        test_coords = [
            (-74.0060, 40.7128),  # NYC
            (-0.1278, 51.5074),  # London
            (0.0, 0.0),  # Equator
            (179.0, 85.0),  # Near north pole, dateline
            (-179.0, -85.0),  # Near south pole, dateline
            (139.6503, 35.6762),  # Tokyo
            (-58.3816, -34.6037),  # Buenos Aires
            (151.2093, -33.8688),  # Sydney
        ]

        for lon, lat in test_coords:
            our_cell_id = lonlat_to_cell(lon, lat, 4)
            palmer_cell_id = palmer_a5.lonlat_to_cell((lon, lat), 4)

            assert our_cell_id == palmer_cell_id, (
                f"Cell ID mismatch at ({lat}, {lon}) res 4: "
                f"ours={our_cell_id:016x}, Palmer's={palmer_cell_id:016x}"
            )

    def test_cell_id_resolution_5_sample_points(self):
        """Test cell ID match for a few points at resolution 5."""
        test_coords = [
            (-74.0060, 40.7128),  # NYC
            (-0.1278, 51.5074),  # London
            (0.0, 0.0),  # Equator
            (179.0, 85.0),  # Near north pole, dateline
            (-179.0, -85.0),  # Near south pole, dateline
            (139.6503, 35.6762),  # Tokyo
            (-58.3816, -34.6037),  # Buenos Aires
            (151.2093, -33.8688),  # Sydney
        ]

        for lon, lat in test_coords:
            our_cell_id = lonlat_to_cell(lon, lat, 5)
            palmer_cell_id = palmer_a5.lonlat_to_cell((lon, lat), 5)

            assert our_cell_id == palmer_cell_id, (
                f"Cell ID mismatch at ({lat}, {lon}) res 5: "
                f"ours={our_cell_id:016x}, Palmer's={palmer_cell_id:016x}"
            )

    def test_cell_id_resolution_6_sample_points(self):
        """Test cell ID match for a few points at resolution 6."""
        test_coords = [
            (-74.0060, 40.7128),  # NYC
            (-0.1278, 51.5074),  # London
            (0.0, 0.0),  # Equator
            (179.0, 85.0),  # Near north pole, dateline
            (-179.0, -85.0),  # Near south pole, dateline
            (139.6503, 35.6762),  # Tokyo
            (-58.3816, -34.6037),  # Buenos Aires
            (151.2093, -33.8688),  # Sydney
        ]

        for lon, lat in test_coords:
            our_cell_id = lonlat_to_cell(lon, lat, 6)
            palmer_cell_id = palmer_a5.lonlat_to_cell((lon, lat), 6)

            assert our_cell_id == palmer_cell_id, (
                f"Cell ID mismatch at ({lat}, {lon}) res 6: "
                f"ours={our_cell_id:016x}, Palmer's={palmer_cell_id:016x}"
            )

    @pytest.mark.parametrize("resolution", RESOLUTIONS_7_PLUS)
    def test_cell_id_resolution_7_plus_sample_points(self, resolution):
        """Test cell ID match for a few points at resolution 7+."""
        test_coords = [
            (-74.0060, 40.7128),  # NYC
            (-0.1278, 51.5074),  # London
            (0.0, 0.0),  # Equator
            (179.0, 85.0),  # Near north pole, dateline
            (-179.0, -85.0),  # Near south pole, dateline
            (139.6503, 35.6762),  # Tokyo
            (-58.3816, -34.6037),  # Buenos Aires
            (151.2093, -33.8688),  # Sydney
        ]

        for lon, lat in test_coords:
            our_cell_id = lonlat_to_cell(lon, lat, resolution)
            palmer_cell_id = palmer_a5.lonlat_to_cell((lon, lat), resolution)

            assert our_cell_id == palmer_cell_id, (
                f"Cell ID mismatch at ({lat}, {lon}) res {resolution}: "
                f"ours={our_cell_id:016x}, Palmer's={palmer_cell_id:016x}"
            )

    def test_cell_id_resolution_2_global_grid(self):
        """Test resolution 2 cell IDs across a coarse global grid."""
        mismatches = []

        for lat in range(-80, 81, 20):
            for lon in range(-180, 180, 20):
                our_cell = lonlat_to_cell(lon, lat, 2)
                palmer_cell = palmer_a5.lonlat_to_cell((lon, lat), 2)

                if our_cell != palmer_cell:
                    mismatches.append((lon, lat, our_cell, palmer_cell))

        if mismatches:
            mismatch_report = "\n".join(
                f"  ({lon}, {lat}): ours={our:016x}, Palmer's={palmer:016x}"
                for lon, lat, our, palmer in mismatches[:10]
            )
            pytest.fail(
                f"Found {len(mismatches)} cell ID mismatches at resolution 2:\n"
                f"{mismatch_report}"
            )

    def test_cell_id_resolution_2_dense_grid(self):
        """Test resolution 2 IDs across a denser global grid."""
        mismatches = []

        for lat in range(-80, 81, 10):
            for lon in range(-180, 180, 10):
                our_cell = lonlat_to_cell(lon, lat, 2)
                palmer_cell = palmer_a5.lonlat_to_cell((lon, lat), 2)

                if our_cell != palmer_cell:
                    mismatches.append((lon, lat, our_cell, palmer_cell))

        if mismatches:
            mismatch_report = "\n".join(
                f"  ({lon}, {lat}): ours={our:016x}, Palmer's={palmer:016x}"
                for lon, lat, our, palmer in mismatches[:10]
            )
            pytest.fail(
                f"Found {len(mismatches)} cell ID mismatches at resolution 2 (dense grid):\n"
                f"{mismatch_report}"
            )

    def test_cell_id_resolution_3_global_grid(self):
        """Test resolution 3 cell IDs across a coarse global grid."""
        mismatches = []

        for lat in range(-80, 81, 20):
            for lon in range(-180, 180, 20):
                our_cell = lonlat_to_cell(lon, lat, 3)
                palmer_cell = palmer_a5.lonlat_to_cell((lon, lat), 3)

                if our_cell != palmer_cell:
                    mismatches.append((lon, lat, our_cell, palmer_cell))

        if mismatches:
            mismatch_report = "\n".join(
                f"  ({lon}, {lat}): ours={our:016x}, Palmer's={palmer:016x}"
                for lon, lat, our, palmer in mismatches[:10]
            )
            pytest.fail(
                f"Found {len(mismatches)} cell ID mismatches at resolution 3:\n"
                f"{mismatch_report}"
            )

    def test_cell_id_resolution_3_dense_grid(self):
        """Test resolution 3 IDs across a denser global grid."""
        mismatches = []

        for lat in range(-75, 76, 15):
            for lon in range(-180, 180, 15):
                our_cell = lonlat_to_cell(lon, lat, 3)
                palmer_cell = palmer_a5.lonlat_to_cell((lon, lat), 3)

                if our_cell != palmer_cell:
                    mismatches.append((lon, lat, our_cell, palmer_cell))

        if mismatches:
            mismatch_report = "\n".join(
                f"  ({lon}, {lat}): ours={our:016x}, Palmer's={palmer:016x}"
                for lon, lat, our, palmer in mismatches[:10]
            )
            pytest.fail(
                f"Found {len(mismatches)} cell ID mismatches at resolution 3 (dense grid):\n"
                f"{mismatch_report}"
            )

    def test_cell_id_resolution_4_global_grid(self):
        """Test resolution 4 cell IDs across a coarse global grid."""
        mismatches = []

        for lat in range(-80, 81, 20):
            for lon in range(-180, 180, 20):
                our_cell = lonlat_to_cell(lon, lat, 4)
                palmer_cell = palmer_a5.lonlat_to_cell((lon, lat), 4)

                if our_cell != palmer_cell:
                    mismatches.append((lon, lat, our_cell, palmer_cell))

        if mismatches:
            mismatch_report = "\n".join(
                f"  ({lon}, {lat}): ours={our:016x}, Palmer's={palmer:016x}"
                for lon, lat, our, palmer in mismatches[:10]
            )
            pytest.fail(
                f"Found {len(mismatches)} cell ID mismatches at resolution 4:\n"
                f"{mismatch_report}"
            )

    def test_cell_id_resolution_4_dense_grid(self):
        """Test resolution 4 IDs across a denser global grid."""
        mismatches = []

        for lat in range(-75, 76, 15):
            for lon in range(-180, 180, 15):
                our_cell = lonlat_to_cell(lon, lat, 4)
                palmer_cell = palmer_a5.lonlat_to_cell((lon, lat), 4)

                if our_cell != palmer_cell:
                    mismatches.append((lon, lat, our_cell, palmer_cell))

        if mismatches:
            mismatch_report = "\n".join(
                f"  ({lon}, {lat}): ours={our:016x}, Palmer's={palmer:016x}"
                for lon, lat, our, palmer in mismatches[:10]
            )
            pytest.fail(
                f"Found {len(mismatches)} cell ID mismatches at resolution 4 (dense grid):\n"
                f"{mismatch_report}"
            )

    def test_cell_id_resolution_5_global_grid(self):
        """Test resolution 5 cell IDs across a coarse global grid."""
        mismatches = []

        for lat in range(-80, 81, 20):
            for lon in range(-180, 180, 20):
                our_cell = lonlat_to_cell(lon, lat, 5)
                palmer_cell = palmer_a5.lonlat_to_cell((lon, lat), 5)

                if our_cell != palmer_cell:
                    mismatches.append((lon, lat, our_cell, palmer_cell))

        if mismatches:
            mismatch_report = "\n".join(
                f"  ({lon}, {lat}): ours={our:016x}, Palmer's={palmer:016x}"
                for lon, lat, our, palmer in mismatches[:10]
            )
            pytest.fail(
                f"Found {len(mismatches)} cell ID mismatches at resolution 5:\n"
                f"{mismatch_report}"
            )

    def test_cell_id_resolution_5_dense_grid(self):
        """Test resolution 5 IDs across a denser global grid."""
        mismatches = []

        for lat in range(-75, 76, 15):
            for lon in range(-180, 180, 15):
                our_cell = lonlat_to_cell(lon, lat, 5)
                palmer_cell = palmer_a5.lonlat_to_cell((lon, lat), 5)

                if our_cell != palmer_cell:
                    mismatches.append((lon, lat, our_cell, palmer_cell))

        if mismatches:
            mismatch_report = "\n".join(
                f"  ({lon}, {lat}): ours={our:016x}, Palmer's={palmer:016x}"
                for lon, lat, our, palmer in mismatches[:10]
            )
            pytest.fail(
                f"Found {len(mismatches)} cell ID mismatches at resolution 5 (dense grid):\n"
                f"{mismatch_report}"
            )

    def test_cell_id_resolution_6_global_grid(self):
        """Test resolution 6 cell IDs across a coarse global grid."""
        mismatches = []

        for lat in range(-80, 81, 20):
            for lon in range(-180, 180, 20):
                our_cell = lonlat_to_cell(lon, lat, 6)
                palmer_cell = palmer_a5.lonlat_to_cell((lon, lat), 6)

                if our_cell != palmer_cell:
                    mismatches.append((lon, lat, our_cell, palmer_cell))

        if mismatches:
            mismatch_report = "\n".join(
                f"  ({lon}, {lat}): ours={our:016x}, Palmer's={palmer:016x}"
                for lon, lat, our, palmer in mismatches[:10]
            )
            pytest.fail(
                f"Found {len(mismatches)} cell ID mismatches at resolution 6:\n"
                f"{mismatch_report}"
            )

    def test_cell_id_resolution_6_dense_grid(self):
        """Test resolution 6 IDs across a denser global grid."""
        mismatches = []

        for lat in range(-75, 76, 15):
            for lon in range(-180, 180, 15):
                our_cell = lonlat_to_cell(lon, lat, 6)
                palmer_cell = palmer_a5.lonlat_to_cell((lon, lat), 6)

                if our_cell != palmer_cell:
                    mismatches.append((lon, lat, our_cell, palmer_cell))

        if mismatches:
            mismatch_report = "\n".join(
                f"  ({lon}, {lat}): ours={our:016x}, Palmer's={palmer:016x}"
                for lon, lat, our, palmer in mismatches[:10]
            )
            pytest.fail(
                f"Found {len(mismatches)} cell ID mismatches at resolution 6 (dense grid):\n"
                f"{mismatch_report}"
            )

    @pytest.mark.parametrize("resolution", RESOLUTIONS_7_PLUS)
    def test_cell_id_resolution_7_plus_global_grid(self, resolution):
        """Test resolution 7+ cell IDs across a coarse global grid."""
        mismatches = []

        for lat in range(-80, 81, 20):
            for lon in range(-180, 180, 20):
                our_cell = lonlat_to_cell(lon, lat, resolution)
                palmer_cell = palmer_a5.lonlat_to_cell((lon, lat), resolution)

                if our_cell != palmer_cell:
                    mismatches.append((lon, lat, our_cell, palmer_cell))

        if mismatches:
            mismatch_report = "\n".join(
                f"  ({lon}, {lat}): ours={our:016x}, Palmer's={palmer:016x}"
                for lon, lat, our, palmer in mismatches[:10]
            )
            pytest.fail(
                f"Found {len(mismatches)} cell ID mismatches at resolution {resolution}:\n"
                f"{mismatch_report}"
            )

    @pytest.mark.parametrize("resolution", RESOLUTIONS_7_PLUS)
    def test_cell_id_resolution_7_plus_dense_grid(self, resolution):
        """Test resolution 7+ IDs across a denser global grid."""
        mismatches = []

        for lat in range(-75, 76, 15):
            for lon in range(-180, 180, 15):
                our_cell = lonlat_to_cell(lon, lat, resolution)
                palmer_cell = palmer_a5.lonlat_to_cell((lon, lat), resolution)

                if our_cell != palmer_cell:
                    mismatches.append((lon, lat, our_cell, palmer_cell))

        if mismatches:
            mismatch_report = "\n".join(
                f"  ({lon}, {lat}): ours={our:016x}, Palmer's={palmer:016x}"
                for lon, lat, our, palmer in mismatches[:10]
            )
            pytest.fail(
                f"Found {len(mismatches)} cell ID mismatches at resolution {resolution} (dense grid):\n"
                f"{mismatch_report}"
            )

    def test_cell_id_resolution_2_edge_cases(self):
        """Test resolution 2 IDs for edge-case points."""
        eps = 1e-6
        test_coords = [
            (179.999, 0.0),
            (-179.999, 0.0),
            (0.0, 89.999),
            (0.0, -89.999),
            (-93.0, 0.0),
            (-93.0 + eps, 0.0),
            (-93.0 - eps, 0.0),
            (93.0, 0.0),
            (93.0 + eps, 0.0),
            (93.0 - eps, 0.0),
        ]

        for lon, lat in test_coords:
            our_cell = lonlat_to_cell(lon, lat, 2)
            palmer_cell = palmer_a5.lonlat_to_cell((lon, lat), 2)
            assert our_cell == palmer_cell, (
                f"Cell ID mismatch at ({lat}, {lon}) res 2: "
                f"ours={our_cell:016x}, Palmer's={palmer_cell:016x}"
            )

    def test_cell_id_resolution_3_edge_cases(self):
        """Test resolution 3 IDs for edge-case points."""
        eps = 1e-6
        test_coords = [
            (179.999, 0.0),
            (-179.999, 0.0),
            (0.0, 89.999),
            (0.0, -89.999),
            (-93.0, 0.0),
            (-93.0 + eps, 0.0),
            (-93.0 - eps, 0.0),
            (93.0, 0.0),
            (93.0 + eps, 0.0),
            (93.0 - eps, 0.0),
        ]

        for lon, lat in test_coords:
            our_cell = lonlat_to_cell(lon, lat, 3)
            palmer_cell = palmer_a5.lonlat_to_cell((lon, lat), 3)
            assert our_cell == palmer_cell, (
                f"Cell ID mismatch at ({lat}, {lon}) res 3: "
                f"ours={our_cell:016x}, Palmer's={palmer_cell:016x}"
            )

    def test_cell_id_resolution_4_edge_cases(self):
        """Test resolution 4 IDs for edge-case points."""
        eps = 1e-6
        test_coords = [
            (179.999, 0.0),
            (-179.999, 0.0),
            (0.0, 89.999),
            (0.0, -89.999),
            (-93.0, 0.0),
            (-93.0 + eps, 0.0),
            (-93.0 - eps, 0.0),
            (93.0, 0.0),
            (93.0 + eps, 0.0),
            (93.0 - eps, 0.0),
        ]

        for lon, lat in test_coords:
            our_cell = lonlat_to_cell(lon, lat, 4)
            palmer_cell = palmer_a5.lonlat_to_cell((lon, lat), 4)
            assert our_cell == palmer_cell, (
                f"Cell ID mismatch at ({lat}, {lon}) res 4: "
                f"ours={our_cell:016x}, Palmer's={palmer_cell:016x}"
            )

    def test_cell_id_resolution_5_edge_cases(self):
        """Test resolution 5 IDs for edge-case points."""
        eps = 1e-6
        test_coords = [
            (179.999, 0.0),
            (-179.999, 0.0),
            (0.0, 89.999),
            (0.0, -89.999),
            (-93.0, 0.0),
            (-93.0 + eps, 0.0),
            (-93.0 - eps, 0.0),
            (93.0, 0.0),
            (93.0 + eps, 0.0),
            (93.0 - eps, 0.0),
        ]

        for lon, lat in test_coords:
            our_cell = lonlat_to_cell(lon, lat, 5)
            palmer_cell = palmer_a5.lonlat_to_cell((lon, lat), 5)
            assert our_cell == palmer_cell, (
                f"Cell ID mismatch at ({lat}, {lon}) res 5: "
                f"ours={our_cell:016x}, Palmer's={palmer_cell:016x}"
            )

    def test_cell_id_resolution_6_edge_cases(self):
        """Test resolution 6 IDs for edge-case points."""
        eps = 1e-6
        test_coords = [
            (179.999, 0.0),
            (-179.999, 0.0),
            (0.0, 89.999),
            (0.0, -89.999),
            (-93.0, 0.0),
            (-93.0 + eps, 0.0),
            (-93.0 - eps, 0.0),
            (93.0, 0.0),
            (93.0 + eps, 0.0),
            (93.0 - eps, 0.0),
        ]

        for lon, lat in test_coords:
            our_cell = lonlat_to_cell(lon, lat, 6)
            palmer_cell = palmer_a5.lonlat_to_cell((lon, lat), 6)
            assert our_cell == palmer_cell, (
                f"Cell ID mismatch at ({lat}, {lon}) res 6: "
                f"ours={our_cell:016x}, Palmer's={palmer_cell:016x}"
            )

    def test_cell_id_resolution_30_unsupported(self):
        """Resolution 30 is not encodable in 64-bit A5 IDs."""
        test_coords = [
            (-74.0060, 40.7128),  # NYC
            (0.0, 0.0),  # Equator
            (139.6503, 35.6762),  # Tokyo
        ]

        for lon, lat in test_coords:
            with pytest.raises(ValueError):
                lonlat_to_cell(lon, lat, 30)

    @pytest.mark.parametrize("resolution", RESOLUTIONS_7_PLUS)
    def test_cell_id_resolution_7_plus_edge_cases(self, resolution):
        """Test resolution 7+ IDs for edge-case points."""
        eps = 1e-6
        test_coords = [
            (179.999, 0.0),
            (-179.999, 0.0),
            (0.0, 89.999),
            (0.0, -89.999),
            (-93.0, 0.0),
            (-93.0 + eps, 0.0),
            (-93.0 - eps, 0.0),
            (93.0, 0.0),
            (93.0 + eps, 0.0),
            (93.0 - eps, 0.0),
        ]

        for lon, lat in test_coords:
            our_cell = lonlat_to_cell(lon, lat, resolution)
            palmer_cell = palmer_a5.lonlat_to_cell((lon, lat), resolution)
            assert our_cell == palmer_cell, (
                f"Cell ID mismatch at ({lat}, {lon}) res {resolution}: "
                f"ours={our_cell:016x}, Palmer's={palmer_cell:016x}"
            )
    @pytest.mark.parametrize("resolution", [2, 3])
    def test_cell_id_resolution_2_3_quintant_boundaries(self, resolution):
        """Test IDs for points near quintant boundaries."""
        from a5.projections.dodecahedron import DodecahedronProjection as PalmerDodec
        from a5.core import coordinate_transforms as palmer_ct

        proj = PalmerDodec()
        eps = 1e-6
        radius = 0.2
        origin_ids = [0, 1, 5, 9]

        test_points = []
        for origin_id in origin_ids:
            for k in range(5):
                angle = k * (2 * 3.141592653589793 / 5)
                for delta in (-eps, eps):
                    x = radius * math.cos(angle + delta)
                    y = radius * math.sin(angle + delta)
                    spherical = proj.inverse((x, y), origin_id)
                    lon, lat = palmer_ct.to_lonlat(spherical)
                    lon = CoordinateTransformer.wrap_longitude(lon)
                    test_points.append((lon, lat))

        for lon, lat in test_points:
            our_cell = lonlat_to_cell(lon, lat, resolution)
            palmer_cell = palmer_a5.lonlat_to_cell((lon, lat), resolution)
            assert our_cell == palmer_cell, (
                f"Cell ID mismatch near quintant boundary at ({lat}, {lon}) res {resolution}: "
                f"ours={our_cell:016x}, Palmer's={palmer_cell:016x}"
            )

    @pytest.mark.parametrize("resolution", RESOLUTIONS_7_PLUS)
    def test_cell_id_resolution_7_plus_quintant_boundaries(self, resolution):
        """Test IDs for points near quintant boundaries at resolution 7+."""
        from a5.projections.dodecahedron import DodecahedronProjection as PalmerDodec
        from a5.core import coordinate_transforms as palmer_ct

        proj = PalmerDodec()
        eps = 1e-6
        radius = 0.2
        origin_ids = [0, 1, 5, 9]

        test_points = []
        for origin_id in origin_ids:
            for k in range(5):
                angle = k * (2 * 3.141592653589793 / 5)
                for delta in (-eps, eps):
                    x = radius * math.cos(angle + delta)
                    y = radius * math.sin(angle + delta)
                    spherical = proj.inverse((x, y), origin_id)
                    lon, lat = palmer_ct.to_lonlat(spherical)
                    lon = CoordinateTransformer.wrap_longitude(lon)
                    test_points.append((lon, lat))

        for lon, lat in test_points:
            our_cell = lonlat_to_cell(lon, lat, resolution)
            palmer_cell = palmer_a5.lonlat_to_cell((lon, lat), resolution)
            assert our_cell == palmer_cell, (
                f"Cell ID mismatch near quintant boundary at ({lat}, {lon}) res {resolution}: "
                f"ours={our_cell:016x}, Palmer's={palmer_cell:016x}"
            )

@pytest.mark.skipif(not PALMER_AVAILABLE, reason="Palmer's a5 library not installed")
class TestBoundaryCompatibility:
    """Test that boundaries are similar to Palmer's (within tolerance)."""

    def test_boundary_resolution_0_nyc(self):
        """Test boundary similarity for NYC at resolution 0."""
        lon, lat = -74.0060, 40.7128
        cell_id = lonlat_to_cell(lon, lat, 0)

        our_boundary = cell_to_boundary(cell_id)
        palmer_boundary = palmer_a5.cell_to_boundary(cell_id)

        # Should have same number of vertices
        assert len(our_boundary) == len(palmer_boundary), (
            f"Boundary vertex count mismatch: "
            f"ours={len(our_boundary)}, Palmer's={len(palmer_boundary)}"
        )

        # Vertices should be very close (within ~1 meter = 0.00001 degrees)
        for i, ((our_lon, our_lat), (p_lon, p_lat)) in enumerate(
            zip(our_boundary, palmer_boundary)
        ):
            lon_diff = abs(our_lon - p_lon)
            lat_diff = abs(our_lat - p_lat)

            # Handle antimeridian wrap
            if lon_diff > 180:
                lon_diff = 360 - lon_diff

            assert lon_diff < 0.1, (
                f"Boundary vertex {i} lon mismatch: "
                f"ours={our_lon}, Palmer's={p_lon}, diff={lon_diff}"
            )
            assert lat_diff < 0.1, (
                f"Boundary vertex {i} lat mismatch: "
                f"ours={our_lat}, Palmer's={p_lat}, diff={lat_diff}"
            )

    def test_boundary_resolution_1_london(self):
        """Test boundary similarity for London at resolution 1."""
        lon, lat = -0.1278, 51.5074
        cell_id = lonlat_to_cell(lon, lat, 1)

        our_boundary = cell_to_boundary(cell_id)
        palmer_boundary = palmer_a5.cell_to_boundary(cell_id)

        # Should have same number of vertices
        assert len(our_boundary) == len(palmer_boundary)

        # Vertices should be close
        for (our_lon, our_lat), (p_lon, p_lat) in zip(our_boundary, palmer_boundary):
            lon_diff = abs(our_lon - p_lon)
            lat_diff = abs(our_lat - p_lat)

            if lon_diff > 180:
                lon_diff = 360 - lon_diff

            assert lon_diff < 0.1
            assert lat_diff < 0.1

    def test_boundary_resolution_2_tokyo(self):
        """Test boundary similarity for Tokyo at resolution 2."""
        lon, lat = 139.6503, 35.6762
        cell_id = lonlat_to_cell(lon, lat, 2)

        our_boundary = cell_to_boundary(cell_id)
        palmer_boundary = palmer_a5.cell_to_boundary(cell_id)

        assert len(our_boundary) == len(palmer_boundary)

        for (our_lon, our_lat), (p_lon, p_lat) in zip(our_boundary, palmer_boundary):
            lon_diff = abs(our_lon - p_lon)
            lat_diff = abs(our_lat - p_lat)

            if lon_diff > 180:
                lon_diff = 360 - lon_diff

            assert lon_diff < 0.1
            assert lat_diff < 0.1

    def test_boundary_resolution_2_antimeridian(self):
        """Test boundary similarity near the antimeridian at resolution 2."""
        lon, lat = 179.999, 10.0
        cell_id = lonlat_to_cell(lon, lat, 2)

        our_boundary = cell_to_boundary(cell_id)
        palmer_boundary = palmer_a5.cell_to_boundary(cell_id)

        assert len(our_boundary) == len(palmer_boundary)

        for (our_lon, our_lat), (p_lon, p_lat) in zip(our_boundary, palmer_boundary):
            lon_diff = abs(our_lon - p_lon)
            lat_diff = abs(our_lat - p_lat)

            if lon_diff > 180:
                lon_diff = 360 - lon_diff

            assert lon_diff < 0.1
            assert lat_diff < 0.1

    def test_boundary_resolution_3_tokyo(self):
        """Test boundary similarity for Tokyo at resolution 3."""
        lon, lat = 139.6503, 35.6762
        cell_id = lonlat_to_cell(lon, lat, 3)

        our_boundary = cell_to_boundary(cell_id)
        palmer_boundary = palmer_a5.cell_to_boundary(cell_id)

        assert len(our_boundary) == len(palmer_boundary)

        for (our_lon, our_lat), (p_lon, p_lat) in zip(our_boundary, palmer_boundary):
            lon_diff = abs(our_lon - p_lon)
            lat_diff = abs(our_lat - p_lat)

            if lon_diff > 180:
                lon_diff = 360 - lon_diff

            assert lon_diff < 0.1
            assert lat_diff < 0.1

    def test_boundary_resolution_4_tokyo(self):
        """Test boundary similarity for Tokyo at resolution 4."""
        lon, lat = 139.6503, 35.6762
        cell_id = lonlat_to_cell(lon, lat, 4)

        our_boundary = cell_to_boundary(cell_id)
        palmer_boundary = palmer_a5.cell_to_boundary(cell_id)

        assert len(our_boundary) == len(palmer_boundary)

        for (our_lon, our_lat), (p_lon, p_lat) in zip(our_boundary, palmer_boundary):
            lon_diff = abs(our_lon - p_lon)
            lat_diff = abs(our_lat - p_lat)

            if lon_diff > 180:
                lon_diff = 360 - lon_diff

            assert lon_diff < 0.1
            assert lat_diff < 0.1

    def test_boundary_resolution_5_tokyo(self):
        """Test boundary similarity for Tokyo at resolution 5."""
        lon, lat = 139.6503, 35.6762
        cell_id = lonlat_to_cell(lon, lat, 5)

        our_boundary = cell_to_boundary(cell_id)
        palmer_boundary = palmer_a5.cell_to_boundary(cell_id)

        assert len(our_boundary) == len(palmer_boundary)

        for (our_lon, our_lat), (p_lon, p_lat) in zip(our_boundary, palmer_boundary):
            lon_diff = abs(our_lon - p_lon)
            lat_diff = abs(our_lat - p_lat)

            if lon_diff > 180:
                lon_diff = 360 - lon_diff

            assert lon_diff < 0.1
            assert lat_diff < 0.1

    def test_boundary_resolution_6_tokyo(self):
        """Test boundary similarity for Tokyo at resolution 6."""
        lon, lat = 139.6503, 35.6762
        cell_id = lonlat_to_cell(lon, lat, 6)

        our_boundary = cell_to_boundary(cell_id)
        palmer_boundary = palmer_a5.cell_to_boundary(cell_id)

        assert len(our_boundary) == len(palmer_boundary)

        for (our_lon, our_lat), (p_lon, p_lat) in zip(our_boundary, palmer_boundary):
            lon_diff = abs(our_lon - p_lon)
            lat_diff = abs(our_lat - p_lat)

            if lon_diff > 180:
                lon_diff = 360 - lon_diff

            assert lon_diff < 0.1
            assert lat_diff < 0.1

    @pytest.mark.parametrize("resolution", RESOLUTIONS_7_PLUS)
    def test_boundary_resolution_7_plus_tokyo(self, resolution):
        """Test boundary similarity for Tokyo at resolution 7+."""
        lon, lat = 139.6503, 35.6762
        cell_id = lonlat_to_cell(lon, lat, resolution)

        our_boundary = cell_to_boundary(cell_id)
        palmer_boundary = palmer_a5.cell_to_boundary(cell_id)

        assert len(our_boundary) == len(palmer_boundary)

        for (our_lon, our_lat), (p_lon, p_lat) in zip(our_boundary, palmer_boundary):
            lon_diff = abs(our_lon - p_lon)
            lat_diff = abs(our_lat - p_lat)

            if lon_diff > 180:
                lon_diff = 360 - lon_diff

            assert lon_diff < 0.1
            assert lat_diff < 0.1

    @pytest.mark.parametrize("resolution", RESOLUTIONS_7_PLUS)
    def test_boundary_resolution_7_plus_antimeridian(self, resolution):
        """Test boundary similarity near the antimeridian at resolution 7+."""
        lon, lat = 179.999, 10.0
        cell_id = lonlat_to_cell(lon, lat, resolution)

        our_boundary = cell_to_boundary(cell_id)
        palmer_boundary = palmer_a5.cell_to_boundary(cell_id)

        assert len(our_boundary) == len(palmer_boundary)

        for (our_lon, our_lat), (p_lon, p_lat) in zip(our_boundary, palmer_boundary):
            lon_diff = abs(our_lon - p_lon)
            lat_diff = abs(our_lat - p_lat)

            if lon_diff > 180:
                lon_diff = 360 - lon_diff

            assert lon_diff < 0.1
            assert lat_diff < 0.1
@pytest.mark.skipif(not PALMER_AVAILABLE, reason="Palmer's a5 library not installed")
class TestCenterCompatibility:
    """Test that cell centers are similar to Palmer's."""

    def test_center_resolution_0_nyc(self):
        """Test cell center for NYC at resolution 0."""
        lon, lat = -74.0060, 40.7128
        cell_id = lonlat_to_cell(lon, lat, 0)

        our_lon, our_lat = cell_to_lonlat(cell_id)
        palmer_lon, palmer_lat = palmer_a5.cell_to_lonlat(cell_id)

        lon_diff = abs(our_lon - palmer_lon)
        lat_diff = abs(our_lat - palmer_lat)

        if lon_diff > 180:
            lon_diff = 360 - lon_diff

        # Centers should be quite close (within a few degrees for res 0)
        assert lon_diff < 5.0, (
            f"Center lon mismatch: ours={our_lon}, Palmer's={palmer_lon}"
        )
        assert lat_diff < 5.0, (
            f"Center lat mismatch: ours={our_lat}, Palmer's={palmer_lat}"
        )

    def test_center_resolution_1_global(self):
        """Test cell centers across multiple locations at resolution 1."""
        test_coords = [
            (-74.0060, 40.7128),  # NYC
            (-0.1278, 51.5074),  # London
            (0.0, 0.0),  # Equator
        ]

        for lon, lat in test_coords:
            cell_id = lonlat_to_cell(lon, lat, 1)

            our_lon, our_lat = cell_to_lonlat(cell_id)
            palmer_lon, palmer_lat = palmer_a5.cell_to_lonlat(cell_id)

            lon_diff = abs(our_lon - palmer_lon)
            lat_diff = abs(our_lat - palmer_lat)

            if lon_diff > 180:
                lon_diff = 360 - lon_diff

            # At resolution 1, should be closer
            assert lon_diff < 1.0, (
                f"Center lon mismatch at ({lat}, {lon}): "
                f"ours={our_lon}, Palmer's={palmer_lon}"
            )
            assert lat_diff < 1.0, (
                f"Center lat mismatch at ({lat}, {lon}): "
                f"ours={our_lat}, Palmer's={palmer_lat}"
            )

    def test_center_resolution_2_global(self):
        """Test cell centers across multiple locations at resolution 2."""
        test_coords = [
            (-74.0060, 40.7128),  # NYC
            (-0.1278, 51.5074),  # London
            (0.0, 0.0),  # Equator
            (139.6503, 35.6762),  # Tokyo
        ]

        for lon, lat in test_coords:
            cell_id = lonlat_to_cell(lon, lat, 2)

            our_lon, our_lat = cell_to_lonlat(cell_id)
            palmer_lon, palmer_lat = palmer_a5.cell_to_lonlat(cell_id)

            lon_diff = abs(our_lon - palmer_lon)
            lat_diff = abs(our_lat - palmer_lat)

            if lon_diff > 180:
                lon_diff = 360 - lon_diff

            assert lon_diff < 0.5, (
                f"Center lon mismatch at ({lat}, {lon}): "
                f"ours={our_lon}, Palmer's={palmer_lon}"
            )
            assert lat_diff < 0.5, (
                f"Center lat mismatch at ({lat}, {lon}): "
                f"ours={our_lat}, Palmer's={palmer_lat}"
            )

    def test_center_resolution_2_edge_cases(self):
        """Test cell centers for edge-case points at resolution 2."""
        test_coords = [
            (179.999, 0.0),
            (-179.999, 0.0),
            (0.0, 89.999),
            (0.0, -89.999),
        ]

        for lon, lat in test_coords:
            cell_id = lonlat_to_cell(lon, lat, 2)

            our_lon, our_lat = cell_to_lonlat(cell_id)
            palmer_lon, palmer_lat = palmer_a5.cell_to_lonlat(cell_id)

            lon_diff = abs(our_lon - palmer_lon)
            lat_diff = abs(our_lat - palmer_lat)

            if lon_diff > 180:
                lon_diff = 360 - lon_diff

            assert lon_diff < 0.5, (
                f"Center lon mismatch at ({lat}, {lon}): "
                f"ours={our_lon}, Palmer's={palmer_lon}"
            )
            assert lat_diff < 0.5, (
                f"Center lat mismatch at ({lat}, {lon}): "
                f"ours={our_lat}, Palmer's={palmer_lat}"
            )

    def test_center_resolution_3_global(self):
        """Test cell centers across multiple locations at resolution 3."""
        test_coords = [
            (-74.0060, 40.7128),  # NYC
            (-0.1278, 51.5074),  # London
            (0.0, 0.0),  # Equator
            (139.6503, 35.6762),  # Tokyo
        ]

        for lon, lat in test_coords:
            cell_id = lonlat_to_cell(lon, lat, 3)

            our_lon, our_lat = cell_to_lonlat(cell_id)
            palmer_lon, palmer_lat = palmer_a5.cell_to_lonlat(cell_id)

            lon_diff = abs(our_lon - palmer_lon)
            lat_diff = abs(our_lat - palmer_lat)

            if lon_diff > 180:
                lon_diff = 360 - lon_diff

            assert lon_diff < 0.5, (
                f"Center lon mismatch at ({lat}, {lon}): "
                f"ours={our_lon}, Palmer's={palmer_lon}"
            )
            assert lat_diff < 0.5, (
                f"Center lat mismatch at ({lat}, {lon}): "
                f"ours={our_lat}, Palmer's={palmer_lat}"
            )

    def test_center_resolution_4_global(self):
        """Test cell centers across multiple locations at resolution 4."""
        test_coords = [
            (-74.0060, 40.7128),  # NYC
            (-0.1278, 51.5074),  # London
            (0.0, 0.0),  # Equator
            (139.6503, 35.6762),  # Tokyo
        ]

        for lon, lat in test_coords:
            cell_id = lonlat_to_cell(lon, lat, 4)

            our_lon, our_lat = cell_to_lonlat(cell_id)
            palmer_lon, palmer_lat = palmer_a5.cell_to_lonlat(cell_id)

            lon_diff = abs(our_lon - palmer_lon)
            lat_diff = abs(our_lat - palmer_lat)

            if lon_diff > 180:
                lon_diff = 360 - lon_diff

            assert lon_diff < 0.5, (
                f"Center lon mismatch at ({lat}, {lon}): "
                f"ours={our_lon}, Palmer's={palmer_lon}"
            )
            assert lat_diff < 0.5, (
                f"Center lat mismatch at ({lat}, {lon}): "
                f"ours={our_lat}, Palmer's={palmer_lat}"
            )

    def test_center_resolution_5_global(self):
        """Test cell centers across multiple locations at resolution 5."""
        test_coords = [
            (-74.0060, 40.7128),  # NYC
            (-0.1278, 51.5074),  # London
            (0.0, 0.0),  # Equator
            (139.6503, 35.6762),  # Tokyo
        ]

        for lon, lat in test_coords:
            cell_id = lonlat_to_cell(lon, lat, 5)

            our_lon, our_lat = cell_to_lonlat(cell_id)
            palmer_lon, palmer_lat = palmer_a5.cell_to_lonlat(cell_id)

            lon_diff = abs(our_lon - palmer_lon)
            lat_diff = abs(our_lat - palmer_lat)

            if lon_diff > 180:
                lon_diff = 360 - lon_diff

            assert lon_diff < 0.5, (
                f"Center lon mismatch at ({lat}, {lon}): "
                f"ours={our_lon}, Palmer's={palmer_lon}"
            )
            assert lat_diff < 0.5, (
                f"Center lat mismatch at ({lat}, {lon}): "
                f"ours={our_lat}, Palmer's={palmer_lat}"
            )

    def test_center_resolution_6_global(self):
        """Test cell centers across multiple locations at resolution 6."""
        test_coords = [
            (-74.0060, 40.7128),  # NYC
            (-0.1278, 51.5074),  # London
            (0.0, 0.0),  # Equator
            (139.6503, 35.6762),  # Tokyo
        ]

        for lon, lat in test_coords:
            cell_id = lonlat_to_cell(lon, lat, 6)

            our_lon, our_lat = cell_to_lonlat(cell_id)
            palmer_lon, palmer_lat = palmer_a5.cell_to_lonlat(cell_id)

            lon_diff = abs(our_lon - palmer_lon)
            lat_diff = abs(our_lat - palmer_lat)

            if lon_diff > 180:
                lon_diff = 360 - lon_diff

            assert lon_diff < 0.5, (
                f"Center lon mismatch at ({lat}, {lon}): "
                f"ours={our_lon}, Palmer's={palmer_lon}"
            )
            assert lat_diff < 0.5, (
                f"Center lat mismatch at ({lat}, {lon}): "
                f"ours={our_lat}, Palmer's={palmer_lat}"
            )

    @pytest.mark.parametrize("resolution", RESOLUTIONS_7_PLUS)
    def test_center_resolution_7_plus_global(self, resolution):
        """Test cell centers across multiple locations at resolution 7+."""
        test_coords = [
            (-74.0060, 40.7128),  # NYC
            (-0.1278, 51.5074),  # London
            (0.0, 0.0),  # Equator
            (139.6503, 35.6762),  # Tokyo
        ]

        for lon, lat in test_coords:
            cell_id = lonlat_to_cell(lon, lat, resolution)

            our_lon, our_lat = cell_to_lonlat(cell_id)
            palmer_lon, palmer_lat = palmer_a5.cell_to_lonlat(cell_id)

            lon_diff = abs(our_lon - palmer_lon)
            lat_diff = abs(our_lat - palmer_lat)

            if lon_diff > 180:
                lon_diff = 360 - lon_diff

            assert lon_diff < 0.5, (
                f"Center lon mismatch at ({lat}, {lon}): "
                f"ours={our_lon}, Palmer's={palmer_lon}"
            )
            assert lat_diff < 0.5, (
                f"Center lat mismatch at ({lat}, {lon}): "
                f"ours={our_lat}, Palmer's={palmer_lat}"
            )

    @pytest.mark.parametrize("resolution", RESOLUTIONS_7_PLUS)
    def test_center_resolution_7_plus_edge_cases(self, resolution):
        """Test cell centers for edge-case points at resolution 7+."""
        test_coords = [
            (179.999, 0.0),
            (-179.999, 0.0),
            (0.0, 89.999),
            (0.0, -89.999),
        ]

        for lon, lat in test_coords:
            cell_id = lonlat_to_cell(lon, lat, resolution)

            our_lon, our_lat = cell_to_lonlat(cell_id)
            palmer_lon, palmer_lat = palmer_a5.cell_to_lonlat(cell_id)

            lon_diff = abs(our_lon - palmer_lon)
            lat_diff = abs(our_lat - palmer_lat)

            if lon_diff > 180:
                lon_diff = 360 - lon_diff

            assert lon_diff < 0.5, (
                f"Center lon mismatch at ({lat}, {lon}): "
                f"ours={our_lon}, Palmer's={palmer_lon}"
            )
            assert lat_diff < 0.5, (
                f"Center lat mismatch at ({lat}, {lon}): "
                f"ours={our_lat}, Palmer's={palmer_lat}"
            )


@pytest.mark.skipif(not PALMER_AVAILABLE, reason="Palmer's a5 library not installed")
class TestComprehensiveCompatibility:
    """Comprehensive compatibility tests across many points."""

    def test_all_dodecahedron_faces_resolution_0(self):
        """Test that we get all 12 unique cell IDs at resolution 0."""
        # Sample points distributed around the globe
        test_points = []
        for lat in range(-80, 81, 40):  # -80, -40, 0, 40, 80
            for lon in range(-180, 180, 60):  # Every 60 degrees
                test_points.append((lon, lat))

        our_cells = set()
        palmer_cells = set()

        for lon, lat in test_points:
            our_cell = lonlat_to_cell(lon, lat, 0)
            palmer_cell = palmer_a5.lonlat_to_cell((lon, lat), 0)

            our_cells.add(our_cell)
            palmer_cells.add(palmer_cell)

        # Should have found all 12 faces
        assert len(our_cells) == 12, f"Found {len(our_cells)} cells, expected 12"
        assert len(palmer_cells) == 12

        # The sets should be identical
        assert our_cells == palmer_cells, (
            f"Cell ID sets don't match:\n"
            f"Ours: {sorted(our_cells)}\n"
            f"Palmer's: {sorted(palmer_cells)}"
        )

    def test_resolution_1_matches_across_globe(self):
        """Test resolution 1 cell IDs match across many points."""
        # Test grid of points
        mismatches = []

        for lat in range(-85, 86, 15):  # Every 15 degrees
            for lon in range(-180, 180, 15):
                our_cell = lonlat_to_cell(lon, lat, 1)
                palmer_cell = palmer_a5.lonlat_to_cell((lon, lat), 1)

                if our_cell != palmer_cell:
                    mismatches.append((lon, lat, our_cell, palmer_cell))

        # Report any mismatches
        if mismatches:
            mismatch_report = "\n".join(
                f"  ({lon}, {lat}): ours={our:016x}, Palmer's={palmer:016x}"
                for lon, lat, our, palmer in mismatches[:10]  # Show first 10
            )
            pytest.fail(
                f"Found {len(mismatches)} cell ID mismatches at resolution 1:\n"
                f"{mismatch_report}"
            )


if __name__ == "__main__":
    if PALMER_AVAILABLE:
        print("Palmer's palmer_a5 library is available - running compatibility tests")
        pytest.main([__file__, "-v"])
    else:
        print("Palmer's palmer_a5 library not available - skipping compatibility tests")
        print("To install: git clone https://github.com/felixpalmer/a5-py")
        print("Then: cd a5-py && pip install -e .")
