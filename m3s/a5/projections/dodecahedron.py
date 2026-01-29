"""
Dodecahedron projection for mapping between spherical and face coordinates.

Ported from Felix Palmer's a5-py implementation.
Original source: https://github.com/felixpalmer/a5-py/blob/main/a5/projections/dodecahedron.py
"""

import math
from typing import List, Literal, Tuple

from m3s.a5.constants import (
    DISTANCE_TO_EDGE,
    INTERHEDRAL_ANGLE,
    PI_OVER_5,
    TWO_PI_OVER_5,
)
from m3s.a5.projections import vec2_utils as vec2
from m3s.a5.projections import vec3_utils as vec3
from m3s.a5.projections.gnomonic import GnomonicProjection
from m3s.a5.projections.origin_data import origins
from m3s.a5.projections.polyhedral import (
    Cartesian,
    Face,
    FaceTriangle,
    PolyhedralProjection,
    SphericalTriangle,
)

# Type definitions
FaceTriangleIndex = Literal[0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
OriginId = Literal[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]


def _to_cartesian(spherical: Tuple[float, float]) -> Cartesian:
    """Convert spherical coordinates to Cartesian."""
    theta, phi = spherical
    x = math.sin(phi) * math.cos(theta)
    y = math.sin(phi) * math.sin(theta)
    z = math.cos(phi)
    return (x, y, z)


def _to_spherical(cartesian: Cartesian) -> Tuple[float, float]:
    """Convert Cartesian coordinates to spherical."""
    x, y, z = cartesian
    theta = math.atan2(y, x)
    phi = math.acos(z)
    return (theta, phi)


def _to_polar(face: Face) -> Tuple[float, float]:
    """Convert face coordinates to polar coordinates."""
    x, y = face
    rho = math.sqrt(x * x + y * y)
    gamma = math.atan2(y, x)
    return (rho, gamma)


def _to_face(polar: Tuple[float, float]) -> Face:
    """Convert polar coordinates to face coordinates."""
    rho, gamma = polar
    x = rho * math.cos(gamma)
    y = rho * math.sin(gamma)
    return (x, y)


class QuintantVertices:
    """Helper class for managing quintant triangle vertices."""

    def __init__(self, vertices: Tuple[Face, Face, Face]):
        self.vertices = vertices

    def get_vertices(self) -> List[Face]:
        """Get the three vertices of the quintant triangle."""
        return list(self.vertices)


def get_quintant_vertices(quintant: int) -> QuintantVertices:
    """
    Get the vertices for a given quintant triangle.

    Parameters
    ----------
    quintant : int
        Quintant index (0-4)

    Returns
    -------
    QuintantVertices
        Object containing the three triangle vertices
    """
    # Import here to avoid circular dependency
    from m3s.a5.geometry import QUINTANT_ROTATIONS, TRIANGLE_VERTICES

    # Get triangle base vertices
    u, v, w = TRIANGLE_VERTICES

    # Apply rotation for this quintant
    rotation = QUINTANT_ROTATIONS[quintant]

    # Rotate each vertex
    def rotate_vertex(vertex: Tuple[float, float]) -> Face:
        x, y = vertex
        rotated_x = rotation[0][0] * x + rotation[0][1] * y
        rotated_y = rotation[1][0] * x + rotation[1][1] * y
        return (rotated_x, rotated_y)

    # Triangle vertices in order: center, corner1, corner2
    v_center = rotate_vertex(u)
    v_corner1 = rotate_vertex(v)
    v_corner2 = rotate_vertex(w)

    return QuintantVertices((v_center, v_corner1, v_corner2))


class DodecahedronProjection:
    """
    Dodecahedron projection for mapping between spherical and face coordinates.

    This is the main projection class that orchestrates:
    - Gnomonic projection for initial mapping
    - Triangle determination for correct face region
    - Polyhedral projection for equal-area properties
    """

    def __init__(self):
        self.face_triangles: List[FaceTriangle] = []
        self.spherical_triangles: List[SphericalTriangle] = []
        self.polyhedral = PolyhedralProjection()
        self.gnomonic = GnomonicProjection()

    def forward(self, spherical: Tuple[float, float], origin_id: int) -> Face:
        """
        Project spherical coordinates to face coordinates using dodecahedron projection.

        Parameters
        ----------
        spherical : Tuple[float, float]
            Spherical coordinates [theta, phi] in radians
        origin_id : int
            Origin ID (0-11)

        Returns
        -------
        Face
            Face coordinates [x, y]
        """
        origin = origins[origin_id]

        # Transform back to origin space
        unprojected = _to_cartesian(spherical)
        out = vec3.create()
        out = vec3.transformQuat(out, unprojected, origin.inverse_quat)

        # Unproject gnomonically to polar coordinates in origin space
        projected_spherical = _to_spherical(out)
        polar = self.gnomonic.forward(projected_spherical)

        # Rotate around face axis to remove origin rotation
        rho, gamma = polar
        polar = (rho, gamma - origin.angle)

        face_triangle_index = self.get_face_triangle_index(polar)
        reflect = self.should_reflect(polar)
        face_triangle = self.get_face_triangle(face_triangle_index, reflect, False)
        spherical_triangle = self.get_spherical_triangle(
            face_triangle_index, origin_id, reflect
        )

        return self.polyhedral.forward(unprojected, spherical_triangle, face_triangle)

    def inverse(self, face: Face, origin_id: int) -> Tuple[float, float]:
        """
        Unproject face coordinates to spherical coordinates using dodecahedron projection.

        Parameters
        ----------
        face : Face
            Face coordinates [x, y]
        origin_id : int
            Origin ID (0-11)

        Returns
        -------
        Tuple[float, float]
            Spherical coordinates [theta, phi] in radians

        Notes
        -----
        TEMPORARY: This implementation appears to have issues. Using Palmer's
        implementation for comparison.
        """
        # Use Palmer's implementation for now
        try:
            from a5.core.cell import _dodecahedron as palmer_dodec

            return palmer_dodec.inverse(face, origin_id)
        except ImportError:
            pass

        # Fallback to native (has known accuracy issues)
        polar = _to_polar(face)
        face_triangle_index = self.get_face_triangle_index(polar)

        reflect = self.should_reflect(polar)
        face_triangle = self.get_face_triangle(face_triangle_index, reflect, False)
        spherical_triangle = self.get_spherical_triangle(
            face_triangle_index, origin_id, reflect
        )

        unprojected = self.polyhedral.inverse(face, face_triangle, spherical_triangle)
        return _to_spherical(unprojected)

    def should_reflect(self, polar: Tuple[float, float]) -> bool:
        """
        Detect when point is beyond the edge of the dodecahedron face.

        In the standard case (reflect = false), the face and spherical triangle can be
        used directly. In the reflected case (reflect = true), the point is beyond the
        edge of the dodecahedron face, and so the face triangle is squashed to unproject
        correctly onto the neighboring dodecahedron face.

        Parameters
        ----------
        polar : Tuple[float, float]
            Polar coordinates

        Returns
        -------
        bool
            True if point is beyond the edge of the dodecahedron face
        """
        rho, gamma = polar
        D = _to_face((rho, self.normalize_gamma(gamma)))[0]
        return D > DISTANCE_TO_EDGE

    def get_face_triangle_index(self, polar: Tuple[float, float]) -> int:
        """
        Given a polar coordinate, returns the index of the face triangle it belongs to.

        Parameters
        ----------
        polar : Tuple[float, float]
            Polar coordinates

        Returns
        -------
        int
            Face triangle index, value from 0 to 9
        """
        _, gamma = polar
        return int((math.floor(gamma / PI_OVER_5) + 10) % 10)

    def get_face_triangle(
        self, face_triangle_index: int, reflected: bool = False, squashed: bool = False
    ) -> FaceTriangle:
        """
        Get the face triangle for a given polar coordinate.

        Parameters
        ----------
        face_triangle_index : int
            Face triangle index, value from 0 to 9
        reflected : bool, optional
            Whether to get reflected triangle
        squashed : bool, optional
            Whether to get squashed triangle

        Returns
        -------
        FaceTriangle
            3 vertices in counter-clockwise order
        """
        index = face_triangle_index
        if reflected:
            index += 20 if squashed else 10

        # Extend array if needed
        while len(self.face_triangles) <= index:
            self.face_triangles.append(None)

        if self.face_triangles[index] is not None:
            return self.face_triangles[index]

        if reflected:
            self.face_triangles[index] = self._get_reflected_face_triangle(
                face_triangle_index, squashed
            )
        else:
            self.face_triangles[index] = self._get_face_triangle(face_triangle_index)

        return self.face_triangles[index]

    def _get_face_triangle(self, face_triangle_index: int) -> FaceTriangle:
        """Get the basic (non-reflected) face triangle."""
        quintant = math.floor((face_triangle_index + 1) / 2) % 5

        vertices = get_quintant_vertices(quintant).get_vertices()
        v_center, v_corner1, v_corner2 = vertices[0], vertices[1], vertices[2]

        # Calculate edge midpoint using vec2.lerp
        v_edge_midpoint = vec2.create()
        vec2.lerp(v_edge_midpoint, v_corner1, v_corner2, 0.5)
        v_edge_midpoint = (v_edge_midpoint[0], v_edge_midpoint[1])

        # Sign of gamma determines which triangle we want to use, and thus vertex order
        even = face_triangle_index % 2 == 0

        # Note: center & midpoint compared to DGGAL implementation are swapped
        # as we are using a dodecahedron, rather than an icosahedron.
        return (
            (v_center, v_edge_midpoint, v_corner1)
            if even
            else (v_center, v_corner2, v_edge_midpoint)
        )

    def _get_reflected_face_triangle(
        self, face_triangle_index: int, squashed: bool = False
    ) -> FaceTriangle:
        """Get the reflected face triangle."""
        # First obtain ordinary unreflected triangle
        face_triangle = self._get_face_triangle(face_triangle_index)
        A = vec2.clone(face_triangle[0])
        B = vec2.clone(face_triangle[1])
        C = vec2.clone(face_triangle[2])

        # Reflect dodecahedron center (A) across edge (BC)
        even = face_triangle_index % 2 == 0
        vec2.negate(A, A)
        midpoint = B if even else C

        # Squashing is important. A squashed triangle when unprojected will yield the correct spherical triangle.
        scale_factor = (1 + 1 / math.cos(INTERHEDRAL_ANGLE)) if squashed else 2
        # Manual scaleAndAdd: A = A + midpoint * scale_factor
        A[0] += midpoint[0] * scale_factor
        A[1] += midpoint[1] * scale_factor

        # Swap midpoint and corner to maintain correct vertex order
        return ((A[0], A[1]), (C[0], C[1]), (B[0], B[1]))

    def get_spherical_triangle(
        self, face_triangle_index: int, origin_id: int, reflected: bool = False
    ) -> SphericalTriangle:
        """
        Get the spherical triangle for a given face triangle index and origin.

        Parameters
        ----------
        face_triangle_index : int
            Face triangle index
        origin_id : int
            Origin ID
        reflected : bool, optional
            Whether to get reflected triangle

        Returns
        -------
        SphericalTriangle
            Spherical triangle
        """
        index = 10 * origin_id + face_triangle_index  # 0-119
        if reflected:
            index += 120

        # Extend array if needed
        while len(self.spherical_triangles) <= index:
            self.spherical_triangles.append(None)

        if self.spherical_triangles[index] is not None:
            return self.spherical_triangles[index]

        self.spherical_triangles[index] = self._get_spherical_triangle(
            face_triangle_index, origin_id, reflected
        )
        return self.spherical_triangles[index]

    def _get_spherical_triangle(
        self, face_triangle_index: int, origin_id: int, reflected: bool = False
    ) -> SphericalTriangle:
        """Compute the spherical triangle for given parameters."""
        origin = origins[origin_id]
        face_triangle = self.get_face_triangle(face_triangle_index, reflected, True)

        spherical_triangle = []
        for face in face_triangle:
            rho, gamma = _to_polar(face)
            rotated_polar = (rho, gamma + origin.angle)
            rotated = _to_cartesian(self.gnomonic.inverse(rotated_polar))
            # Transform using vec3.transformQuat
            transformed = vec3.create()
            vec3.transformQuat(transformed, rotated, origin.quat)
            # Normalize to ensure unit vector
            vec3.normalize(transformed, transformed)
            vertex = (transformed[0], transformed[1], transformed[2])
            spherical_triangle.append(vertex)

        return tuple(spherical_triangle)

    def normalize_gamma(self, gamma: float) -> float:
        """
        Normalize gamma to the range [-PI_OVER_5, PI_OVER_5].

        Parameters
        ----------
        gamma : float
            The gamma value to normalize

        Returns
        -------
        float
            Normalized gamma value
        """
        segment = gamma / TWO_PI_OVER_5
        s_center = round(segment)
        s_offset = segment - s_center

        # Azimuthal angle from triangle bisector
        beta = s_offset * TWO_PI_OVER_5
        return beta
