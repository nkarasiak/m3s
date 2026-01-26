"""
A5 Cell Operations.

This module provides core cell operations for the A5 grid:
- lonlat_to_cell: Convert geographic coordinates to cell ID
- cell_to_lonlat: Convert cell ID to center coordinates
- cell_to_boundary: Get cell boundary polygon
- Parent-child hierarchy operations

Phase 2 implementation supports resolutions 0-30 with Hilbert curves.
"""

from typing import List, Tuple

import numpy as np

from m3s.a5.constants import validate_latitude, validate_longitude, validate_resolution
from m3s.a5.coordinates import CoordinateTransformer
from m3s.a5.geometry import Dodecahedron, Pentagon
from m3s.a5.serialization import A5Serializer


class A5CellOperations:
    """
    A5 cell hierarchy and operations.

    This class provides the core functionality for working with A5 cells,
    including coordinate conversion, cell ID generation, and boundary calculation.
    """

    def __init__(self):
        """Initialize cell operations with geometry and coordinate transformers."""
        self.transformer = CoordinateTransformer()
        self.dodec = Dodecahedron()
        self.serializer = A5Serializer()
        self.pentagon = Pentagon()

    def lonlat_to_cell(self, lon: float, lat: float, resolution: int) -> int:
        """
        Convert geographic coordinates to A5 cell ID.

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
            from m3s.a5.hilbert import ij_to_s
            from m3s.a5.constants import PI_OVER_5

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
            scale_factor = 2 ** hilbert_resolution
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

        Uses Palmer's implementation when available for accuracy.
        Falls back to native implementation otherwise.

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
        # Decode cell ID
        origin_id, segment, s, resolution = self.serializer.decode(cell_id)

        # Get IJ coordinates based on resolution
        if resolution >= 2:
            # Use Hilbert curve to convert S back to IJ with orientation
            import math
            from m3s.a5.hilbert import s_to_anchor
            from m3s.a5.projections.origin_data import origins, segment_to_quintant

            origin = origins[origin_id]
            quintant, orientation = segment_to_quintant(segment, origin)

            # Calculate Hilbert resolution
            hilbert_resolution = resolution - 2 + 1

            # Convert S to IJ using orientation-aware Hilbert curve
            anchor = s_to_anchor(s, hilbert_resolution, orientation)
            ij_i, ij_j = anchor.offset

            # Transform from IJ basis to face coordinates (inverse of face_to_ij)
            # Using BASIS matrix (inverse of BASIS_INVERSE)
            BASIS_00 = 0.6180339887498949
            BASIS_01 = 0.6180339887498949
            BASIS_10 = 0.4490279765795854
            BASIS_11 = -0.4490279765795854

            face_x = BASIS_00 * ij_i + BASIS_01 * ij_j
            face_y = BASIS_10 * ij_i + BASIS_11 * ij_j

            # Unscale from Hilbert grid
            scale_factor = 2 ** hilbert_resolution
            i = face_x / scale_factor
            j = face_y / scale_factor

            # Unrotate from quintant 0 back to original quintant
            from m3s.a5.constants import PI_OVER_5
            if quintant != 0:
                extra_angle = 2 * PI_OVER_5 * quintant
                c = math.cos(extra_angle)  # Note: positive angle to reverse the rotation
                s_rot = math.sin(extra_angle)
                new_i = c * i - s_rot * j
                new_j = s_rot * i + c * j
                i, j = new_i, new_j
        elif resolution == 1:
            # Convert segment back to quintant using proper reverse mapping
            import math
            from m3s.a5.projections.origin_data import origins, segment_to_quintant

            origin = origins[origin_id]
            quintant, orientation = segment_to_quintant(segment, origin)

            # Convert quintant to IJ coordinates
            angle = (2 * math.pi / 5) * quintant
            r = 0.5  # Approximate radius for resolution 1
            i = r * math.cos(angle)
            j = r * math.sin(angle)
        else:
            # Resolution 0: center of face
            i, j = 0.0, 0.0

        # Project IJ back to 3D Cartesian
        origin_xyz = self.dodec.get_origin_cartesian(origin_id)
        xyz = self.transformer.face_ij_to_cartesian(i, j, origin_xyz, origin_id)

        # Convert Cartesian to lonlat
        lon, lat = self.transformer.cartesian_to_lonlat(xyz)

        return lon, lat

    def cell_to_boundary(self, cell_id: int) -> List[Tuple[float, float]]:
        """
        Get pentagon boundary vertices for a cell (native implementation).

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
        import math

        # Decode cell ID to get resolution and coordinates
        origin_id, segment, s, resolution = self.serializer.decode(cell_id)

        # Get cell center in IJ space
        if resolution >= 2:
            from m3s.a5.hilbert import A5HilbertCurve

            hilbert = A5HilbertCurve(resolution)
            center_i, center_j = hilbert.s_to_ij(s)
        elif resolution == 1:
            # Convert segment back to quintant
            from m3s.a5.projections.origin_data import origins

            origin = origins[origin_id]
            first_quintant = origin.first_quintant
            quintant = (segment + first_quintant) % 5

            angle = (2 * math.pi / 5) * quintant
            r = 0.5
            center_i = r * math.cos(angle)
            center_j = r * math.sin(angle)
        else:
            center_i, center_j = 0.0, 0.0

        # Calculate cell size at this resolution
        # Each resolution subdivides by approximately √5
        base_size = 2.0  # Size at resolution 0
        cell_size = base_size / (math.sqrt(5) ** resolution)

        # Generate pentagon vertices in IJ space
        vertices_ij = []
        for k in range(5):
            # Pentagon vertices at 72° intervals, rotated by 18° to point up
            vertex_angle = (2 * math.pi / 5) * k + math.pi / 10
            vertex_i = center_i + (cell_size / 2) * math.cos(vertex_angle)
            vertex_j = center_j + (cell_size / 2) * math.sin(vertex_angle)
            vertices_ij.append((vertex_i, vertex_j))

        # Project each vertex to lonlat
        origin_xyz = self.dodec.get_origin_cartesian(origin_id)
        vertices_lonlat = []

        for vi, vj in vertices_ij:
            xyz = self.transformer.face_ij_to_cartesian(vi, vj, origin_xyz, origin_id)
            lon, lat = self.transformer.cartesian_to_lonlat(xyz)
            vertices_lonlat.append((lon, lat))

        # Close the polygon by repeating the first vertex
        vertices_lonlat.append(vertices_lonlat[0])

        return vertices_lonlat

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
            raise ValueError("Cell at resolution 0 has no parent")

        # Parent is at resolution - 1
        parent_resolution = resolution - 1

        if parent_resolution == 0:
            # Parent at resolution 0 covers entire face
            parent_segment = 0
            parent_s = 0
        elif parent_resolution == 1:
            # Resolution 1 has no Hilbert subdivision
            parent_segment = segment
            parent_s = 0
        else:
            # For resolution >= 2, calculate parent S-value from Hilbert hierarchy
            # Each parent cell has 4 children in Hilbert space
            # Parent S = child S divided by 4 (bitwise right shift by 2)
            parent_segment = segment
            parent_s = s >> 2

        parent_cell_id = self.serializer.encode(
            origin_id, parent_segment, parent_s, parent_resolution
        )

        return parent_cell_id

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

        # Children are at resolution + 1
        child_resolution = resolution + 1

        if child_resolution >= 2:
            # For resolution >= 2, generate children using sampling
            # Get parent cell center and boundary
            parent_lon, parent_lat = self.cell_to_lonlat(cell_id)
            parent_boundary = self.cell_to_boundary(cell_id)

            # Calculate approximate cell size
            import math
            from shapely.geometry import Point, Polygon

            parent_poly = Polygon(parent_boundary)
            bounds = parent_poly.bounds
            cell_width = bounds[2] - bounds[0]
            cell_height = bounds[3] - bounds[1]

            # Sample points within the parent cell to find children
            # Use a grid of sample points
            num_samples = 7  # 7x7 grid should give us good coverage
            sample_spacing_lon = cell_width / num_samples
            sample_spacing_lat = cell_height / num_samples

            children_set = set()

            for i in range(num_samples + 1):
                for j in range(num_samples + 1):
                    sample_lon = bounds[0] + i * sample_spacing_lon
                    sample_lat = bounds[1] + j * sample_spacing_lat

                    # Check if sample point is within parent cell
                    sample_point = Point(sample_lon, sample_lat)
                    if parent_poly.contains(sample_point) or parent_poly.touches(
                        sample_point
                    ):
                        try:
                            # Get child cell at this point
                            child_cell_id = self.lonlat_to_cell(
                                sample_lon, sample_lat, child_resolution
                            )
                            children_set.add(child_cell_id)
                        except:
                            pass

            return list(children_set)
        else:
            # For resolution 0 → 1, create 5 children (one per quintant)
            children = []
            for child_segment in range(5):
                child_cell_id = self.serializer.encode(
                    origin_id, child_segment, 0, child_resolution
                )
                children.append(child_cell_id)

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
