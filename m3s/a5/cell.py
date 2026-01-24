"""
A5 Cell Operations.

This module provides core cell operations for the A5 grid:
- lonlat_to_cell: Convert geographic coordinates to cell ID
- cell_to_lonlat: Convert cell ID to center coordinates
- cell_to_boundary: Get cell boundary polygon
- Parent-child hierarchy operations

Resolutions 0+ are supported, including Hilbert curves for res >= 2.
"""

import math
from typing import Dict, List, Tuple

from m3s.a5.constants import (
    FIRST_HILBERT_RESOLUTION,
    MAX_RESOLUTION,
    validate_latitude,
    validate_longitude,
    validate_resolution,
)
from m3s.a5.coordinates import CoordinateTransformer
from m3s.a5.hilbert import ij_to_s, s_to_anchor
from m3s.a5.geometry import Dodecahedron
from m3s.a5.pentagon_shape import PentagonShape
from m3s.a5.projections.dodecahedron import DodecahedronProjection
from m3s.a5.projections.origin_data import origins, quintant_to_segment, segment_to_quintant
from m3s.a5.serialization import A5Serializer
from m3s.a5.tiling import (
    get_face_vertices,
    get_pentagon_vertices,
    get_quintant_vertices,
)


class A5CellOperations:
    """
    A5 cell hierarchy and operations.
    """

    def __init__(self):
        self.transformer = CoordinateTransformer()
        self.dodec = Dodecahedron(use_hilbert_order=True)
        self.serializer = A5Serializer()
        self.projection = DodecahedronProjection()

    def lonlat_to_cell(self, lon: float, lat: float, resolution: int) -> int:
        """
        Convert geographic coordinates to A5 cell ID.
        """
        self._validate_inputs(lon, lat, resolution)

        if resolution < FIRST_HILBERT_RESOLUTION:
            estimate = self._lonlat_to_estimate((lon, lat), resolution)
            return self.serializer.encode(
                estimate["origin"].id, estimate["segment"], estimate["S"], resolution
            )

        hilbert_resolution = 1 + resolution - FIRST_HILBERT_RESOLUTION
        samples = [(lon, lat)]
        n_samples = 25
        scale = 50 / (2**hilbert_resolution)

        for i in range(n_samples):
            radius = (i / n_samples) * scale
            coordinate = (
                math.cos(i) * radius + lon,
                math.sin(i) * radius + lat,
            )
            samples.append(coordinate)

        estimate_set = set()
        candidates: List[Dict[str, object]] = []

        for sample in samples:
            estimate = self._lonlat_to_estimate(sample, resolution)
            estimate_key = self.serializer.encode(
                estimate["origin"].id,
                estimate["segment"],
                estimate["S"],
                resolution,
            )
            if estimate_key in estimate_set:
                continue
            estimate_set.add(estimate_key)
            distance = self._cell_contains_point(estimate, (lon, lat))
            if distance > 0:
                return estimate_key
            candidates.append({"cell": estimate, "distance": distance})

        candidates.sort(key=lambda x: x["distance"], reverse=True)
        best_cell = candidates[0]["cell"]
        return self.serializer.encode(
            best_cell["origin"].id,
            best_cell["segment"],
            best_cell["S"],
            resolution,
        )

    def cell_to_lonlat(self, cell_id: int) -> Tuple[float, float]:
        """
        Convert A5 cell ID to center coordinates.
        """
        origin_id, segment, s, resolution = self.serializer.decode(cell_id)
        origin = origins[origin_id]

        cell = {
            "origin": origin,
            "segment": segment,
            "S": s,
            "resolution": resolution,
        }
        pentagon = self._get_pentagon(cell)
        face_center = pentagon.get_center()
        theta, phi = self.projection.inverse(face_center, origin_id)
        return self.transformer.spherical_to_lonlat(theta, phi)

    def cell_to_boundary(
        self, cell_id: int, segments: int | None = None
    ) -> List[Tuple[float, float]]:
        """
        Get pentagon boundary vertices for a cell.
        """
        origin_id, segment, s, resolution = self.serializer.decode(cell_id)
        origin = origins[origin_id]
        cell = {
            "origin": origin,
            "segment": segment,
            "S": s,
            "resolution": resolution,
        }

        if segments is None:
            segments = max(1, 2 ** (6 - resolution))
        pentagon = self._get_pentagon(cell)
        split_pentagon = pentagon.split_edges(segments)
        vertices = split_pentagon.get_vertices()

        unprojected_vertices = [
            self.projection.inverse(vertex, origin_id) for vertex in vertices
        ]
        boundary = [
            self.transformer.spherical_to_lonlat(theta, phi)
            for theta, phi in unprojected_vertices
        ]

        normalized = self.transformer.normalize_longitudes(boundary)
        if normalized and normalized[0] != normalized[-1]:
            normalized.append(normalized[0])
        normalized.reverse()
        return normalized

    def get_parent(self, cell_id: int) -> int:
        """
        Get parent cell at resolution-1.
        """
        origin_id, segment, s, resolution = self.serializer.decode(cell_id)

        if resolution == 0:
            raise ValueError("Cell at resolution 0 has no parent")

        parent_resolution = resolution - 1
        parent_segment = segment
        parent_s = s

        if parent_resolution == 0:
            parent_segment = 0
            parent_s = 0
        elif parent_resolution < FIRST_HILBERT_RESOLUTION:
            parent_s = 0
        else:
            resolution_diff = resolution - parent_resolution
            parent_s = s >> (2 * resolution_diff)

        return self.serializer.encode(
            origin_id, parent_segment, parent_s, parent_resolution
        )

    def get_children(self, cell_id: int) -> List[int]:
        """
        Get child cells at resolution+1.
        """
        origin_id, segment, s, resolution = self.serializer.decode(cell_id)

        if resolution >= MAX_RESOLUTION:
            raise ValueError("Cell at maximum resolution has no children")

        child_resolution = resolution + 1
        new_segments = [segment]

        if resolution == 0:
            new_segments = list(range(5))

        resolution_diff = child_resolution - max(resolution, FIRST_HILBERT_RESOLUTION - 1)
        children_count = 4 ** max(0, resolution_diff)
        shifted_s = s << (2 * max(0, resolution_diff))

        children = []
        for new_segment in new_segments:
            for i in range(children_count):
                new_s = shifted_s + i
                children.append(
                    self.serializer.encode(origin_id, new_segment, new_s, child_resolution)
                )
        return children

    def get_resolution(self, cell_id: int) -> int:
        """Get resolution level of a cell."""
        return self.serializer.get_resolution(cell_id)

    def _validate_inputs(self, lon: float, lat: float, resolution: int) -> None:
        validate_longitude(lon)
        validate_latitude(lat)
        validate_resolution(resolution)

    def _lonlat_to_estimate(self, lon_lat: Tuple[float, float], resolution: int) -> Dict:
        spherical = self.transformer.lonlat_to_spherical_unchecked(
            lon_lat[0], lon_lat[1]
        )
        origin_id = self.dodec.find_nearest_origin(spherical)
        origin = origins[origin_id]

        dodec_point = self.projection.forward(spherical, origin_id)
        quintant = self.transformer.determine_quintant(dodec_point[0], dodec_point[1])
        segment, orientation = quintant_to_segment(quintant, origin)

        if resolution < FIRST_HILBERT_RESOLUTION:
            return {
                "origin": origin,
                "segment": segment,
                "S": 0,
                "resolution": resolution,
            }

        if quintant != 0:
            extra_angle = 2 * math.pi / 5 * quintant
            c = math.cos(-extra_angle)
            s = math.sin(-extra_angle)
            new_x = c * dodec_point[0] - s * dodec_point[1]
            new_y = s * dodec_point[0] + c * dodec_point[1]
            dodec_point = (new_x, new_y)

        hilbert_resolution = 1 + resolution - FIRST_HILBERT_RESOLUTION
        scale_factor = 2**hilbert_resolution
        dodec_point = (dodec_point[0] * scale_factor, dodec_point[1] * scale_factor)

        ij = self.transformer.face_to_ij(dodec_point)
        s_val = ij_to_s(ij, hilbert_resolution, orientation)
        return {
            "origin": origin,
            "segment": segment,
            "S": s_val,
            "resolution": resolution,
        }

    def _get_pentagon(self, cell: Dict) -> PentagonShape:
        quintant, orientation = segment_to_quintant(cell["segment"], cell["origin"])
        if cell["resolution"] == (FIRST_HILBERT_RESOLUTION - 1):
            return get_quintant_vertices(quintant)
        if cell["resolution"] == (FIRST_HILBERT_RESOLUTION - 2):
            return get_face_vertices()

        hilbert_resolution = cell["resolution"] - FIRST_HILBERT_RESOLUTION + 1
        anchor = s_to_anchor(cell["S"], hilbert_resolution, orientation)
        return get_pentagon_vertices(hilbert_resolution, quintant, anchor)

    def _cell_contains_point(self, cell: Dict, point: Tuple[float, float]) -> float:
        pentagon = self._get_pentagon(cell)
        spherical = self.transformer.lonlat_to_spherical(point[0], point[1])
        projected_point = self.projection.forward(spherical, cell["origin"].id)
        return pentagon.contains_point(projected_point)


# Module-level convenience functions (public API)


def lonlat_to_cell(lon: float, lat: float, resolution: int) -> int:
    ops = A5CellOperations()
    return ops.lonlat_to_cell(lon, lat, resolution)


def cell_to_lonlat(cell_id: int) -> Tuple[float, float]:
    ops = A5CellOperations()
    return ops.cell_to_lonlat(cell_id)


def cell_to_boundary(
    cell_id: int, segments: int | None = None
) -> List[Tuple[float, float]]:
    ops = A5CellOperations()
    return ops.cell_to_boundary(cell_id, segments=segments)


def get_parent(cell_id: int) -> int:
    ops = A5CellOperations()
    return ops.get_parent(cell_id)


def get_children(cell_id: int) -> List[int]:
    ops = A5CellOperations()
    return ops.get_children(cell_id)


def get_resolution(cell_id: int) -> int:
    ops = A5CellOperations()
    return ops.get_resolution(cell_id)
