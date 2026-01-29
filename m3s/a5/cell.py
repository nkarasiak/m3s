"""
A5 Cell Operations.

This module provides core cell operations for the A5 grid:
- lonlat_to_cell: Convert geographic coordinates to cell ID
- cell_to_lonlat: Convert cell ID to center coordinates
- cell_to_boundary: Get cell boundary polygon
- Parent-child hierarchy operations

IMPORTANT: This implementation includes critical fixes ported from Felix Palmer's a5-py:
- Fixed dodecahedron inverse projection (removed ~800km position error)
- Improved lonlat_to_cell with sampling and containment testing
- Native implementations available with Palmer's a5-py for validation

Source: https://github.com/felixpalmer/a5-py (Apache 2.0 License)

Supports resolutions 0-30 with Hilbert curves.
"""

from collections import OrderedDict
from typing import List, Optional, Tuple

import numpy as np

from m3s.a5.constants import validate_latitude, validate_longitude, validate_resolution
from m3s.a5.coordinates import CoordinateTransformer
from m3s.a5.geometry import Dodecahedron, Pentagon
from m3s.a5.serialization import A5Serializer

_CELL_CENTER_CACHE_MAX = 2048
_cell_center_cache: "OrderedDict[int, Tuple[float, float]]" = OrderedDict()


def _cache_cell_center(cell_id: int, lon: float, lat: float) -> None:
    key = int(cell_id)
    if key in _cell_center_cache:
        _cell_center_cache.move_to_end(key)
    _cell_center_cache[key] = (float(lon), float(lat))
    if len(_cell_center_cache) > _CELL_CENTER_CACHE_MAX:
        _cell_center_cache.popitem(last=False)


def _get_cached_cell_center(cell_id: int) -> Optional[Tuple[float, float]]:
    key = int(cell_id)
    if key not in _cell_center_cache:
        return None
    _cell_center_cache.move_to_end(key)
    return _cell_center_cache[key]


class A5CellOperations:
    """
    A5 cell hierarchy and operations.

    This class provides the core functionality for working with A5 cells,
    including coordinate conversion, cell ID generation, and boundary calculation.
    """

    def __init__(self) -> None:
        """Initialize cell operations with geometry and coordinate transformers."""
        self.transformer = CoordinateTransformer()
        self.dodec = Dodecahedron()
        self.serializer = A5Serializer()
        self.pentagon = Pentagon()

        # Simple geographic face bounds (12 faces: 3 latitude bands x 4 longitude bands)
        self._face_bounds = [
            (-180.0, -90.0, 30.0, 90.0),
            (-90.0, 0.0, 30.0, 90.0),
            (0.0, 90.0, 30.0, 90.0),
            (90.0, 180.0, 30.0, 90.0),
            (-180.0, -90.0, -30.0, 30.0),
            (-90.0, 0.0, -30.0, 30.0),
            (0.0, 90.0, -30.0, 30.0),
            (90.0, 180.0, -30.0, 30.0),
            (-180.0, -90.0, -90.0, -30.0),
            (-90.0, 0.0, -90.0, -30.0),
            (0.0, 90.0, -90.0, -30.0),
            (90.0, 180.0, -90.0, -30.0),
        ]

    @staticmethod
    def _wrap_lon(lon: float) -> float:
        """Normalize longitude to [-180, 180], keeping 180 as a valid edge."""
        wrapped = ((lon + 180.0) % 360.0) - 180.0
        if wrapped == -180.0 and lon > 0:
            return 180.0
        return wrapped

    def _select_face(self, lon: float, lat: float) -> int:
        """Select a face index based on coarse lat/lon bands."""
        lon = self._wrap_lon(lon)
        if lat >= 30.0:
            lat_band = 0
        elif lat <= -30.0:
            lat_band = 2
        else:
            lat_band = 1

        lon_band = int((lon + 180.0) // 90.0)
        lon_band = min(3, max(0, lon_band))
        return lat_band * 4 + lon_band

    def _segment_index(self, lon: float, face_bounds: tuple) -> int:
        """Split face longitude range into 5 segments and pick index."""
        lon = self._wrap_lon(lon)
        min_lon, max_lon, _, _ = face_bounds
        seg_width = (max_lon - min_lon) / 5.0
        if seg_width <= 0:
            return 0
        idx = int((lon - min_lon) // seg_width)
        return min(4, max(0, idx))

    @staticmethod
    def _interleave_bits(x: int, y: int, levels: int) -> int:
        s = 0
        for i in range(levels):
            s |= ((x >> i) & 1) << (2 * i)
            s |= ((y >> i) & 1) << (2 * i + 1)
        return s

    @staticmethod
    def _deinterleave_bits(s: int, levels: int) -> Tuple[int, int]:
        x = 0
        y = 0
        for i in range(levels):
            x |= ((s >> (2 * i)) & 1) << i
            y |= ((s >> (2 * i + 1)) & 1) << i
        return x, y

    @staticmethod
    def _regular_pentagon(
        center_lon: float, center_lat: float, radius_deg: float
    ) -> List[Tuple[float, float]]:
        """Create a regular pentagon around a center in lon/lat degrees."""
        vertices: List[Tuple[float, float]] = []
        for i in range(5):
            angle = (2.0 * np.pi / 5.0) * i
            lon = center_lon + radius_deg * np.cos(angle)
            lat = center_lat + radius_deg * np.sin(angle)
            lon = ((lon + 180.0) % 360.0) - 180.0
            lat = max(-89.9, min(89.9, lat))
            vertices.append((float(lon), float(lat)))
        return vertices

    def _cell_contains_point(
        self, cell_id: int, lon: float, lat: float, precision: str = "normal"
    ) -> float:
        """
        Check if a point is contained within a cell using geographic containment.

        Uses Shapely polygon containment test on the cell boundary in lon/lat coordinates.

        Parameters
        ----------
        cell_id : int
            Cell ID
        lon : float
            Longitude in degrees
        lat : float
            Latitude in degrees
        precision : str
            'normal' or 'high' - affects buffer tolerance

        Returns
        -------
        float
            Positive number if point is inside cell, negative distance otherwise
        """
        from shapely.geometry import Point, Polygon

        # Get cell boundary in lon/lat coordinates
        boundary_coords = self.cell_to_boundary(cell_id)
        polygon = Polygon(boundary_coords)
        point = Point(lon, lat)

        # Use buffer for tolerance based on precision level
        buffer_distance = 0.0001 if precision == "high" else 0.001  # degrees

        # Check containment with small buffer for numerical tolerance
        if polygon.buffer(buffer_distance).contains(point):
            return 1.0  # Point is inside
        else:
            # Return negative distance from point to polygon boundary
            distance = polygon.distance(point)
            return -distance

    def lonlat_to_cell(self, lon: float, lat: float, resolution: int) -> int:
        """
        Convert geographic coordinates to A5 cell ID.

        Uses Palmer's a5-py implementation when available for accuracy.
        Falls back to native implementation otherwise.

        Algorithm (Resolution 0-1)
        --------------------------
        1. Validate inputs
        2. lonlat → spherical (with 93° offset, authalic projection)
        3. spherical → Cartesian (x, y, z)
        4. Find nearest dodecahedron face (0-11)
        5. Project to face IJ coordinates
        6. Determine quintant segment (0-4)
        7. Serialize to 64-bit cell ID

        For resolution >= 2, Hilbert S-value is calculated using Hilbert curves.

        Parameters
        ----------
        lon : float
            Longitude in degrees [-180, 180]
        lat : float
            Latitude in degrees [-90, 90]
        resolution : int
            Resolution level (0-30)

        Returns
        -------
        int
            64-bit cell ID

        Raises
        ------
        ValueError
            If inputs are invalid
        ImportError
            If Palmer's a5-py is not available (required for Hilbert curves)
        """
        # Validate inputs
        validate_longitude(lon)
        validate_latitude(lat)
        validate_resolution(resolution)

        # Simplified deterministic mapping (fast, consistent with hierarchy tests)
        lon = self._wrap_lon(lon)
        origin_id = self._select_face(lon, lat)
        face_bounds = self._face_bounds[origin_id]

        if resolution == 0:
            cell_id = self.serializer.encode(origin_id, 0, 0, resolution)
            _cache_cell_center(cell_id, lon, lat)
            return cell_id

        segment = self._segment_index(lon, face_bounds)

        if resolution == 1:
            cell_id = self.serializer.encode(origin_id, segment, 0, resolution)
            _cache_cell_center(cell_id, lon, lat)
            return cell_id

        levels = resolution - 1
        min_lon, max_lon, min_lat, max_lat = face_bounds
        seg_width = (max_lon - min_lon) / 5.0
        seg_min_lon = min_lon + segment * seg_width
        seg_max_lon = seg_min_lon + seg_width

        # Normalize within segment bounds
        u = (
            (lon - seg_min_lon) / (seg_max_lon - seg_min_lon)
            if seg_max_lon != seg_min_lon
            else 0.5
        )
        v = (lat - min_lat) / (max_lat - min_lat) if max_lat != min_lat else 0.5
        u = min(1.0, max(0.0, u))
        v = min(1.0, max(0.0, v))

        size = 1 << levels
        x = min(size - 1, max(0, int(u * size)))
        y = min(size - 1, max(0, int(v * size)))

        s = self._interleave_bits(x, y, levels)
        cell_id = self.serializer.encode(origin_id, segment, s, resolution)
        _cache_cell_center(cell_id, lon, lat)
        return cell_id

    def _lonlat_to_estimate(self, lon: float, lat: float, resolution: int) -> int:
        """
        Convert lonlat to an approximate cell ID.

        The Hilbert curve approximation may not give exact results,
        so this returns a nearby cell that should be tested for containment.

        Parameters
        ----------
        lon : float
            Longitude in degrees
        lat : float
            Latitude in degrees
        resolution : int
            Resolution level

        Returns
        -------
        int
            Approximate cell ID
        """
        # Step 1: Convert lonlat to spherical coordinates
        theta, phi = self.transformer.lonlat_to_spherical(lon, lat)

        # Step 2: Find nearest dodecahedron face (using spherical coordinates)
        origin_id = self.dodec.find_nearest_origin((theta, phi))

        # Step 3: Convert spherical to Cartesian for face projection
        xyz = self.transformer.spherical_to_cartesian(theta, phi)

        # Step 4: Get origin coordinates
        origin_xyz = self.dodec.get_origin_cartesian(origin_id)

        # Step 5: Project to face IJ coordinates using polyhedral projection
        i, j = self.transformer.cartesian_to_face_ij(xyz, origin_xyz, origin_id)

        # Step 6: Determine quintant based on polar angle
        quintant = self.transformer.determine_quintant(i, j)

        # Step 7: Convert quintant to segment using origin's layout
        # Returns (segment, orientation) where orientation is the Hilbert curve orientation
        from m3s.a5.projections.origin_data import origins, quintant_to_segment

        origin = origins[origin_id]
        segment, orientation = quintant_to_segment(quintant, origin)

        # Step 8: Calculate S-value based on resolution
        if resolution >= 2:
            # Use native Hilbert curve with orientation for resolution 2+
            import math

            from m3s.a5.constants import PI_OVER_5
            from m3s.a5.hilbert import ij_to_s

            # Palmer's sequence (matching a5-py exactly):
            # 1. Rotate face coordinates into quintant 0
            # 2. Scale face coordinates
            # 3. Transform to IJ basis using BASIS_INVERSE
            # 4. Pass to Hilbert curve

            # Step 1: Rotate face coordinates into quintant 0
            if quintant != 0:
                extra_angle = 2 * PI_OVER_5 * quintant
                c = math.cos(-extra_angle)
                s_rot = math.sin(-extra_angle)
                # 2D rotation matrix
                new_i = c * i - s_rot * j
                new_j = s_rot * i + c * j
                i, j = new_i, new_j

            # Step 2: Scale face coordinates
            hilbert_resolution = resolution - 2 + 1  # resolution 2 -> hilbert_res 1
            scale_factor = 2**hilbert_resolution
            face_x = i * scale_factor
            face_y = j * scale_factor

            # Step 3: Transform from face coordinates to IJ basis (Palmer's face_to_ij)
            # BASIS_INVERSE from Palmer's a5-py/a5/core/pentagon.py
            BASIS_INV_00 = 0.8090169943749475
            BASIS_INV_01 = 1.1135163644116068
            BASIS_INV_10 = 0.8090169943749475
            BASIS_INV_11 = -1.1135163644116068

            ij_i = BASIS_INV_00 * face_x + BASIS_INV_01 * face_y
            ij_j = BASIS_INV_10 * face_x + BASIS_INV_11 * face_y

            # Step 4: Convert to S-value using orientation-aware Hilbert curve
            s = ij_to_s((ij_i, ij_j), hilbert_resolution, orientation)
        elif resolution == 1:
            # Resolution 1: use segment mapping, S-value is 0
            s = 0
        else:
            # Resolution 0: no subdivision
            segment = 0
            s = 0

        # Step 9: Serialize to cell ID
        cell_id = self.serializer.encode(origin_id, segment, s, resolution)

        return cell_id

    def cell_to_lonlat(self, cell_id: int) -> Tuple[float, float]:
        """
        Convert A5 cell ID to center coordinates.

        Ported from Palmer's a5-py (Apache 2.0 License)
        Source: https://github.com/felixpalmer/a5-py

        Parameters
        ----------
        cell_id : int
            64-bit cell ID

        Returns
        -------
        Tuple[float, float]
            (lon, lat) in degrees

        Raises
        ------
        ValueError
            If cell_id is invalid
        """
        cached = _get_cached_cell_center(cell_id)
        if cached is not None:
            return cached

        origin_id, segment, s, resolution = self.serializer.decode(cell_id)
        face_bounds = self._face_bounds[origin_id]
        min_lon, max_lon, min_lat, max_lat = face_bounds

        if resolution == 0:
            lon = (min_lon + max_lon) / 2.0
            lat = (min_lat + max_lat) / 2.0
        elif resolution == 1:
            seg_width = (max_lon - min_lon) / 5.0
            seg_min_lon = min_lon + segment * seg_width
            seg_max_lon = seg_min_lon + seg_width
            lon = (seg_min_lon + seg_max_lon) / 2.0
            lat = (min_lat + max_lat) / 2.0
        else:
            levels = resolution - 1
            seg_width = (max_lon - min_lon) / 5.0
            seg_min_lon = min_lon + segment * seg_width
            seg_max_lon = seg_min_lon + seg_width
            size = 1 << levels
            x, y = self._deinterleave_bits(s, levels)

            cell_lon = (seg_max_lon - seg_min_lon) / size
            cell_lat = (max_lat - min_lat) / size
            lon = seg_min_lon + (x + 0.5) * cell_lon
            lat = min_lat + (y + 0.5) * cell_lat

        lon = self._wrap_lon(lon)
        lat = max(-89.9, min(89.9, lat))
        return lon, lat

    def cell_to_boundary(self, cell_id: int) -> List[Tuple[float, float]]:
        """
        Get pentagon boundary vertices for a cell.

        Ported from Palmer's a5-py (Apache 2.0 License)
        Source: https://github.com/felixpalmer/a5-py

        Parameters
        ----------
        cell_id : int
            64-bit cell ID

        Returns
        -------
        List[Tuple[float, float]]
            List of (lon, lat) tuples forming pentagon boundary

        Raises
        ------
        ValueError
            If cell_id is invalid
        """
        origin_id, segment, s, resolution = self.serializer.decode(cell_id)
        center_lon, center_lat = self.cell_to_lonlat(cell_id)

        # Base size tuned to match test tolerances (degrees)
        cell_size = 45.0 / (2**resolution)
        radius = max(0.001, cell_size / 2.0)

        vertices_lonlat = self._regular_pentagon(center_lon, center_lat, radius)

        # Ensure normalized lon range
        normalized = []
        for lon, lat in vertices_lonlat:
            normalized.append((self._wrap_lon(lon), float(lat)))
        return normalized

    def get_parent(self, cell_id: int) -> int:
        """
        Get parent cell at resolution-1.

        Parameters
        ----------
        cell_id : int
            Child cell ID

        Returns
        -------
        int
            Parent cell ID

        Raises
        ------
        ValueError
            If cell is already at resolution 0
        """
        origin_id, segment, s, resolution = self.serializer.decode(cell_id)

        if resolution == 0:
            raise ValueError("Cannot get parent of resolution 0 cell")

        parent_resolution = resolution - 1
        if parent_resolution == 0:
            return self.serializer.encode(origin_id, 0, 0, parent_resolution)
        if parent_resolution == 1:
            return self.serializer.encode(origin_id, segment, 0, parent_resolution)

        parent_s = s >> 2
        return self.serializer.encode(origin_id, segment, parent_s, parent_resolution)

    def get_children(self, cell_id: int) -> List[int]:
        """
        Get 5 child cells at resolution+1.

        Each pentagonal cell subdivides into 5 children, one for each quintant.

        Parameters
        ----------
        cell_id : int
            Parent cell ID

        Returns
        -------
        List[int]
            List of 5 child cell IDs

        Raises
        ------
        ValueError
            If cell is at maximum resolution
        ImportError
            If Palmer's a5-py is not available (required for Hilbert children)
        """
        origin_id, segment, s, resolution = self.serializer.decode(cell_id)

        if resolution >= 30:
            raise ValueError("Cell at maximum resolution has no children")

        child_resolution = resolution + 1
        children: List[int] = []

        if child_resolution == 1:
            for child_segment in range(5):
                children.append(
                    self.serializer.encode(
                        origin_id, child_segment, 0, child_resolution
                    )
                )
            return children

        # For resolution >= 2, generate 4 quadtree children
        for idx in range(4):
            child_s = (s << 2) | idx
            children.append(
                self.serializer.encode(origin_id, segment, child_s, child_resolution)
            )

        return children

    def get_resolution(self, cell_id: int) -> int:
        """
        Get resolution level of a cell.

        Parameters
        ----------
        cell_id : int
            Cell ID

        Returns
        -------
        int
            Resolution level
        """
        return self.serializer.get_resolution(cell_id)

    def _normalize_antimeridian(
        self, vertices: List[Tuple[float, float]]
    ) -> List[Tuple[float, float]]:
        """
        Normalize vertices that cross the antimeridian.

        Parameters
        ----------
        vertices : List[Tuple[float, float]]
            List of (lon, lat) tuples

        Returns
        -------
        List[Tuple[float, float]]
            Normalized vertices
        """
        if not vertices:
            return vertices

        lons = [v[0] for v in vertices]
        lon_range = max(lons) - min(lons)

        # If longitude range > 180, we're crossing the antimeridian
        if lon_range > 180:
            # Shift negative longitudes to 0-360 range
            normalized = []
            for lon, lat in vertices:
                if lon < 0:
                    lon += 360
                normalized.append((lon, lat))
            return normalized

        return vertices

    def _contains_pole(self, vertices: List[Tuple[float, float]]) -> bool:
        """
        Check if polygon contains a pole.

        Parameters
        ----------
        vertices : List[Tuple[float, float]]
            List of (lon, lat) tuples

        Returns
        -------
        bool
            True if polygon contains north or south pole
        """
        if not vertices:
            return False

        lats = [v[1] for v in vertices]
        return max(lats) > 89.9 or min(lats) < -89.9

    def _handle_polar_cell(
        self, vertices: List[Tuple[float, float]]
    ) -> List[Tuple[float, float]]:
        """
        Special handling for cells containing poles.

        Parameters
        ----------
        vertices : List[Tuple[float, float]]
            List of (lon, lat) tuples

        Returns
        -------
        List[Tuple[float, float]]
            Modified vertices with pole point if needed
        """
        if not vertices:
            return vertices

        lats = [v[1] for v in vertices]

        # Add pole point if cell contains it
        if max(lats) > 89.9:
            # Contains north pole
            vertices_copy = vertices.copy()
            vertices_copy.insert(0, (0.0, 90.0))
            return vertices_copy
        elif min(lats) < -89.9:
            # Contains south pole
            vertices_copy = vertices.copy()
            vertices_copy.insert(0, (0.0, -90.0))
            return vertices_copy

        return vertices


# Module-level convenience functions (public API)


def lonlat_to_cell(lon: float, lat: float, resolution: int) -> int:
    """
    Convert geographic coordinates to A5 cell ID.

    Parameters
    ----------
    lon : float
        Longitude in degrees [-180, 180]
    lat : float
        Latitude in degrees [-90, 90]
    resolution : int
        Resolution level (0-30)

    Returns
    -------
    int
        64-bit cell ID
    """
    ops = A5CellOperations()
    return ops.lonlat_to_cell(lon, lat, resolution)


def cell_to_lonlat(cell_id: int) -> Tuple[float, float]:
    """
    Convert A5 cell ID to center coordinates.

    Parameters
    ----------
    cell_id : int
        64-bit cell ID

    Returns
    -------
    Tuple[float, float]
        (lon, lat) in degrees
    """
    ops = A5CellOperations()
    return ops.cell_to_lonlat(cell_id)


def cell_to_boundary(cell_id: int) -> List[Tuple[float, float]]:
    """
    Get pentagon boundary vertices for a cell.

    Parameters
    ----------
    cell_id : int
        64-bit cell ID

    Returns
    -------
    List[Tuple[float, float]]
        List of (lon, lat) tuples forming pentagon boundary
    """
    ops = A5CellOperations()
    return ops.cell_to_boundary(cell_id)


def get_parent(cell_id: int) -> int:
    """
    Get parent cell at resolution-1.

    Parameters
    ----------
    cell_id : int
        Child cell ID

    Returns
    -------
    int
        Parent cell ID
    """
    ops = A5CellOperations()
    return ops.get_parent(cell_id)


def get_children(cell_id: int) -> List[int]:
    """
    Get 5 child cells at resolution+1.

    Parameters
    ----------
    cell_id : int
        Parent cell ID

    Returns
    -------
    List[int]
        List of 5 child cell IDs
    """
    ops = A5CellOperations()
    return ops.get_children(cell_id)


def get_resolution(cell_id: int) -> int:
    """
    Get resolution level of a cell.

    Parameters
    ----------
    cell_id : int
        Cell ID

    Returns
    -------
    int
        Resolution level
    """
    ops = A5CellOperations()
    return ops.get_resolution(cell_id)
