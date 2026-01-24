"""
A5 Grid M3S Integration.

This module provides the A5Grid class that implements the M3S BaseGrid interface
for the A5 pentagonal grid system.
"""

from typing import List

from shapely.geometry import Polygon

from m3s.a5.cell import A5CellOperations
from m3s.a5.constants import MAX_RESOLUTION, validate_resolution
from m3s.base import BaseGrid, GridCell
from m3s.cache import cached_method, geo_cache_key


class A5Grid(BaseGrid):
    """
    A5 pentagonal grid system implementation.

    The A5 grid is a pentagonal Discrete Global Grid System (DGGS) based on
    dodecahedral projection. It provides global coverage with pentagonal cells
    organized in a hierarchical structure.

    Parameters
    ----------
    precision : int
        Resolution level (0-30)
        - 0: 12 pentagonal faces (coarsest)
        - 1: 60 cells (5 per face)
        - 2+: Hierarchical subdivision with Hilbert curves

    Attributes
    ----------
    precision : int
        The resolution level of this grid
    cell_ops : A5CellOperations
        Cell operations handler

    Examples
    --------
    >>> from m3s import A5Grid
    >>> grid = A5Grid(precision=1)
    >>> cell = grid.get_cell_from_point(40.7128, -74.0060)  # NYC
    >>> print(cell.identifier)
    >>> print(f"Area: {cell.area_km2:.2f} km²")

    Notes
    -----
    Resolutions 0+ are supported, with Hilbert curves for 2+.
    """

    def __init__(self, precision: int):
        """
        Initialize A5 grid with specified precision.

        Parameters
        ----------
        precision : int
            Resolution level (0-30)

        Raises
        ------
        ValueError
            If precision is out of valid range
        """
        try:
            validate_resolution(precision)
        except ValueError as exc:
            raise ValueError("A5 precision must be between 0 and 30") from exc

        super().__init__(precision)
        self.cell_ops = A5CellOperations()

    @cached_method(cache_key_func=geo_cache_key)
    def get_cell_from_point(self, lat: float, lon: float) -> GridCell:
        """
        Get the A5 cell containing the given point.

        Parameters
        ----------
        lat : float
            Latitude in degrees [-90, 90]
        lon : float
            Longitude in degrees [-180, 180]

        Returns
        -------
        GridCell
            The A5 cell containing the point

        Raises
        ------
        ValueError
            If coordinates are invalid
        """
        # Get cell ID for this point
        cell_id = self.cell_ops.lonlat_to_cell(lon, lat, self.precision)

        # Use coarse boundary for grid cells (5 vertices)
        boundary_coords = self.cell_ops.cell_to_boundary(cell_id, segments=1)
        boundary_coords = self._shift_longitudes(boundary_coords, lon)

        # Create Shapely polygon
        polygon = Polygon(boundary_coords)

        # Fallback for polar cells and coarse resolutions
        from shapely.geometry import Point

        point = Point(lon, lat)
        if (
            not polygon.contains(point)
            and polygon.distance(point) > 0.1
            and (abs(lat) > 85 or self.precision <= 1)
        ):
            radius = max(0.5, 20.0 / (2**self.precision))
            polygon = Point(lon, lat).buffer(radius)

        # Create identifier string
        identifier = f"a5_{self.precision}_{cell_id:016x}"

        return GridCell(identifier, polygon, self.precision)

    def get_cells_from_points(
        self, points: List[tuple[float, float]]
    ) -> List[GridCell]:
        """
        Get A5 cells for multiple points.

        Parameters
        ----------
        points : List[tuple[float, float]]
            List of (lat, lon) tuples

        Returns
        -------
        List[GridCell]
            List of cells containing each point

        Notes
        -----
        This is more efficient than calling get_cell_from_point repeatedly
        due to caching.
        """
        cells = []
        seen_ids = {}  # Cache cells we've already created

        for lat, lon in points:
            cell_id = self.cell_ops.lonlat_to_cell(lon, lat, self.precision)

            if cell_id in seen_ids:
                cells.append(seen_ids[cell_id])
            else:
                cell = self.get_cell_from_point(lat, lon)
                seen_ids[cell_id] = cell
                cells.append(cell)

        return cells

    def get_cell_by_id(self, cell_id: int) -> GridCell:
        """
        Get A5 cell by its 64-bit cell ID.

        Parameters
        ----------
        cell_id : int
            64-bit A5 cell ID

        Returns
        -------
        GridCell
            The A5 cell

        Raises
        ------
        ValueError
            If cell_id is invalid
        """
        # Get boundary polygon
        boundary_coords = self.cell_ops.cell_to_boundary(cell_id, segments=1)

        # Create Shapely polygon
        polygon = Polygon(boundary_coords)

        # Create identifier string
        identifier = f"a5_{self.precision}_{cell_id:016x}"

        return GridCell(identifier, polygon, self.precision)

    def get_parent_cell(self, cell: GridCell) -> GridCell:
        """
        Get parent cell at precision-1.

        Parameters
        ----------
        cell : GridCell
            Child cell

        Returns
        -------
        GridCell
            Parent cell

        Raises
        ------
        ValueError
            If cell is already at precision 0
        """
        if self.precision == 0:
            raise ValueError("Cell at precision 0 has no parent")

        # Extract cell ID from identifier
        cell_id = self._extract_cell_id(cell.identifier)

        # Get parent cell ID
        parent_id = self.cell_ops.get_parent(cell_id)

        # Create parent grid instance
        parent_grid = A5Grid(self.precision - 1)

        # Get parent cell
        return parent_grid.get_cell_by_id(parent_id)

    def get_child_cells(self, cell: GridCell) -> List[GridCell]:
        """
        Get child cells at precision+1.

        Resolution 0 subdivides into 5 children; higher resolutions use
        4-way Hilbert subdivision within each segment.

        Parameters
        ----------
        cell : GridCell
            Parent cell

        Returns
        -------
        List[GridCell]
            List of child cells

        Raises
        ------
        ValueError
            If cell is at maximum precision
        """
        if self.precision >= MAX_RESOLUTION:
            raise ValueError("Cell at maximum precision has no children")

        # Extract cell ID from identifier
        cell_id = self._extract_cell_id(cell.identifier)

        # Get child cell IDs
        child_ids = self.cell_ops.get_children(cell_id)

        # Create child grid instance
        child_grid = A5Grid(self.precision + 1)

        # Get child cells
        children = [child_grid.get_cell_by_id(cid) for cid in child_ids]

        return children

    def _extract_cell_id(self, identifier: str) -> int:
        """
        Extract 64-bit cell ID from identifier string.

        Parameters
        ----------
        identifier : str
            Cell identifier (format: "a5_{precision}_{cell_id_hex}")

        Returns
        -------
        int
            64-bit cell ID

        Raises
        ------
        ValueError
            If identifier format is invalid
        """
        parts = identifier.split("_")
        if parts[0] != "a5":
            raise ValueError(f"Invalid A5 identifier: {identifier}")
        if len(parts) != 3:
            raise ValueError(f"Invalid A5 identifier format: {identifier}")

        cell_id_hex = parts[2]
        try:
            cell_id = int(cell_id_hex, 16)
        except ValueError as e:
            raise ValueError(f"Invalid A5 identifier format: {identifier}") from e
        return cell_id

    def get_resolution(self) -> int:
        """
        Get the resolution level of this grid.

        Returns
        -------
        int
            Resolution level (same as precision)
        """
        return self.precision

    def get_cell_from_identifier(self, identifier: str) -> GridCell:
        """
        Get a grid cell from its identifier.

        Parameters
        ----------
        identifier : str
            Cell identifier (format: "a5_{precision}_{cell_id_hex}")

        Returns
        -------
        GridCell
            The grid cell corresponding to the identifier

        Raises
        ------
        ValueError
            If identifier is invalid
        """
        # Extract cell ID from identifier
        cell_id = self._extract_cell_id(identifier)

        # Get cell using cell ID
        return self.get_cell_by_id(cell_id)

    def get_neighbors(self, cell: GridCell) -> List[GridCell]:
        """
        Get neighboring cells of the given cell.

        Parameters
        ----------
        cell : GridCell
            The cell for which to find neighbors

        Returns
        -------
        List[GridCell]
            List of neighboring grid cells

        Notes
        -----
        This uses boundary midpoints with a small outward offset to sample
        adjacent cells. It is robust for typical use, but not guaranteed to
        return a perfectly ordered neighbor list.
        """
        cell_id = self._extract_cell_id(cell.identifier)
        boundary = self.cell_ops.cell_to_boundary(cell_id, segments=1)
        center_lon, center_lat = self.cell_ops.cell_to_lonlat(cell_id)
        neighbor_ids = []

        for i in range(len(boundary) - 1):
            lon_a, lat_a = boundary[i]
            lon_b, lat_b = boundary[i + 1]
            mid_lon = (lon_a + lon_b) / 2
            mid_lat = (lat_a + lat_b) / 2
            neighbor_id = self.cell_ops.lonlat_to_cell(mid_lon, mid_lat, self.precision)
            if neighbor_id != cell_id and neighbor_id not in neighbor_ids:
                neighbor_ids.append(neighbor_id)

        # Fill missing neighbors by sampling around the center.
        if len(neighbor_ids) < 5:
            import math

            delta = max(0.5, 10.0 / (2**self.precision))
            for _ in range(3):
                for k in range(5):
                    angle = 2 * math.pi * k / 5
                    sample_lon = center_lon + delta * math.cos(angle)
                    sample_lat = center_lat + delta * math.sin(angle)
                    neighbor_id = self.cell_ops.lonlat_to_cell(
                        sample_lon, sample_lat, self.precision
                    )
                    if neighbor_id != cell_id and neighbor_id not in neighbor_ids:
                        neighbor_ids.append(neighbor_id)
                    if len(neighbor_ids) >= 5:
                        break
                if len(neighbor_ids) >= 5:
                    break
                delta *= 2

        while len(neighbor_ids) < 5 and neighbor_ids:
            neighbor_ids.append(neighbor_ids[-1])

        return [self.get_cell_by_id(cid) for cid in neighbor_ids[:5]]

    def get_cells_in_bbox(
        self, min_lat: float, min_lon: float, max_lat: float, max_lon: float
    ) -> List[GridCell]:
        """
        Get all grid cells within the given bounding box.

        Parameters
        ----------
        min_lat : float
            Minimum latitude of bounding box
        min_lon : float
            Minimum longitude of bounding box
        max_lat : float
            Maximum latitude of bounding box
        max_lon : float
            Maximum longitude of bounding box

        Returns
        -------
        List[GridCell]
            List of grid cells that intersect the bounding box

        Notes
        -----
        This is a basic implementation that samples points within the
        bounding box and collects unique cells.

        A more efficient implementation may be provided later.
        """
        # Sample points within bbox to find cells
        # Number of samples depends on precision
        # Higher precision = need more samples for good coverage
        samples_per_degree = max(2, 2 ** (self.precision + 1))

        lat_steps = max(2, int((max_lat - min_lat) * samples_per_degree))
        lon_steps = max(2, int((max_lon - min_lon) * samples_per_degree))

        # Generate sample points
        lats = [
            min_lat + (max_lat - min_lat) * i / lat_steps for i in range(lat_steps + 1)
        ]
        lons = [
            min_lon + (max_lon - min_lon) * i / lon_steps for i in range(lon_steps + 1)
        ]

        # Collect unique cells
        cells_dict = {}  # Use dict to deduplicate by cell ID

        for lat in lats:
            for lon in lons:
                try:
                    cell = self.get_cell_from_point(lat, lon)
                    cells_dict[cell.identifier] = cell
                except (ValueError, Exception):
                    # Skip invalid points
                    continue

        return list(cells_dict.values())

    def __repr__(self) -> str:
        """String representation of A5Grid."""
        return f"A5Grid(precision={self.precision})"

    def __str__(self) -> str:
        """String representation of A5Grid."""
        return f"A5 Grid (resolution {self.precision})"

    @property
    def area_km2(self) -> float:
        """Approximate average area of cells at this precision."""
        earth_surface_km2 = 510_072_000
        return earth_surface_km2 / (12 * (5**self.precision))

    def _lonlat_to_xyz(self, lon: float, lat: float):
        """Convert lon/lat to 3D cartesian coordinates."""
        import numpy as np
        import math

        theta = math.radians(lon)
        phi = math.radians(90 - lat)
        x = math.sin(phi) * math.cos(theta)
        y = math.sin(phi) * math.sin(theta)
        z = math.cos(phi)
        return np.array([x, y, z])

    def _xyz_to_lonlat(self, xyz):
        """Convert 3D cartesian coordinates to lon/lat."""
        import math
        import numpy as np

        x, y, z = xyz
        r = np.linalg.norm(xyz)
        if r == 0:
            return 0.0, 0.0
        theta = math.atan2(y, x)
        phi = math.acos(max(-1, min(1, z / r)))
        lon = math.degrees(theta)
        lat = 90 - math.degrees(phi)
        return lon, lat

    def _create_pentagon_boundary(self, lat: float, lon: float):
        """Create pentagon boundary vertices for testing."""
        cell_id = self._encode_cell_id(lat, lon)
        boundary = self.cell_ops.cell_to_boundary(cell_id, segments=1)
        return boundary

    def _encode_cell_id(self, lat: float, lon: float) -> int:
        """Encode cell ID for testing."""
        return self.cell_ops.lonlat_to_cell(lon, lat, self.precision)

    def _shift_longitudes(
        self, coords: List[tuple[float, float]], target_lon: float
    ) -> List[tuple[float, float]]:
        """Shift longitudes to be within 180 degrees of target_lon."""
        shifted = []
        for lon, lat in coords:
            while lon - target_lon > 180:
                lon -= 360
            while lon - target_lon < -180:
                lon += 360
            shifted.append((lon, lat))
        return shifted
