"""
Pentagon geometry for A5 grid system.

This module provides the PentagonShape class for pentagon transformations
and operations used in the A5 grid tiling.

Ported from Palmer's a5-py/a5/geometry/pentagon.py and a5/core/pentagon.py
"""

import math
from typing import List, Tuple

from m3s.a5 import vec2
from m3s.a5.constants import (
    BASIS_ROTATION,
    DISTANCE_TO_EDGE,
    PI_OVER_5,
    PI_OVER_10,
)

# Type alias for face coordinates
Face = Tuple[float, float]
Pentagon = List[Face]


# ============================================================================
# Pentagon Vertex Definitions (from Palmer's a5/core/pentagon.py)
# ============================================================================

# Pentagon vertex angles
A = 72.0  # degrees
B = 127.94543761193603  # degrees
C = 108.0  # degrees
D = 82.29202980963508  # degrees
E = 149.7625318412527  # degrees

# Initialize vertices before transformations
a = (0.0, 0.0)
b = (0.0, 1.0)
# c & d calculated by circle intersections
c = (0.7885966681787006, 1.6149108024237764)
d = (1.6171013659387945, 1.054928690397459)
e = (math.cos(PI_OVER_10), math.sin(PI_OVER_10))

# Distance to edge midpoint
c_norm = math.sqrt(c[0] * c[0] + c[1] * c[1])
edge_midpoint_d = 2 * c_norm * math.cos(PI_OVER_5)

# Scale to match unit sphere
scale = 2 * DISTANCE_TO_EDGE / edge_midpoint_d


def transform_vertex(vertex: Face, scale_factor: float, rotation: float) -> Face:
    """
    Apply scale and rotation to a vertex.

    Parameters
    ----------
    vertex : Face
        The vertex to transform
    scale_factor : float
        Scaling factor
    rotation : float
        Rotation angle in radians

    Returns
    -------
    Face
        Transformed vertex
    """
    # Scale
    scaled_x = vertex[0] * scale_factor
    scaled_y = vertex[1] * scale_factor

    # Rotate around origin
    cos_rot = math.cos(rotation)
    sin_rot = math.sin(rotation)

    return (
        scaled_x * cos_rot - scaled_y * sin_rot,
        scaled_x * sin_rot + scaled_y * cos_rot,
    )


# Apply transformations to vertices
a = transform_vertex(a, scale, BASIS_ROTATION)
b = transform_vertex(b, scale, BASIS_ROTATION)
c = transform_vertex(c, scale, BASIS_ROTATION)
d = transform_vertex(d, scale, BASIS_ROTATION)
e = transform_vertex(e, scale, BASIS_ROTATION)

# Triangle vertices (UVW)
u = (0.0, 0.0)
L = DISTANCE_TO_EDGE / math.cos(PI_OVER_5)

bisector_angle = math.atan2(c[1], c[0]) - PI_OVER_5

V = bisector_angle + PI_OVER_5
v = (L * math.cos(V), L * math.sin(V))

W = bisector_angle - PI_OVER_5
w = (L * math.cos(W), L * math.sin(W))


# ============================================================================
# PentagonShape Class
# ============================================================================


class PentagonShape:
    """
    Pentagon shape with transformation operations.

    This class represents a pentagon as a list of 2D face coordinates
    and provides methods for geometric transformations used in the A5 tiling.
    """

    def __init__(self, vertices: Pentagon):
        """
        Initialize pentagon with vertices.

        Parameters
        ----------
        vertices : Pentagon
            List of (x, y) tuples representing pentagon vertices
        """
        self.vertices = list(vertices)  # Make a copy to avoid mutating original
        if not self._is_winding_correct():
            self.vertices.reverse()

    def get_area(self) -> float:
        """
        Calculate the signed area of the pentagon using the shoelace formula.

        Returns
        -------
        float
            Signed area (positive for counter-clockwise winding)
        """
        signed_area = 0.0
        n = len(self.vertices)
        for i in range(n):
            j = (i + 1) % n
            signed_area += (self.vertices[j][0] - self.vertices[i][0]) * (
                self.vertices[j][1] + self.vertices[i][1]
            )
        return signed_area

    def _is_winding_correct(self) -> bool:
        """
        Check if the pentagon has counter-clockwise winding (positive area).

        Returns
        -------
        bool
            True if counter-clockwise
        """
        return self.get_area() >= 0

    def get_vertices(self) -> Pentagon:
        """
        Get the vertices of the pentagon.

        Returns
        -------
        Pentagon
            List of vertices
        """
        return self.vertices

    def scale(self, scale_factor: float) -> "PentagonShape":
        """
        Scale the pentagon by the given factor.

        Parameters
        ----------
        scale_factor : float
            Scaling factor

        Returns
        -------
        PentagonShape
            Self (for chaining)
        """
        for i, vertex in enumerate(self.vertices):
            self.vertices[i] = (vertex[0] * scale_factor, vertex[1] * scale_factor)
        return self

    def rotate180(self) -> "PentagonShape":
        """
        Rotate the pentagon 180 degrees (equivalent to negating x & y).

        Returns
        -------
        PentagonShape
            Self (for chaining)
        """
        for i, vertex in enumerate(self.vertices):
            self.vertices[i] = (-vertex[0], -vertex[1])
        return self

    def reflect_y(self) -> "PentagonShape":
        """
        Reflect the pentagon over the x-axis (negate y).

        Also reverses the winding order to maintain consistent orientation.

        Returns
        -------
        PentagonShape
            Self (for chaining)
        """
        # First reflect all vertices
        for i, vertex in enumerate(self.vertices):
            self.vertices[i] = (vertex[0], -vertex[1])

        # Then reverse the winding order to maintain consistent orientation
        self.vertices.reverse()

        return self

    def translate(self, translation: Tuple[float, float]) -> "PentagonShape":
        """
        Translate the pentagon by the given vector.

        Parameters
        ----------
        translation : Tuple[float, float]
            Translation vector (dx, dy)

        Returns
        -------
        PentagonShape
            Self (for chaining)
        """
        for i, vertex in enumerate(self.vertices):
            self.vertices[i] = (
                vertex[0] + translation[0],
                vertex[1] + translation[1],
            )
        return self

    def transform(
        self, transform: Tuple[Tuple[float, float], Tuple[float, float]]
    ) -> "PentagonShape":
        """
        Apply a 2x2 transformation matrix to the pentagon.

        Parameters
        ----------
        transform : Tuple[Tuple[float, float], Tuple[float, float]]
            2x2 matrix as ((a, b), (c, d))

        Returns
        -------
        PentagonShape
            Self (for chaining)
        """
        for i, vertex in enumerate(self.vertices):
            # Manual matrix multiplication: transform @ vertex
            new_x = transform[0][0] * vertex[0] + transform[0][1] * vertex[1]
            new_y = transform[1][0] * vertex[0] + transform[1][1] * vertex[1]
            self.vertices[i] = (new_x, new_y)
        return self

    def transform2d(
        self, transform: Tuple[Tuple[float, float, float], Tuple[float, float, float]]
    ) -> "PentagonShape":
        """
        Apply a 2x3 transformation matrix to the pentagon.

        Parameters
        ----------
        transform : Tuple[Tuple[float, float, float], Tuple[float, float, float]]
            2x3 affine matrix

        Returns
        -------
        PentagonShape
            Self (for chaining)
        """
        for i, vertex in enumerate(self.vertices):
            # Manual matrix multiplication for 2x3 matrix
            new_x = (
                transform[0][0] * vertex[0]
                + transform[0][1] * vertex[1]
                + transform[0][2]
            )
            new_y = (
                transform[1][0] * vertex[0]
                + transform[1][1] * vertex[1]
                + transform[1][2]
            )
            self.vertices[i] = (new_x, new_y)
        return self

    def clone(self) -> "PentagonShape":
        """
        Create a deep copy of the pentagon.

        Returns
        -------
        PentagonShape
            A new pentagon with copied vertices
        """
        return PentagonShape([vertex for vertex in self.vertices])

    def get_center(self) -> Face:
        """
        Get the center point of the pentagon (centroid).

        Returns
        -------
        Face
            Center coordinates (x, y)
        """
        n = len(self.vertices)
        sum_x = sum(v[0] for v in self.vertices) / n
        sum_y = sum(v[1] for v in self.vertices) / n
        return (sum_x, sum_y)

    def contains_point(self, point: Tuple[float, float]) -> float:
        """
        Test if a point is inside the pentagon.

        Uses edge cross-product tests assuming counter-clockwise winding.

        Parameters
        ----------
        point : Tuple[float, float]
            The point to test

        Returns
        -------
        float
            1 if point is inside, otherwise a negative value proportional
            to the distance from the point to the edge
        """
        if not self._is_winding_correct():
            raise ValueError("Pentagon is not counter-clockwise")

        n = len(self.vertices)
        d_max = 1
        for i in range(n):
            v1 = self.vertices[i]
            v2 = self.vertices[(i + 1) % n]

            # Calculate the cross product to determine which side of the line
            # the point is on: (v1 - v2) × (point - v1)
            dx = v1[0] - v2[0]
            dy = v1[1] - v2[1]
            px = point[0] - v1[0]
            py = point[1] - v1[1]

            # Cross product: dx * py - dy * px
            cross_product = dx * py - dy * px
            if cross_product < 0:
                # Normalize by distance of point to edge
                p_length = math.sqrt(px * px + py * py)
                d_max = min(d_max, cross_product / p_length)

        return d_max

    def split_edges(self, segments: int) -> "PentagonShape":
        """
        Split each edge of the pentagon into the specified number of segments.

        Parameters
        ----------
        segments : int
            Number of segments to split each edge into

        Returns
        -------
        PentagonShape
            A new PentagonShape with more vertices, or the original if segments <= 1
        """
        if segments <= 1:
            return self

        new_vertices = []
        n = len(self.vertices)

        for i in range(n):
            v1 = self.vertices[i]
            v2 = self.vertices[(i + 1) % n]

            # Add the current vertex
            new_vertices.append(v1)

            # Add interpolated points along the edge (excluding the endpoints)
            for j in range(1, segments):
                t = j / segments
                interpolated = vec2.create()
                vec2.lerp(interpolated, v1, v2, t)
                new_vertices.append((interpolated[0], interpolated[1]))

        return PentagonShape(new_vertices)


# Export the template pentagon and triangle shapes
PENTAGON = PentagonShape([a, b, c, d, e])
TRIANGLE = PentagonShape([u, v, w])

# Export individual vertices for reference
__all__ = [
    "PentagonShape",
    "PENTAGON",
    "TRIANGLE",
    "a",
    "b",
    "c",
    "d",
    "e",
    "u",
    "v",
    "w",
    "V",
    "Face",
    "Pentagon",
]
