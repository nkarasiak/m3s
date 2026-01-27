"""
A5 Coordinate Transformations.

This module provides coordinate system transformations for the A5 grid:
- lonlat ↔ spherical ↔ Cartesian conversions
- Face projection (3D to 2D on dodecahedron face)
- IJ ↔ polar conversions
- Quintant determination
"""

import math
from typing import Optional, Tuple

import numpy as np

from m3s.a5.constants import (
    EPSILON,
    LONGITUDE_OFFSET,
    LONGITUDE_OFFSET_DEGREES,
    MAX_LATITUDE,
    MAX_LONGITUDE,
    MIN_LATITUDE,
    MIN_LONGITUDE,
    R_INSCRIBED,
    validate_latitude,
    validate_longitude,
)
from m3s.a5.geometry import BASIS, BASIS_INVERSE

# Authalic projection coefficients (from Palmer's implementation)
# These ensure equal-area properties when mapping the WGS84 ellipsoid to a sphere
# Source: https://arxiv.org/pdf/2212.05818
GEODETIC_TO_AUTHALIC = (
    -2.2392098386786394e-03,
    2.1308606513250217e-06,
    -2.5592576864212742e-09,
    3.3701965267802837e-12,
    -4.6675453126112487e-15,
    6.6749287038481596e-18,
)

AUTHALIC_TO_GEODETIC = (
    2.2392089963541657e-03,
    2.8831978048607556e-06,
    5.0862207399726603e-09,
    1.0201812377816100e-11,
    2.1912872306767718e-14,
    4.9284235482523806e-17,
)


class CoordinateTransformer:
    """
    Coordinate transformation utilities for A5 grid system.

    This class handles all coordinate conversions between:
    - Geographic (lon, lat)
    - Spherical (theta, phi)
    - Cartesian (x, y, z)
    - Face IJ coordinates
    - Polar (r, theta) for quintant determination
    """

    @staticmethod
    def _apply_authalic_coefficients(phi: float, coefficients: tuple) -> float:
        """
        Apply authalic projection coefficients using Clenshaw summation.

        This implements the proper equal-area (authalic) projection that converts
        between geodetic and authalic latitudes on the WGS84 ellipsoid.

        Parameters
        ----------
        phi : float
            Input latitude in radians
        coefficients : tuple
            Polynomial coefficients for the transformation

        Returns
        -------
        float
            Transformed latitude in radians
        """
        sin_phi = math.sin(phi)
        cos_phi = math.cos(phi)
        X = 2 * (cos_phi - sin_phi) * (cos_phi + sin_phi)  # = cos(2*phi)

        # Clenshaw summation (order 6)
        C0, C1, C2, C3, C4, C5 = coefficients

        B6 = 0.0
        B5 = C5
        B4 = X * B5 + C4
        B3 = X * B4 - B5 + C3
        B2 = X * B3 - B4 + C2
        B1 = X * B2 - B3 + C1
        B0 = X * B1 - B2 + C0

        return phi + math.sin(2 * phi) * B0

    @staticmethod
    def geodetic_to_authalic(lat_rad: float) -> float:
        """
        Convert geodetic latitude to authalic latitude.

        Parameters
        ----------
        lat_rad : float
            Geodetic latitude in radians

        Returns
        -------
        float
            Authalic latitude in radians
        """
        return CoordinateTransformer._apply_authalic_coefficients(
            lat_rad, GEODETIC_TO_AUTHALIC
        )

    @staticmethod
    def authalic_to_geodetic(lat_rad: float) -> float:
        """
        Convert authalic latitude to geodetic latitude.

        Parameters
        ----------
        lat_rad : float
            Authalic latitude in radians

        Returns
        -------
        float
            Geodetic latitude in radians
        """
        return CoordinateTransformer._apply_authalic_coefficients(
            lat_rad, AUTHALIC_TO_GEODETIC
        )

    @staticmethod
    def lonlat_to_spherical(lon: float, lat: float) -> Tuple[float, float]:
        """
        Convert longitude/latitude to spherical coordinates.

        This transformation includes:
        1. 93° longitude offset for grid alignment
        2. Conversion to radians
        3. Authalic (equal-area) projection for latitude

        Parameters
        ----------
        lon : float
            Longitude in degrees [-180, 180]
        lat : float
            Latitude in degrees [-90, 90]

        Returns
        -------
        Tuple[float, float]
            (theta, phi) where:
            - theta: azimuthal angle in radians [0, 2π]
            - phi: polar angle from north pole in radians [0, π]

        Raises
        ------
        ValueError
            If lon or lat are out of valid ranges
        """
        validate_longitude(lon)
        validate_latitude(lat)

        # Apply longitude offset and convert to radians (match Palmer's ordering)
        theta = math.radians(lon + LONGITUDE_OFFSET_DEGREES)

        # Convert latitude to radians
        geodetic_lat_rad = math.radians(lat)

        # Apply authalic (equal-area) projection to latitude
        # This ensures proper equal-area mapping from WGS84 ellipsoid to sphere
        authalic_lat_rad = CoordinateTransformer.geodetic_to_authalic(geodetic_lat_rad)

        # Convert from latitude to polar angle (phi = π/2 - lat)
        phi = math.pi / 2 - authalic_lat_rad

        return theta, phi

    @staticmethod
    def lonlat_to_spherical_unchecked(lon: float, lat: float) -> Tuple[float, float]:
        """
        Convert longitude/latitude to spherical coordinates without range validation.

        This mirrors lonlat_to_spherical but skips input checks so internal sampling
        can match Palmer's behavior when temporary samples fall outside valid ranges.
        """
        theta = math.radians(lon + LONGITUDE_OFFSET_DEGREES)
        geodetic_lat_rad = math.radians(lat)
        authalic_lat_rad = CoordinateTransformer.geodetic_to_authalic(geodetic_lat_rad)
        phi = math.pi / 2 - authalic_lat_rad
        return theta, phi

    @staticmethod
    def spherical_to_lonlat(theta: float, phi: float) -> Tuple[float, float]:
        """
        Convert spherical coordinates to longitude/latitude.

        Inverse of lonlat_to_spherical.

        Parameters
        ----------
        theta : float
            Azimuthal angle in radians
        phi : float
            Polar angle from north pole in radians

        Returns
        -------
        Tuple[float, float]
            (lon, lat) in degrees
        """
        # Convert phi to authalic latitude
        authalic_lat_rad = math.pi / 2 - phi

        # Convert authalic latitude to geodetic latitude
        geodetic_lat_rad = CoordinateTransformer.authalic_to_geodetic(authalic_lat_rad)
        lat = math.degrees(geodetic_lat_rad)

        # Convert theta to longitude (remove offset)
        lon = math.degrees(theta) - LONGITUDE_OFFSET_DEGREES

        return lon, lat

    @staticmethod
    def spherical_to_cartesian(theta: float, phi: float) -> np.ndarray:
        """
        Convert spherical to 3D Cartesian coordinates.

        Parameters
        ----------
        theta : float
            Azimuthal angle in radians
        phi : float
            Polar angle from north pole in radians

        Returns
        -------
        np.ndarray
            3D Cartesian coordinates [x, y, z] on unit sphere
        """
        x = R_INSCRIBED * math.sin(phi) * math.cos(theta)
        y = R_INSCRIBED * math.sin(phi) * math.sin(theta)
        z = R_INSCRIBED * math.cos(phi)

        return np.array([x, y, z])

    @staticmethod
    def cartesian_to_spherical(xyz: np.ndarray) -> Tuple[float, float]:
        """
        Convert 3D Cartesian to spherical coordinates.

        Parameters
        ----------
        xyz : np.ndarray
            3D Cartesian coordinates [x, y, z]

        Returns
        -------
        Tuple[float, float]
            (theta, phi) in radians
        """
        x, y, z = xyz

        # Calculate radius (should be ~1.0 for unit sphere)
        r = math.sqrt(x * x + y * y + z * z)

        # Avoid division by zero
        if r < EPSILON:
            return 0.0, 0.0

        # Polar angle from north pole
        phi = math.acos(np.clip(z / r, -1.0, 1.0))

        # Azimuthal angle
        theta = math.atan2(y, x)
        if theta < 0:
            theta += 2 * math.pi

        return theta, phi

    @staticmethod
    def lonlat_to_cartesian(lon: float, lat: float) -> np.ndarray:
        """
        Convert longitude/latitude directly to Cartesian.

        Parameters
        ----------
        lon : float
            Longitude in degrees
        lat : float
            Latitude in degrees

        Returns
        -------
        np.ndarray
            3D Cartesian coordinates [x, y, z]
        """
        theta, phi = CoordinateTransformer.lonlat_to_spherical(lon, lat)
        return CoordinateTransformer.spherical_to_cartesian(theta, phi)

    @staticmethod
    def cartesian_to_lonlat(xyz: np.ndarray) -> Tuple[float, float]:
        """
        Convert Cartesian directly to longitude/latitude.

        Parameters
        ----------
        xyz : np.ndarray
            3D Cartesian coordinates [x, y, z]

        Returns
        -------
        Tuple[float, float]
            (lon, lat) in degrees
        """
        theta, phi = CoordinateTransformer.cartesian_to_spherical(xyz)
        return CoordinateTransformer.spherical_to_lonlat(theta, phi)

    @staticmethod
    def cartesian_to_face_ij(
        xyz: np.ndarray, origin_xyz: np.ndarray, origin_id: int
    ) -> Tuple[float, float]:
        """
        Project 3D Cartesian point to 2D face coordinates.

        This uses the polyhedral projection (Slice & Dice algorithm) to map
        points from the sphere to the dodecahedron face plane with proper
        equal-area properties and segment determination.

        Parameters
        ----------
        xyz : np.ndarray
            3D point on sphere [x, y, z]
        origin_xyz : np.ndarray
            Face center in 3D [x, y, z]
        origin_id : int
            Origin ID (0-11) for the dodecahedron face

        Returns
        -------
        Tuple[float, float]
            (x, y) coordinates on the face's 2D plane

        Notes
        -----
        This now uses Felix Palmer's polyhedral projection which ensures:
        - Proper equal-area mapping
        - Correct segment determination for resolution 1+
        - Quaternion-based coordinate transformations
        - Compatibility with Palmer's a5-py reference implementation
        """
        from m3s.a5.projections.dodecahedron import DodecahedronProjection

        # Convert Cartesian to spherical coordinates
        theta, phi = CoordinateTransformer.cartesian_to_spherical(xyz)
        spherical = (theta, phi)

        # Use polyhedral projection for proper equal-area mapping
        proj = DodecahedronProjection()
        i, j = proj.forward(spherical, origin_id)

        return i, j

    @staticmethod
    def face_ij_to_cartesian(
        i: float,
        j: float,
        origin_xyz: Optional[np.ndarray] = None,
        origin_id: Optional[int] = None,
    ) -> np.ndarray:
        """
        Convert 2D face coordinates back to 3D Cartesian.

        Inverse of cartesian_to_face_ij.

        Parameters
        ----------
        i : float
            I coordinate on face
        j : float
            J coordinate on face
        origin_xyz : np.ndarray, optional
            Face center in 3D [x, y, z] for fallback projection
        origin_id : int, optional
            Origin ID for polyhedral inverse projection

        Returns
        -------
        np.ndarray
            3D Cartesian coordinates [x, y, z] on sphere
        """
        if origin_id is not None:
            from m3s.a5.projections.dodecahedron import DodecahedronProjection

            proj = DodecahedronProjection()
            theta, phi = proj.inverse((i, j), origin_id)
            return CoordinateTransformer.spherical_to_cartesian(theta, phi)

        if origin_xyz is None:
            raise ValueError("origin_xyz or origin_id must be provided")

        face_normal = origin_xyz / np.linalg.norm(origin_xyz)

        if abs(face_normal[2]) < 0.9:
            up = np.array([0, 0, 1])
        else:
            up = np.array([1, 0, 0])

        basis_i = np.cross(face_normal, up)
        basis_i = basis_i / np.linalg.norm(basis_i)

        basis_j = np.cross(face_normal, basis_i)
        basis_j = basis_j / np.linalg.norm(basis_j)

        offset = i * basis_i + j * basis_j
        point_on_plane = face_normal + offset
        point_on_sphere = point_on_plane / np.linalg.norm(point_on_plane)

        return point_on_sphere * R_INSCRIBED

    @staticmethod
    def ij_to_polar(i: float, j: float) -> Tuple[float, float]:
        """
        Convert IJ coordinates to polar (r, theta).

        Used for determining which quintant (0-4) a point belongs to.

        Parameters
        ----------
        i : float
            I coordinate
        j : float
            J coordinate

        Returns
        -------
        Tuple[float, float]
            (r, theta) where:
            - r: distance from origin
            - theta: angle in radians [0, 2π]
        """
        r = math.sqrt(i * i + j * j)
        theta = math.atan2(j, i)

        return r, theta

    @staticmethod
    def determine_quintant(i: float, j: float) -> int:
        """
        Determine which quintant (0-4) based on IJ coordinates.

        The pentagon is divided into 5 equal quintants, each spanning 72°.
        Uses rounding to match Palmer's implementation.

        Parameters
        ----------
        i : float
            I coordinate
        j : float
            J coordinate

        Returns
        -------
        int
            Quintant ID (0-4)
        """
        _, gamma = CoordinateTransformer.ij_to_polar(i, j)

        # Each quintant spans 72° (2π/5 radians)
        TWO_PI_OVER_5 = 2 * math.pi / 5

        # Use rounding to match Palmer's method
        quintant = (round(gamma / TWO_PI_OVER_5) + 5) % 5

        return quintant

    @staticmethod
    def face_to_ij(face: Tuple[float, float]) -> Tuple[float, float]:
        """
        Convert face coordinates to IJ lattice coordinates.
        """
        basis_flat = [
            BASIS_INVERSE[0][0],
            BASIS_INVERSE[1][0],
            BASIS_INVERSE[0][1],
            BASIS_INVERSE[1][1],
        ]
        out = [0.0, 0.0]
        from m3s.a5.projections import vec2_utils as vec2

        vec2.transformMat2(out, face, basis_flat)
        return (out[0], out[1])

    @staticmethod
    def ij_to_face(ij: Tuple[float, float]) -> Tuple[float, float]:
        """
        Convert IJ lattice coordinates to face coordinates.
        """
        basis_flat = [
            BASIS[0][0],
            BASIS[1][0],
            BASIS[0][1],
            BASIS[1][1],
        ]
        out = [0.0, 0.0]
        from m3s.a5.projections import vec2_utils as vec2

        vec2.transformMat2(out, ij, basis_flat)
        return (out[0], out[1])

    @staticmethod
    def normalize_longitudes(coords: list) -> list:
        """
        Normalize longitudes to handle antimeridian crossing.
        """
        if not coords:
            return coords

        points = [
            CoordinateTransformer._lonlat_to_cartesian_unchecked(lon, lat)
            for lon, lat in coords
        ]
        center = np.array([0.0, 0.0, 0.0])
        for point in points:
            center += point

        norm = np.linalg.norm(center)
        if norm > 0:
            center /= norm

        center_lon, center_lat = CoordinateTransformer.cartesian_to_lonlat(center)
        if center_lat > 89.99 or center_lat < -89.99:
            center_lon = coords[0][0]

        center_lon = ((center_lon + 180) % 360 + 360) % 360 - 180

        result = []
        for lon, lat in coords:
            while lon - center_lon > 180:
                lon -= 360
            while lon - center_lon < -180:
                lon += 360
            result.append((lon, lat))

        return result

    @staticmethod
    def _lonlat_to_cartesian_unchecked(lon: float, lat: float) -> np.ndarray:
        """Convert longitude/latitude to Cartesian without range validation."""
        theta = math.radians(lon + LONGITUDE_OFFSET_DEGREES)
        geodetic_lat_rad = math.radians(lat)
        authalic_lat_rad = CoordinateTransformer.geodetic_to_authalic(geodetic_lat_rad)
        phi = math.pi / 2 - authalic_lat_rad
        return CoordinateTransformer.spherical_to_cartesian(theta, phi)

    @staticmethod
    def normalize_antimeridian(coords: list) -> list:
        """
        Handle antimeridian crossing by normalizing longitudes.

        When a polygon crosses the antimeridian (±180°), longitudes need
        to be adjusted to prevent rendering issues.

        Parameters
        ----------
        coords : list
            List of (lon, lat) tuples

        Returns
        -------
        list
            Normalized (lon, lat) tuples

        Notes
        -----
        This function detects large longitude jumps (> 180°) and adjusts
        coordinates to use the 0-360° range instead of -180 to 180°.
        """
        return CoordinateTransformer.normalize_longitudes(coords)

    @staticmethod
    def wrap_longitude(lon: float) -> float:
        """
        Wrap longitude to [-180, 180] range.

        Parameters
        ----------
        lon : float
            Longitude in degrees

        Returns
        -------
        float
            Wrapped longitude in [-180, 180]
        """
        while lon > 180:
            lon -= 360
        while lon < -180:
            lon += 360
        return lon
