"""
Unit tests for A5 grid system Phase 1-2 (Resolution 0-1).

These tests validate the implementation of:
- Constants and geometry
- Coordinate transformations
- Cell ID serialization
- Basic cell operations (res 0-1)
- M3S integration
"""

import math

import numpy as np
import pytest
from shapely.geometry import Point

from m3s.a5 import A5Grid, cell_to_boundary, cell_to_lonlat, lonlat_to_cell
from m3s.a5.constants import (
    DODEC_ORIGINS,
    EPSILON,
    MAX_LATITUDE,
    MAX_LONGITUDE,
    MIN_LATITUDE,
    MIN_LONGITUDE,
    PHI,
)
from m3s.a5.coordinates import CoordinateTransformer
from m3s.a5.geometry import Dodecahedron, Pentagon
from m3s.a5.serialization import A5Serializer


class TestConstants:
    """Test A5 constants."""

    def test_golden_ratio(self):
        """Verify golden ratio value."""
        expected_phi = (1 + math.sqrt(5)) / 2
        assert abs(PHI - expected_phi) < EPSILON
        assert abs(PHI - 1.618034) < 0.000001

    def test_dodecahedron_origins(self):
        """Verify dodecahedron has 12 origins."""
        assert len(DODEC_ORIGINS) == 12

    def test_origin_structure(self):
        """Verify origin structure (theta, phi tuples)."""
        for origin in DODEC_ORIGINS:
            assert isinstance(origin, tuple)
            assert len(origin) == 2
            theta, phi = origin
            # Theta in [0, 2π]
            assert 0 <= theta <= 2 * math.pi
            # Phi in [0, π]
            assert 0 <= phi <= math.pi

    def test_latitude_longitude_bounds(self):
        """Verify coordinate bounds."""
        assert MIN_LATITUDE == -90.0
        assert MAX_LATITUDE == 90.0
        assert MIN_LONGITUDE == -180.0
        assert MAX_LONGITUDE == 180.0


class TestPentagonGeometry:
    """Test Pentagon geometry operations."""

    def test_create_base_vertices(self):
        """Test creation of base pentagon vertices."""
        vertices = Pentagon.create_base_vertices()
        assert vertices.shape == (5, 2)
        assert isinstance(vertices, np.ndarray)

    def test_vertex_coordinates(self):
        """Verify vertices are finite numbers."""
        vertices = Pentagon.create_base_vertices()
        assert np.all(np.isfinite(vertices))

    def test_transform_vertex(self):
        """Test vertex transformation."""
        vertex = np.array([1.0, 0.0])

        # Test scaling
        scaled = Pentagon.transform_vertex(vertex, scale=2.0)
        assert np.allclose(scaled, [2.0, 0.0])

        # Test rotation (90 degrees)
        rotated = Pentagon.transform_vertex(vertex, rotation=math.pi / 2)
        assert np.allclose(rotated, [0.0, 1.0], atol=1e-10)

    def test_subdivide_into_quintants(self):
        """Test pentagon subdivision into 5 quintants."""
        vertices = Pentagon.create_base_vertices()
        quintants = Pentagon.subdivide_into_quintants(vertices)

        assert len(quintants) == 5
        for q in quintants:
            assert q.shape == (5, 2)

    def test_get_centroid(self):
        """Test centroid calculation."""
        vertices = Pentagon.create_base_vertices()
        centroid = Pentagon.get_centroid(vertices)

        assert centroid.shape == (2,)
        assert np.all(np.isfinite(centroid))

    def test_scale_for_resolution(self):
        """Test resolution-based scaling."""
        vertices = Pentagon.create_base_vertices()

        # Resolution 0 should return unchanged
        res0 = Pentagon.scale_for_resolution(vertices, 0)
        assert np.allclose(res0, vertices)

        # Resolution 1 should scale down
        res1 = Pentagon.scale_for_resolution(vertices, 1)
        scale_factor = 1.0 / math.sqrt(5)
        expected = vertices * scale_factor
        assert np.allclose(res1, expected)


class TestDodecahedronGeometry:
    """Test Dodecahedron geometry operations."""

    def test_initialization(self):
        """Test dodecahedron initialization."""
        dodec = Dodecahedron()
        assert len(dodec.origins) == 12

    def test_origin_vectors(self):
        """Test origin vector computation."""
        dodec = Dodecahedron()
        assert dodec._origin_vectors.shape == (12, 3)

        # All vectors should be unit length (on sphere)
        for vec in dodec._origin_vectors:
            length = np.linalg.norm(vec)
            assert abs(length - 1.0) < 1e-6

    def test_find_nearest_origin(self):
        """Test finding nearest dodecahedron face."""
        dodec = Dodecahedron()

        # North pole should be nearest to origin 0
        north_pole = np.array([0, 0, 1])
        origin_id = dodec.find_nearest_origin(north_pole)
        assert origin_id == 0

        # South pole should be nearest to origin 9 (after Hilbert reordering)
        south_pole = np.array([0, 0, -1])
        origin_id = dodec.find_nearest_origin(south_pole)
        assert origin_id == 9

    def test_get_origin_spherical(self):
        """Test getting origin in spherical coordinates."""
        dodec = Dodecahedron()

        theta, phi = dodec.get_origin_spherical(0)
        assert isinstance(theta, float)
        assert isinstance(phi, float)

        # Invalid origin should raise error
        with pytest.raises(ValueError):
            dodec.get_origin_spherical(12)

    def test_get_origin_cartesian(self):
        """Test getting origin in Cartesian coordinates."""
        dodec = Dodecahedron()

        xyz = dodec.get_origin_cartesian(0)
        assert xyz.shape == (3,)
        assert np.all(np.isfinite(xyz))

        # Should be unit vector
        length = np.linalg.norm(xyz)
        assert abs(length - 1.0) < 1e-6

    def test_get_adjacent_origins(self):
        """Test getting adjacent face IDs."""
        dodec = Dodecahedron()

        # Each face has exactly 5 neighbors
        for origin_id in range(12):
            neighbors = dodec.get_adjacent_origins(origin_id)
            assert len(neighbors) == 5
            assert all(0 <= n < 12 for n in neighbors)

        # Invalid origin should raise error
        with pytest.raises(ValueError):
            dodec.get_adjacent_origins(12)


class TestCoordinateTransformations:
    """Test coordinate transformation operations."""

    def test_lonlat_to_spherical(self):
        """Test lonlat to spherical conversion."""
        transformer = CoordinateTransformer()

        # Equator at prime meridian
        theta, phi = transformer.lonlat_to_spherical(0, 0)
        assert isinstance(theta, float)
        assert isinstance(phi, float)
        assert 0 <= theta <= 2 * math.pi
        assert 0 <= phi <= math.pi

    def test_spherical_to_lonlat(self):
        """Test spherical to lonlat conversion."""
        transformer = CoordinateTransformer()

        # Test roundtrip
        lon, lat = transformer.spherical_to_lonlat(0, math.pi / 2)
        assert -180 <= lon <= 180
        assert -90 <= lat <= 90

    def test_lonlat_roundtrip(self):
        """Test lonlat -> spherical -> lonlat roundtrip."""
        transformer = CoordinateTransformer()

        test_points = [
            (0, 0),  # Equator, prime meridian
            (90, 45),  # Mid-latitude
            (-90, -45),  # Southern hemisphere
            (179, 85),  # Near pole
            (-179, -85),  # Near south pole
        ]

        for lon, lat in test_points:
            theta, phi = transformer.lonlat_to_spherical(lon, lat)
            lon2, lat2 = transformer.spherical_to_lonlat(theta, phi)

            # Allow small tolerance for floating point
            assert abs(lat - lat2) < 1e-6
            # Longitude wrapping may occur
            lon_diff = abs(lon - lon2)
            assert lon_diff < 1e-6 or abs(lon_diff - 360) < 1e-6

    def test_spherical_to_cartesian(self):
        """Test spherical to Cartesian conversion."""
        transformer = CoordinateTransformer()

        xyz = transformer.spherical_to_cartesian(0, 0)
        assert xyz.shape == (3,)
        assert np.all(np.isfinite(xyz))

        # Should be on unit sphere
        length = np.linalg.norm(xyz)
        assert abs(length - 1.0) < 1e-6

    def test_cartesian_to_spherical(self):
        """Test Cartesian to spherical conversion."""
        transformer = CoordinateTransformer()

        # North pole
        xyz = np.array([0, 0, 1])
        theta, phi = transformer.cartesian_to_spherical(xyz)
        assert abs(phi) < 1e-6  # phi = 0 at north pole

    def test_cartesian_roundtrip(self):
        """Test spherical -> Cartesian -> spherical roundtrip."""
        transformer = CoordinateTransformer()

        test_spherical = [
            (0, math.pi / 2),  # Equator
            (math.pi / 2, math.pi / 4),  # Mid-latitude
            (0, 0),  # North pole
            (0, math.pi),  # South pole
        ]

        for theta, phi in test_spherical:
            xyz = transformer.spherical_to_cartesian(theta, phi)
            theta2, phi2 = transformer.cartesian_to_spherical(xyz)

            assert abs(phi - phi2) < 1e-6
            # Theta is undefined at poles
            if abs(phi) > 1e-6 and abs(phi - math.pi) > 1e-6:
                theta_diff = abs(theta - theta2)
                assert theta_diff < 1e-6 or abs(theta_diff - 2 * math.pi) < 1e-6

    def test_ij_to_polar(self):
        """Test IJ to polar conversion."""
        transformer = CoordinateTransformer()

        r, theta = transformer.ij_to_polar(1, 0)
        assert abs(r - 1.0) < EPSILON
        assert abs(theta - 0.0) < EPSILON

        r, theta = transformer.ij_to_polar(0, 1)
        assert abs(r - 1.0) < EPSILON
        assert abs(theta - math.pi / 2) < EPSILON

    def test_determine_quintant(self):
        """Test quintant determination."""
        transformer = CoordinateTransformer()

        # Test each quintant (0-4)
        for q in range(5):
            angle = q * (2 * math.pi / 5) + 0.1  # Offset to be clearly in quintant
            i = math.cos(angle)
            j = math.sin(angle)
            quintant = transformer.determine_quintant(i, j)
            assert quintant == q


class TestSerialization:
    """Test cell ID serialization."""

    def test_encode_resolution_0(self):
        """Test encoding resolution 0 cell."""
        serializer = A5Serializer()

        cell_id = serializer.encode(origin=0, segment=0, s=0, resolution=0)
        assert isinstance(cell_id, int)
        assert cell_id > 0

    def test_encode_resolution_1(self):
        """Test encoding resolution 1 cell."""
        serializer = A5Serializer()

        cell_id = serializer.encode(origin=5, segment=3, s=0, resolution=1)
        assert isinstance(cell_id, int)
        assert cell_id > 0

    def test_decode_resolution_0(self):
        """Test decoding resolution 0 cell."""
        serializer = A5Serializer()

        cell_id = serializer.encode(origin=7, segment=0, s=0, resolution=0)
        origin, segment, s, resolution = serializer.decode(cell_id)

        assert origin == 7
        assert segment == 0
        assert s == 0
        assert resolution == 0

    def test_decode_resolution_1(self):
        """Test decoding resolution 1 cell."""
        serializer = A5Serializer()

        cell_id = serializer.encode(origin=3, segment=4, s=0, resolution=1)
        origin, segment, s, resolution = serializer.decode(cell_id)

        assert origin == 3
        assert segment == 4
        assert s == 0
        assert resolution == 1

    def test_encode_decode_roundtrip(self):
        """Test encode -> decode roundtrip."""
        serializer = A5Serializer()

        # Test resolution 0 (only origin, no segment)
        for origin in range(12):
            cell_id = serializer.encode(origin, 0, 0, 0)
            decoded = serializer.decode(cell_id)

            assert decoded[0] == origin
            assert decoded[1] == 0  # segment always 0 at res 0
            assert decoded[2] == 0  # s value
            assert decoded[3] == 0  # resolution

        # Test resolution 1 and higher (with segments)
        for resolution in [1, 2]:
            for origin in range(12):
                for segment in range(5):
                    cell_id = serializer.encode(origin, segment, 0, resolution)
                    decoded = serializer.decode(cell_id)

                    assert decoded[0] == origin
                    assert decoded[1] == segment
                    assert decoded[2] == 0  # s value
                    assert decoded[3] == resolution

    def test_invalid_origin(self):
        """Test invalid origin raises error."""
        serializer = A5Serializer()

        with pytest.raises(ValueError):
            serializer.encode(origin=12, segment=0, s=0, resolution=0)

    def test_invalid_segment(self):
        """Test invalid segment raises error."""
        serializer = A5Serializer()

        with pytest.raises(ValueError):
            serializer.encode(origin=0, segment=5, s=0, resolution=0)

    def test_invalid_resolution(self):
        """Test invalid resolution raises error."""
        serializer = A5Serializer()

        with pytest.raises(ValueError):
            serializer.encode(origin=0, segment=0, s=0, resolution=-1)

        with pytest.raises(ValueError):
            serializer.encode(origin=0, segment=0, s=0, resolution=31)

    def test_cell_id_to_string(self):
        """Test cell ID to hex string conversion."""
        serializer = A5Serializer()

        cell_id = serializer.encode(origin=0, segment=0, s=0, resolution=0)
        hex_str = serializer.cell_id_to_string(cell_id)

        assert isinstance(hex_str, str)
        assert len(hex_str) == 16
        assert all(c in "0123456789abcdef" for c in hex_str)

    def test_string_to_cell_id(self):
        """Test hex string to cell ID conversion."""
        serializer = A5Serializer()

        cell_id = serializer.encode(origin=5, segment=2, s=0, resolution=1)
        hex_str = serializer.cell_id_to_string(cell_id)
        recovered = serializer.string_to_cell_id(hex_str)

        assert recovered == cell_id


class TestCellOperations:
    """Test cell operations."""

    def test_lonlat_to_cell_resolution_0(self):
        """Test lonlat to cell conversion at resolution 0."""
        # NYC coordinates
        cell_id = lonlat_to_cell(-74.0060, 40.7128, 0)
        assert isinstance(cell_id, int)
        assert cell_id > 0

    def test_lonlat_to_cell_resolution_1(self):
        """Test lonlat to cell conversion at resolution 1."""
        # London coordinates
        cell_id = lonlat_to_cell(-0.1278, 51.5074, 1)
        assert isinstance(cell_id, int)
        assert cell_id > 0

    def test_cell_to_lonlat_resolution_0(self):
        """Test cell to lonlat conversion at resolution 0."""
        cell_id = lonlat_to_cell(-74.0060, 40.7128, 0)
        lon, lat = cell_to_lonlat(cell_id)

        assert -180 <= lon <= 180
        assert -90 <= lat <= 90

    def test_cell_to_lonlat_resolution_1(self):
        """Test cell to lonlat conversion at resolution 1."""
        cell_id = lonlat_to_cell(-0.1278, 51.5074, 1)
        lon, lat = cell_to_lonlat(cell_id)

        assert -180 <= lon <= 180
        assert -90 <= lat <= 90

    def test_cell_to_boundary(self):
        """Test cell boundary generation."""
        cell_id = lonlat_to_cell(-74.0060, 40.7128, 1)
        boundary = cell_to_boundary(cell_id)

        # Should be a list of coordinates
        assert isinstance(boundary, list)
        assert len(boundary) >= 5  # At least 5 vertices for pentagon

        # Each coordinate should be (lon, lat)
        for coord in boundary:
            assert isinstance(coord, tuple)
            assert len(coord) == 2
            lon, lat = coord
            assert -180 <= lon <= 360  # May use 0-360 for antimeridian
            assert -90 <= lat <= 90

    def test_same_point_same_cell(self):
        """Test that same point always gives same cell."""
        lon, lat = -74.0060, 40.7128

        cell_id1 = lonlat_to_cell(lon, lat, 1)
        cell_id2 = lonlat_to_cell(lon, lat, 1)

        assert cell_id1 == cell_id2

    def test_nearby_points_resolution_behavior(self):
        """Test that nearby points may be in same or different cells."""
        # Very close points
        cell1 = lonlat_to_cell(-74.0060, 40.7128, 0)
        cell2 = lonlat_to_cell(-74.0061, 40.7129, 0)

        # At resolution 0, very close points might be in same cell
        # (12 large cells cover the globe)
        assert isinstance(cell1, int)
        assert isinstance(cell2, int)


class TestA5Grid:
    """Test A5Grid M3S integration."""

    def test_initialization_resolution_0(self):
        """Test grid initialization at resolution 0."""
        grid = A5Grid(precision=0)
        assert grid.precision == 0

    def test_initialization_resolution_1(self):
        """Test grid initialization at resolution 1."""
        grid = A5Grid(precision=1)
        assert grid.precision == 1

    def test_initialization_invalid_resolution(self):
        """Test that invalid resolution raises error."""
        with pytest.raises(ValueError):
            A5Grid(precision=-1)

        with pytest.raises(ValueError):
            A5Grid(precision=31)

    def test_initialization_phase2_resolution(self):
        """Test that resolution >= 2 is now supported (Phase 2 complete)."""
        # Phase 2: Resolutions 2-30 are now supported via Palmer delegation
        grid = A5Grid(precision=2)
        assert grid.precision == 2

    def test_get_cell_from_point(self):
        """Test getting cell from point."""
        grid = A5Grid(precision=1)
        cell = grid.get_cell_from_point(40.7128, -74.0060)

        assert cell is not None
        assert cell.precision == 1
        assert cell.polygon is not None
        assert cell.identifier.startswith("a5_1_")

    def test_cell_contains_point(self):
        """Test that cell contains its generating point."""
        grid = A5Grid(precision=1)
        lat, lon = 40.7128, -74.0060

        cell = grid.get_cell_from_point(lat, lon)
        point = Point(lon, lat)

        # Cell should contain or be very close to the generating point
        assert cell.polygon.contains(point) or cell.polygon.distance(point) < 0.1

    def test_get_cells_from_points(self):
        """Test getting cells from multiple points."""
        grid = A5Grid(precision=1)

        points = [
            (40.7128, -74.0060),  # NYC
            (51.5074, -0.1278),  # London
            (35.6762, 139.6503),  # Tokyo
        ]

        cells = grid.get_cells_from_points(points)

        assert len(cells) == 3
        for cell in cells:
            assert cell.precision == 1
            assert cell.polygon is not None

    def test_grid_repr(self):
        """Test grid string representation."""
        grid = A5Grid(precision=1)
        repr_str = repr(grid)

        assert "A5Grid" in repr_str
        assert "precision=1" in repr_str


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
