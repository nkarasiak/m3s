"""
Polyhedral Equal Area projection using Slice & Dice algorithm.

Ported from Felix Palmer's a5-py implementation.
Original source: https://github.com/felixpalmer/a5-py/blob/main/a5/projections/polyhedral.py

Adaptation of icoVertexGreatCircle.ec from DGGAL project (BSD 3-Clause License).
Copyright (c) 2014-2025, Ecere Corporation
Copyright (c) 2024, A5 Project Contributors
"""

import math
from typing import Dict, Tuple

import numpy as np

from m3s.a5.projections import vec3_utils as vec3

# Type aliases for clarity
Cartesian = Tuple[float, float, float]  # 3D point on sphere
Face = Tuple[float, float]  # 2D point on face plane
Barycentric = Tuple[float, float, float]  # Barycentric coordinates
FaceTriangle = Tuple[Face, Face, Face]  # Triangle on face plane
SphericalTriangle = Tuple[Cartesian, Cartesian, Cartesian]  # Triangle on sphere


def _spherical_triangle_area(triangle: SphericalTriangle) -> float:
    """
    Calculate the area of a spherical triangle using L'Huilier's theorem.

    Parameters
    ----------
    triangle : SphericalTriangle
        Three vertices on the unit sphere

    Returns
    -------
    float
        Area of the spherical triangle
    """
    A, B, C = triangle

    # Calculate side lengths (great circle distances)
    a = vec3.angle(B, C)
    b = vec3.angle(A, C)
    c = vec3.angle(A, B)

    # Semi-perimeter
    s = (a + b + c) / 2

    # L'Huilier's theorem for spherical excess
    # tan(E/4)² = tan(s/2) * tan((s-a)/2) * tan((s-b)/2) * tan((s-c)/2)
    tan_quarter_excess_sq = (
        math.tan(s / 2)
        * math.tan((s - a) / 2)
        * math.tan((s - b) / 2)
        * math.tan((s - c) / 2)
    )

    if tan_quarter_excess_sq < 0:
        tan_quarter_excess_sq = 0

    # Area = spherical excess
    excess = 4 * math.atan(math.sqrt(tan_quarter_excess_sq))
    return excess


def _face_to_barycentric(point: Face, triangle: FaceTriangle) -> Barycentric:
    """
    Convert face coordinates to barycentric coordinates.

    Parameters
    ----------
    point : Face
        Point on face plane
    triangle : FaceTriangle
        Triangle vertices on face plane

    Returns
    -------
    Barycentric
        Barycentric coordinates (u, v, w) where u + v + w = 1
    """
    p = np.array([point[0], point[1]])
    A = np.array([triangle[0][0], triangle[0][1]])
    B = np.array([triangle[1][0], triangle[1][1]])
    C = np.array([triangle[2][0], triangle[2][1]])

    # Vectors from A to B and A to C
    v0 = C - A
    v1 = B - A
    v2 = p - A

    # Compute dot products
    dot00 = np.dot(v0, v0)
    dot01 = np.dot(v0, v1)
    dot02 = np.dot(v0, v2)
    dot11 = np.dot(v1, v1)
    dot12 = np.dot(v1, v2)

    # Compute barycentric coordinates
    inv_denom = 1 / (dot00 * dot11 - dot01 * dot01)
    v = (dot11 * dot02 - dot01 * dot12) * inv_denom
    w = (dot00 * dot12 - dot01 * dot02) * inv_denom
    u = 1 - v - w

    return (u, v, w)


def _barycentric_to_face(barycentric: Barycentric, triangle: FaceTriangle) -> Face:
    """
    Convert barycentric coordinates to face coordinates.

    Parameters
    ----------
    barycentric : Barycentric
        Barycentric coordinates (u, v, w)
    triangle : FaceTriangle
        Triangle vertices on face plane

    Returns
    -------
    Face
        Point on face plane
    """
    u, v, w = barycentric
    A, B, C = triangle

    x = u * A[0] + v * B[0] + w * C[0]
    y = u * A[1] + v * B[1] + w * C[1]

    return (x, y)


class PolyhedralProjection:
    """
    Polyhedral Equal Area projection using Slice & Dice algorithm.

    This projection ensures equal-area properties when mapping between
    spherical triangles and planar triangles.
    """

    def __init__(self):
        # Cache for triangle-dependent calculations in inverse projection
        self._inverse_triangle_cache: Dict[Tuple, Dict] = {}

    def forward(
        self,
        v: Cartesian,
        spherical_triangle: SphericalTriangle,
        face_triangle: FaceTriangle,
    ) -> Face:
        """
        Forward projection: converts a spherical point to face coordinates.

        Parameters
        ----------
        v : Cartesian
            The spherical point to project
        spherical_triangle : SphericalTriangle
            The spherical triangle vertices
        face_triangle : FaceTriangle
            The face triangle vertices

        Returns
        -------
        Face
            The face coordinates
        """
        A, B, C = spherical_triangle

        # When v is close to A, the quadruple product is unstable.
        # As we just need the intersection of two great circles we can use difference
        # between A and v, as it lies in the same plane of the great circle containing A & v
        Z = vec3.create()
        vec3.subtract(Z, v, A)
        vec3.normalize(Z, Z)
        Z = (Z[0], Z[1], Z[2])

        p = vec3.create()
        vec3.quadrupleProduct(p, A, Z, B, C)
        vec3.normalize(p, p)
        p = (p[0], p[1], p[2])

        h = vec3.vectorDifference(A, v) / vec3.vectorDifference(A, p)
        Area_ABC = _spherical_triangle_area(spherical_triangle)
        scaled_area = h / Area_ABC

        b = (
            1 - h,
            scaled_area * _spherical_triangle_area((A, p, C)),
            scaled_area * _spherical_triangle_area((A, B, p)),
        )

        return _barycentric_to_face(b, face_triangle)

    def inverse(
        self,
        face_point: Face,
        face_triangle: FaceTriangle,
        spherical_triangle: SphericalTriangle,
    ) -> Cartesian:
        """
        Inverse projection: converts face coordinates back to spherical coordinates.

        Parameters
        ----------
        face_point : Face
            The face coordinates
        face_triangle : FaceTriangle
            The face triangle vertices
        spherical_triangle : SphericalTriangle
            The spherical triangle vertices

        Returns
        -------
        Cartesian
            The spherical coordinates
        """
        A, B, C = spherical_triangle
        b = _face_to_barycentric(face_point, face_triangle)

        threshold = 1 - 1e-14
        if b[0] > threshold:
            return A
        if b[1] > threshold:
            return B
        if b[2] > threshold:
            return C

        # Get cached triangle-dependent constants
        constants = self._get_triangle_constants(spherical_triangle)
        area_abc = constants["area_abc"]
        # c1 = constants["c1"]  # Not used in current calculation
        c01 = constants["c01"]
        c12 = constants["c12"]
        c20 = constants["c20"]
        s12 = constants["s12"]
        V = constants["V"]

        # Point-dependent calculations
        h = 1 - b[0]
        R = b[2] / h
        alpha = R * area_abc
        S = math.sin(alpha)
        half_c = math.sin(alpha / 2)
        CC = 2 * half_c * half_c  # Half angle formula

        f = S * V + CC * (c01 * c12 - c20)
        g = CC * s12 * (1 + c01)
        q = (2 / math.acos(c12)) * math.atan2(g, f)

        # Use gl-matrix style slerp for P = slerp(B, C, q)
        P = vec3.create()
        vec3.slerp(P, B, C, q)
        P = (P[0], P[1], P[2])

        # K = A - P
        K = vec3.vectorDifference(A, P)
        t = self._safe_acos(h * K) / self._safe_acos(K)

        # Final slerp: out = slerp(A, P, t)
        out = [0.0, 0.0, 0.0]
        vec3.slerp(out, A, P, t)
        return (out[0], out[1], out[2])

    def _get_triangle_constants(self, spherical_triangle: SphericalTriangle):
        """
        Get cached triangle-dependent constants for inverse projection.

        These values only depend on the spherical triangle, not the input point.
        """
        # Create a cache key from the triangle vertices
        # Convert to tuples since lists aren't hashable
        A, B, C = spherical_triangle
        cache_key = (tuple(A), tuple(B), tuple(C))

        if cache_key not in self._inverse_triangle_cache:
            c1 = vec3.create()
            vec3.cross(c1, B, C)

            constants = {
                "area_abc": _spherical_triangle_area(spherical_triangle),
                "c1": (c1[0], c1[1], c1[2]),  # Store as tuple
                "c01": vec3.dot(A, B),
                "c12": vec3.dot(B, C),
                "c20": vec3.dot(C, A),
                "s12": vec3.length(c1),
                "V": vec3.dot(A, c1),  # Triple product of A, B, C
            }
            self._inverse_triangle_cache[cache_key] = constants

        return self._inverse_triangle_cache[cache_key]

    def _safe_acos(self, x: float) -> float:
        """
        Compute acos(1 - 2 * x * x) without loss of precision for small x.

        Parameters
        ----------
        x : float
            Input value

        Returns
        -------
        float
            acos(1 - x)
        """
        if x < 1e-3:
            return 2 * x + x * x * x / 3
        else:
            return math.acos(1 - 2 * x * x)
