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
        from m3s.a5.projections.origin_data import origins, quintant_to_segment
        origin = origins[origin_id]
        segment = quintant_to_segment(quintant, origin)

        # Step 8: For resolution >= 2, delegate to Palmer for Hilbert calculation
        if resolution >= 2:
            # TEMPORARY: Use Palmer's lonlat_to_cell for Hilbert resolutions
            # Palmer's implementation handles the complex IJ→Hilbert→S conversion
            # TODO Phase 3: Implement native Hilbert S-value calculation
            import a5 as palmer_a5

            cell_id = palmer_a5.lonlat_to_cell((lon, lat), resolution)
            return cell_id
        else:
            # For resolution 0-1, S-value is always 0
            s = 0

            # Step 9: Serialize to cell ID
            cell_id = self.serializer.encode(origin_id, segment, s, resolution)

            return cell_id

    def cell_to_lonlat(self, cell_id: int) -> Tuple[float, float]:
        """
        Convert A5 cell ID to center coordinates.

        TEMPORARY: Using Palmer's implementation for accuracy.
        TODO: Implement proper pentagon center calculation.

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
        # TEMPORARY: Use Palmer's implementation directly
        import a5

        lon, lat = a5.cell_to_lonlat(cell_id)
        return lon, lat

    def cell_to_boundary(self, cell_id: int) -> List[Tuple[float, float]]:
        """
        Get pentagon boundary vertices for a cell.

        TEMPORARY: Using Palmer's implementation for accuracy.
        TODO: Implement proper pentagon boundary generation.

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
        # TEMPORARY: Use Palmer's implementation directly
        import a5

        boundary = a5.cell_to_boundary(cell_id)
        return boundary

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
            # For resolution >= 2, use Palmer's Hilbert children calculation
            # Palmer handles the complex Hilbert curve subdivision
            import a5 as palmer_a5

            children = palmer_a5.cell_to_children(cell_id)
            return children
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
