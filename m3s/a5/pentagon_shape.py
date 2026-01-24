"""
Pentagon shape utilities for A5 tiling and boundary generation.

Ported from Felix Palmer's a5-py implementation.
"""

import math
from typing import List, Tuple

from m3s.a5.projections import vec2_utils as vec2

Face = Tuple[float, float]
Pentagon = List[Face]


class PentagonShape:
    """
    Simple polygon wrapper for pentagon vertices with winding correction.
    """

    def __init__(self, vertices: Pentagon):
        self.vertices = list(vertices)
        if not self._is_winding_correct():
            self.vertices.reverse()

    def get_area(self) -> float:
        """Signed polygon area using the shoelace formula."""
        signed_area = 0.0
        n = len(self.vertices)
        for i in range(n):
            j = (i + 1) % n
            signed_area += (self.vertices[j][0] - self.vertices[i][0]) * (
                self.vertices[j][1] + self.vertices[i][1]
            )
        return signed_area

    def _is_winding_correct(self) -> bool:
        """Check if the polygon has counter-clockwise winding."""
        return self.get_area() >= 0

    def get_vertices(self) -> Pentagon:
        """Return polygon vertices."""
        return self.vertices

    def scale(self, scale: float) -> "PentagonShape":
        """Scale vertices by a constant factor."""
        for i, vertex in enumerate(self.vertices):
            self.vertices[i] = (vertex[0] * scale, vertex[1] * scale)
        return self

    def rotate180(self) -> "PentagonShape":
        """Rotate the polygon 180 degrees around the origin."""
        for i, vertex in enumerate(self.vertices):
            self.vertices[i] = (-vertex[0], -vertex[1])
        return self

    def reflect_y(self) -> "PentagonShape":
        """
        Reflect over the x-axis (negate y) and reverse winding to keep orientation.
        """
        for i, vertex in enumerate(self.vertices):
            self.vertices[i] = (vertex[0], -vertex[1])
        self.vertices.reverse()
        return self

    def translate(self, translation: Tuple[float, float]) -> "PentagonShape":
        """Translate vertices by a vector."""
        for i, vertex in enumerate(self.vertices):
            self.vertices[i] = (vertex[0] + translation[0], vertex[1] + translation[1])
        return self

    def transform(
        self, transform: Tuple[Tuple[float, float], Tuple[float, float]]
    ) -> "PentagonShape":
        """Apply a 2x2 transformation matrix to all vertices."""
        for i, vertex in enumerate(self.vertices):
            new_x = transform[0][0] * vertex[0] + transform[0][1] * vertex[1]
            new_y = transform[1][0] * vertex[0] + transform[1][1] * vertex[1]
            self.vertices[i] = (new_x, new_y)
        return self

    def clone(self) -> "PentagonShape":
        """Deep copy."""
        return PentagonShape([vertex for vertex in self.vertices])

    def get_center(self) -> Face:
        """Centroid of polygon vertices."""
        n = len(self.vertices)
        sum_x = sum(v[0] for v in self.vertices) / n
        sum_y = sum(v[1] for v in self.vertices) / n
        return (sum_x, sum_y)

    def contains_point(self, point: Tuple[float, float]) -> float:
        """
        Test if a point is inside by checking edge-side consistency.

        Returns a positive number if contained, negative if outside.
        """
        if not self._is_winding_correct():
            raise ValueError("Pentagon winding is not counter-clockwise")

        n = len(self.vertices)
        d_max = 1
        for i in range(n):
            v1 = self.vertices[i]
            v2 = self.vertices[(i + 1) % n]
            dx = v1[0] - v2[0]
            dy = v1[1] - v2[1]
            px = point[0] - v1[0]
            py = point[1] - v1[1]
            cross_product = dx * py - dy * px
            if cross_product < 0:
                p_length = math.sqrt(px * px + py * py)
                d_max = min(d_max, cross_product / p_length)

        return d_max

    def split_edges(self, segments: int) -> "PentagonShape":
        """
        Split each edge into the specified number of segments.
        """
        if segments <= 1:
            return self

        new_vertices = []
        n = len(self.vertices)
        for i in range(n):
            v1 = self.vertices[i]
            v2 = self.vertices[(i + 1) % n]
            new_vertices.append(v1)
            for j in range(1, segments):
                t = j / segments
                interpolated = vec2.create()
                vec2.lerp(interpolated, v1, v2, t)
                new_vertices.append((interpolated[0], interpolated[1]))

        return PentagonShape(new_vertices)
