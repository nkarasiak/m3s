"""
Coordinate Reference System (CRS) vertices for the A5 dodecahedron projection.

Ported from Felix Palmer's a5-py implementation.
"""

import math
from typing import List, Tuple

from m3s.a5.constants import DISTANCE_TO_EDGE, DISTANCE_TO_VERTEX
from m3s.a5.projections.origin_data import origins
from m3s.a5.projections import vec3_utils as vec3


Cartesian = Tuple[float, float, float]


def _to_cartesian(spherical: Tuple[float, float]) -> Cartesian:
    """Convert spherical coordinates to Cartesian."""
    theta, phi = spherical
    x = math.sin(phi) * math.cos(theta)
    y = math.sin(phi) * math.sin(theta)
    z = math.cos(phi)
    return (x, y, z)


class CRS:
    """
    The CRS is a fixed set of 62 vertices used as a rigid frame of reference:
    - 12 face centers
    - 20 vertices
    - 30 edge midpoints
    """

    def __init__(self) -> None:
        self._vertices: List[Cartesian] = []
        self._invocations = 0

        self._add_face_centers()  # 12 centers
        self._add_vertices()  # 20 vertices
        self._add_midpoints()  # 30 midpoints

        if len(self._vertices) != 62:
            raise ValueError(
                f"Failed to construct CRS: vertices length is {len(self._vertices)}, not 62"
            )

        # Make vertices read-only
        self._vertices = tuple(self._vertices)

    @property
    def vertices(self) -> List[Cartesian]:
        """Get the list of vertices (for testing access)."""
        return list(self._vertices)

    def get_vertex(self, point: Cartesian) -> Cartesian:
        """Find the CRS vertex that matches the given point."""
        self._invocations += 1
        if self._invocations == 10000:
            print("Too many CRS invocations, results should be cached")

        for vertex in self._vertices:
            dx = point[0] - vertex[0]
            dy = point[1] - vertex[1]
            dz = point[2] - vertex[2]
            distance = math.sqrt(dx * dx + dy * dy + dz * dz)
            if distance < 1e-5:
                return vertex

        raise ValueError("Failed to find vertex in CRS")

    def _add_face_centers(self) -> None:
        """Add face centers to vertices."""
        for origin in origins:
            cartesian_center = _to_cartesian(origin.axis)
            self._add(cartesian_center)

    def _add_vertices(self) -> None:
        """Add dodecahedron vertices to the CRS."""
        phi_vertex = math.atan(DISTANCE_TO_VERTEX)

        for origin in origins:
            for i in range(5):
                theta_vertex = (2 * i + 1) * math.pi / 5
                spherical_vertex = (theta_vertex + origin.angle, phi_vertex)
                vertex = list(_to_cartesian(spherical_vertex))
                vec3.transformQuat(vertex, vertex, origin.quat)
                self._add(vertex)

    def _add_midpoints(self) -> None:
        """Add edge midpoints to the CRS."""
        phi_midpoint = math.atan(DISTANCE_TO_EDGE)

        for origin in origins:
            for i in range(5):
                theta_midpoint = (2 * i) * math.pi / 5
                spherical_midpoint = (theta_midpoint + origin.angle, phi_midpoint)
                midpoint = list(_to_cartesian(spherical_midpoint))
                vec3.transformQuat(midpoint, midpoint, origin.quat)
                self._add(midpoint)

    def _add(self, new_vertex: Cartesian) -> bool:
        """Add a new vertex if it doesn't already exist."""
        normalized = vec3.normalize(vec3.create(), new_vertex)

        for existing_vertex in self._vertices:
            distance = vec3.distance(normalized, existing_vertex)
            if distance < 1e-5:
                return False

        self._vertices.append(normalized)
        return True
