"""
A5 Pentagon and Dodecahedron Geometry.

This module provides geometric operations for pentagons and the dodecahedron
structure used in the A5 grid system.
"""

import math
from typing import List, Tuple

import numpy as np

from m3s.a5.constants import (
    BASIS_ROTATION,
    DODEC_ORIGINS,
    PENTAGON_ANGLE_A,
    PENTAGON_ANGLE_B,
    PENTAGON_ANGLE_D,
    PENTAGON_ANGLE_E,
    PHI,
    R_INSCRIBED,
)


class Pentagon:
    """
    Pentagon geometry operations.

    This class provides methods for creating and transforming pentagon vertices
    used in the A5 grid system.
    """

    @staticmethod
    def create_base_vertices() -> np.ndarray:
        """
        Create the 5 vertices of a base pentagon.

        The pentagon is constructed using the specific angles defined in the
        A5 specification (PENTAGON_ANGLE_A through E), which are derived from
        circle intersections to create the proper pentagonal tessellation.

        Returns
        -------
        np.ndarray
            Array of shape (5, 2) containing [x, y] coordinates of vertices,
            labeled as points a, b, c, d, e in order.

        Notes
        -----
        The vertices are positioned to align with the dodecahedral face
        structure and enable proper hierarchical subdivision.
        """
        # Start with vertex 'a' at origin
        a = np.array([0.0, 0.0])

        # Vertex 'b' is at angle A from vertex a
        # Place at unit distance initially (will be scaled later)
        b_angle = PENTAGON_ANGLE_A
        b = np.array([math.cos(b_angle), math.sin(b_angle)])

        # Vertex 'c' - the key vertex for lattice alignment
        # Angle B is measured from 'a' in the direction that creates
        # the proper pentagon shape
        c_angle = PENTAGON_ANGLE_B
        c = np.array([math.cos(c_angle), math.sin(c_angle)])

        # Vertex 'd' and 'e' complete the pentagon
        # These are calculated to maintain the pentagon's internal angles
        # Angle C is the regular pentagon interior angle (108°)
        d_angle = PENTAGON_ANGLE_A + PENTAGON_ANGLE_D
        d = np.array([math.cos(d_angle), math.sin(d_angle)])

        e_angle = PENTAGON_ANGLE_E
        e = np.array([math.cos(e_angle), math.sin(e_angle)])

        vertices = np.array([a, b, c, d, e])

        # Normalize vertices to create proper edge lengths
        # The scale factor ensures proper tessellation
        scale = 1.0 / PHI  # Golden ratio scaling for dodecahedral faces
        vertices = vertices * scale

        return vertices

    @staticmethod
    def transform_vertex(
        vertex: np.ndarray, scale: float = 1.0, rotation: float = 0.0
    ) -> np.ndarray:
        """
        Apply scaling and rotation transformation to a vertex.

        Parameters
        ----------
        vertex : np.ndarray
            2D vertex coordinates [x, y]
        scale : float, optional
            Scaling factor (default: 1.0)
        rotation : float, optional
            Rotation angle in radians (default: 0.0)

        Returns
        -------
        np.ndarray
            Transformed vertex coordinates
        """
        # Apply scaling
        transformed = vertex * scale

        # Apply rotation if non-zero
        if abs(rotation) > 1e-10:
            cos_r = math.cos(rotation)
            sin_r = math.sin(rotation)
            rotation_matrix = np.array([[cos_r, -sin_r], [sin_r, cos_r]])
            transformed = rotation_matrix @ transformed

        return transformed

    @staticmethod
    def apply_basis_rotation(vertices: np.ndarray) -> np.ndarray:
        """
        Apply the basis rotation to align pentagon with dodecahedral lattice.

        This rotation aligns the lattice growth direction (line AC) parallel
        to the x-axis, which is essential for proper hierarchical subdivision.

        Parameters
        ----------
        vertices : np.ndarray
            Array of shape (N, 2) containing vertex coordinates

        Returns
        -------
        np.ndarray
            Rotated vertices
        """
        cos_r = math.cos(BASIS_ROTATION)
        sin_r = math.sin(BASIS_ROTATION)
        rotation_matrix = np.array([[cos_r, -sin_r], [sin_r, cos_r]])

        return vertices @ rotation_matrix.T

    @staticmethod
    def subdivide_into_quintants(vertices: np.ndarray) -> List[np.ndarray]:
        """
        Subdivide a pentagon into 5 quintants (72° rotational segments).

        Each quintant represents one-fifth of the pentagon, rotated by
        multiples of 72° (2π/5 radians).

        Parameters
        ----------
        vertices : np.ndarray
            Pentagon vertices (5, 2)

        Returns
        -------
        List[np.ndarray]
            List of 5 vertex arrays, one for each quintant

        Notes
        -----
        This subdivision is fundamental to the A5 hierarchical structure,
        where each cell at resolution n contains 5 cells at resolution n+1.
        """
        quintants = []
        quintant_angle = 2 * math.pi / 5  # 72 degrees

        for i in range(5):
            angle = i * quintant_angle
            cos_a = math.cos(angle)
            sin_a = math.sin(angle)
            rotation_matrix = np.array([[cos_a, -sin_a], [sin_a, cos_a]])

            rotated_vertices = vertices @ rotation_matrix.T
            quintants.append(rotated_vertices)

        return quintants

    @staticmethod
    def get_centroid(vertices: np.ndarray) -> np.ndarray:
        """
        Calculate the centroid of a pentagon.

        Parameters
        ----------
        vertices : np.ndarray
            Pentagon vertices (5, 2)

        Returns
        -------
        np.ndarray
            Centroid coordinates [x, y]
        """
        return np.mean(vertices, axis=0)

    @staticmethod
    def scale_for_resolution(vertices: np.ndarray, resolution: int) -> np.ndarray:
        """
        Scale pentagon vertices for a specific resolution.

        At each resolution level, cells are subdivided into 5 smaller cells.
        This means the scale factor decreases by sqrt(5) at each level.

        Parameters
        ----------
        vertices : np.ndarray
            Base pentagon vertices
        resolution : int
            Target resolution level

        Returns
        -------
        np.ndarray
            Scaled vertices

        Notes
        -----
        The scaling follows the pattern:
        - Resolution 0: scale = 1.0
        - Resolution 1: scale = 1/sqrt(5)
        - Resolution 2: scale = 1/5
        - Resolution n: scale = 1/(sqrt(5)^n)
        """
        if resolution == 0:
            return vertices

        # Scale decreases by sqrt(5) per resolution level
        scale_factor = 1.0 / (math.sqrt(5) ** resolution)
        return vertices * scale_factor


class Dodecahedron:
    """
    Dodecahedron geometry and face operations.

    The dodecahedron has 12 pentagonal faces, which serve as the base
    structure for the A5 grid system.
    """

    def __init__(self):
        """Initialize dodecahedron with 12 face origins."""
        self.origins = DODEC_ORIGINS
        self._origin_vectors = self._compute_origin_vectors()

    def _compute_origin_vectors(self) -> np.ndarray:
        """
        Compute 3D Cartesian vectors for each dodecahedron face origin.

        Returns
        -------
        np.ndarray
            Array of shape (12, 3) containing unit vectors pointing to
            each face center
        """
        vectors = np.zeros((12, 3))

        for i, (theta, phi) in enumerate(self.origins):
            # Convert spherical to Cartesian
            # theta: azimuthal angle (longitude)
            # phi: polar angle (from north pole)
            x = R_INSCRIBED * math.sin(phi) * math.cos(theta)
            y = R_INSCRIBED * math.sin(phi) * math.sin(theta)
            z = R_INSCRIBED * math.cos(phi)
            vectors[i] = [x, y, z]

        return vectors

    def find_nearest_origin(self, point) -> int:
        """
        Find the nearest dodecahedron face to a point on the sphere.

        Uses haversine formula to calculate great-circle distance,
        matching Palmer's implementation exactly.

        Parameters
        ----------
        point : Tuple[float, float] or np.ndarray
            Either spherical coordinates (theta, phi) in radians,
            or Cartesian coordinates [x, y, z]

        Returns
        -------
        int
            Origin ID (0-11) of the nearest face

        Notes
        -----
        This uses spherical distance (haversine) rather than Cartesian
        dot products, which is critical for matching Palmer's A5 specification.
        """
        # Convert Cartesian to spherical if needed
        if isinstance(point, np.ndarray):
            from m3s.a5.coordinates import CoordinateTransformer

            theta_phi = CoordinateTransformer.cartesian_to_spherical(point)
        else:
            theta_phi = point

        min_distance = float("inf")
        nearest_id = 0

        for origin_id, origin_coords in enumerate(self.origins):
            distance = self._haversine(theta_phi, origin_coords)
            if distance < min_distance:
                min_distance = distance
                nearest_id = origin_id

        return nearest_id

    def _haversine(
        self, point: Tuple[float, float], axis: Tuple[float, float]
    ) -> float:
        """
        Modified haversine formula to calculate great-circle distance.

        Returns the "angle" parameter (not the full arc distance), which is
        sufficient for comparing distances. This matches Palmer's implementation.

        Parameters
        ----------
        point : Tuple[float, float]
            Point in spherical coordinates (theta, phi)
        axis : Tuple[float, float]
            Axis in spherical coordinates (theta, phi)

        Returns
        -------
        float
            The "angle" parameter from haversine formula (for comparison)
        """
        theta, phi = point
        theta2, phi2 = axis

        dtheta = theta2 - theta
        dphi = phi2 - phi

        a1 = math.sin(dphi / 2)
        a2 = math.sin(dtheta / 2)

        # Return 'a' parameter directly (not full haversine)
        # This is faster and sufficient for distance comparison
        angle = a1 * a1 + a2 * a2 * math.sin(phi) * math.sin(phi2)

        return angle

    def get_origin_spherical(self, origin_id: int) -> Tuple[float, float]:
        """
        Get spherical coordinates of a face origin.

        Parameters
        ----------
        origin_id : int
            Origin ID (0-11)

        Returns
        -------
        Tuple[float, float]
            (theta, phi) in radians, where:
            - theta: azimuthal angle (longitude-like)
            - phi: polar angle (from north pole)

        Raises
        ------
        ValueError
            If origin_id is not in range [0, 11]
        """
        if not 0 <= origin_id < 12:
            raise ValueError(f"Origin ID must be 0-11, got {origin_id}")

        return self.origins[origin_id]

    def get_origin_cartesian(self, origin_id: int) -> np.ndarray:
        """
        Get Cartesian coordinates of a face origin.

        Parameters
        ----------
        origin_id : int
            Origin ID (0-11)

        Returns
        -------
        np.ndarray
            3D Cartesian coordinates [x, y, z]

        Raises
        ------
        ValueError
            If origin_id is not in range [0, 11]
        """
        if not 0 <= origin_id < 12:
            raise ValueError(f"Origin ID must be 0-11, got {origin_id}")

        return self._origin_vectors[origin_id].copy()

    def get_adjacent_origins(self, origin_id: int) -> List[int]:
        """
        Get IDs of adjacent (neighboring) dodecahedron faces.

        Each pentagonal face has exactly 5 neighboring faces.

        Parameters
        ----------
        origin_id : int
            Origin ID (0-11)

        Returns
        -------
        List[int]
            List of 5 adjacent origin IDs

        Notes
        -----
        This is used for finding neighboring cells across face boundaries.
        The adjacency structure follows the dodecahedron's edge connectivity.
        """
        # Dodecahedron adjacency structure
        # Each face has exactly 5 neighbors
        adjacency_map = {
            0: [1, 2, 3, 4, 5],  # North pole neighbors ring 1
            1: [0, 2, 6, 7, 5],
            2: [0, 3, 7, 8, 1],
            3: [0, 4, 8, 9, 2],
            4: [0, 5, 9, 10, 3],
            5: [0, 1, 10, 6, 4],
            6: [1, 5, 10, 11, 7],
            7: [2, 1, 6, 11, 8],
            8: [3, 2, 7, 11, 9],
            9: [4, 3, 8, 11, 10],
            10: [5, 4, 9, 11, 6],
            11: [6, 7, 8, 9, 10],  # South pole neighbors ring 2
        }

        if not 0 <= origin_id < 12:
            raise ValueError(f"Origin ID must be 0-11, got {origin_id}")

        return adjacency_map[origin_id]


# ============================================================================
# Pentagon Basis Matrices for Lattice Alignment
# ============================================================================

# Ported from Felix Palmer's a5-py/a5/core/pentagon.py
# These matrices are used for proper lattice alignment in the pentagon tiling

# Pentagon constants (from Palmer's pentagon.py)
PI_OVER_5 = math.pi / 5
PI_OVER_10 = math.pi / 10

# Distance to edge of pentagon face (golden ratio - 1)
DISTANCE_TO_EDGE = (math.sqrt(5) - 1) / 2  # PHI - 1

# Pentagon vertices (calculated from circle intersections)
_pentagon_a = (0.0, 0.0)
_pentagon_b = (0.0, 1.0)
_pentagon_c = (0.7885966681787006, 1.6149108024237764)
_pentagon_d = (1.6171013659387945, 1.054928690397459)
_pentagon_e = (math.cos(PI_OVER_10), math.sin(PI_OVER_10))

# Distance to edge midpoint
_c_norm = math.sqrt(_pentagon_c[0] * _pentagon_c[0] + _pentagon_c[1] * _pentagon_c[1])
_edge_midpoint_d = 2 * _c_norm * math.cos(PI_OVER_5)

# Lattice growth direction is AC, rotate it to be parallel to x-axis
_basis_rotation = PI_OVER_5 - math.atan2(
    _pentagon_c[1], _pentagon_c[0]
)  # -27.97 degrees

# Scale to match unit sphere
_scale = 2 * DISTANCE_TO_EDGE / _edge_midpoint_d


def _transform_pentagon_vertex(
    vertex: Tuple[float, float], scale: float, rotation: float
) -> Tuple[float, float]:
    """
    Apply scale and rotation to a pentagon vertex.

    Parameters
    ----------
    vertex : Tuple[float, float]
        Vertex coordinates (x, y)
    scale : float
        Scale factor
    rotation : float
        Rotation angle in radians

    Returns
    -------
    Tuple[float, float]
        Transformed vertex
    """
    # Scale
    scaled_x = vertex[0] * scale
    scaled_y = vertex[1] * scale

    # Rotate around origin
    cos_rot = math.cos(rotation)
    sin_rot = math.sin(rotation)

    return (
        scaled_x * cos_rot - scaled_y * sin_rot,
        scaled_x * sin_rot + scaled_y * cos_rot,
    )


# Apply transformations to vertices
_a = _transform_pentagon_vertex(_pentagon_a, _scale, _basis_rotation)
_b = _transform_pentagon_vertex(_pentagon_b, _scale, _basis_rotation)
_c = _transform_pentagon_vertex(_pentagon_c, _scale, _basis_rotation)
_d = _transform_pentagon_vertex(_pentagon_d, _scale, _basis_rotation)
_e = _transform_pentagon_vertex(_pentagon_e, _scale, _basis_rotation)

# Define triangle vertices (UVW)
_u = (0.0, 0.0)
_L = DISTANCE_TO_EDGE / math.cos(PI_OVER_5)

_bisector_angle = math.atan2(_c[1], _c[0]) - PI_OVER_5
_V = _bisector_angle + PI_OVER_5
_v = (_L * math.cos(_V), _L * math.sin(_V))

_W = _bisector_angle - PI_OVER_5
_w = (_L * math.cos(_W), _L * math.sin(_W))

# Pentagon BASIS matrices for proper lattice alignment
# These are used in the dodecahedron projection for correct coordinate transformations
BASIS = ((_v[0], _w[0]), (_v[1], _w[1]))

# Calculate matrix inverse manually for 2x2 matrix
# For matrix [[a, b], [c, d]], inverse is [[d, -b], [-c, a]] / (ad - bc)
_det = BASIS[0][0] * BASIS[1][1] - BASIS[0][1] * BASIS[1][0]
BASIS_INVERSE = (
    (BASIS[1][1] / _det, -BASIS[0][1] / _det),
    (-BASIS[1][0] / _det, BASIS[0][0] / _det),
)

# Pentagon vertices (after transformation)
PENTAGON_VERTICES = (_a, _b, _c, _d, _e)

# Triangle vertices (after transformation)
TRIANGLE_VERTICES = (_u, _v, _w)

# Quintant rotation matrices (5 rotations for 5 quintants)
TWO_PI_OVER_5 = 2 * math.pi / 5
QUINTANT_ROTATIONS = [
    (
        (math.cos(TWO_PI_OVER_5 * quintant), -math.sin(TWO_PI_OVER_5 * quintant)),
        (math.sin(TWO_PI_OVER_5 * quintant), math.cos(TWO_PI_OVER_5 * quintant)),
    )
    for quintant in range(5)
]
