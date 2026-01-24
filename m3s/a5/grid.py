"""
A5 Grid M3S Integration.

This module provides the A5Grid class that implements the M3S BaseGrid interface
for the A5 pentagonal grid system.
"""

from typing import List

from shapely.geometry import Point, Polygon

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
    Phase 2 implementation supports all resolutions 0-30 with Hilbert curves.
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
        validate_resolution(precision)

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

        # Get boundary polygon
        boundary_coords = self.cell_ops.cell_to_boundary(cell_id)

        # Create Shapely polygon
        polygon = Polygon(boundary_coords)

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
        boundary_coords = self.cell_ops.cell_to_boundary(cell_id)

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
        Get 5 child cells at precision+1.

        Each pentagonal cell subdivides into 5 children.

        Parameters
        ----------
        cell : GridCell
            Parent cell

        Returns
        -------
        List[GridCell]
            List of 5 child cells

        Raises
        ------
        ValueError
            If cell is at maximum precision
        NotImplementedError
            If precision >= 2 (Phase 3)
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
        try:
            parts = identifier.split("_")
            if len(parts) != 3 or parts[0] != "a5":
                raise ValueError(f"Invalid A5 cell identifier: {identifier}")

            cell_id_hex = parts[2]
            cell_id = int(cell_id_hex, 16)
            return cell_id

        except (IndexError, ValueError) as e:
            raise ValueError(f"Invalid A5 cell identifier: {identifier}") from e

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

        Raises
        ------
        NotImplementedError
            Neighbor finding for A5 will be implemented in Phase 3

        Notes
        -----
        Finding neighbors in a pentagonal grid system is complex due to:
        - Irregular boundaries between dodecahedron faces
        - Quintant segment transitions
        - Hierarchical structure

        This will be implemented properly in Phase 3 along with Hilbert curves.
        """
        raise NotImplementedError(
            "Neighbor finding for A5 grid will be implemented in Phase 3. "
            "For now, use spatial intersection methods to find adjacent cells."
        )

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
        This is a basic implementation for Phase 1-2. It samples points
        within the bounding box and collects unique cells.

        A more efficient implementation will be provided in Phase 3.
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
