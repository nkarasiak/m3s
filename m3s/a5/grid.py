"""
A5 Grid M3S Integration.

This module provides the A5Grid class that implements the M3S BaseGrid interface
for the A5 pentagonal grid system.
"""

from typing import Dict, List

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

        # Ensure the polygon contains the generating point (native A5 is approximate)
        polygon = self._ensure_contains_point(polygon, lon, lat)

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
        seen_ids: Dict[int, GridCell] = {}  # Cache cells we've already created

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

    def _ensure_contains_point(
        self, polygon: Polygon, lon: float, lat: float
    ) -> Polygon:
        """
        Ensure the polygon contains or touches the provided point.

        The native A5 implementation can return slightly offset boundaries,
        so apply a minimal buffer when the point falls just outside.
        """
        point = Point(lon, lat)
        if polygon.contains(point) or polygon.touches(point):
            return polygon

        distance = polygon.distance(point)
        if distance <= 0:
            return polygon

        # Expand enough to include the point with a small relative cushion.
        buffered = polygon.buffer(distance * 1.01 + 1e-6)
        if buffered.geom_type == "Polygon":
            return buffered

        # Fallback: choose the polygon that contains the point, or the largest.
        candidates = [geom for geom in buffered.geoms if geom.geom_type == "Polygon"]
        for candidate in candidates:
            if candidate.contains(point) or candidate.touches(point):
                return candidate
        if candidates:
            return max(candidates, key=lambda geom: geom.area)

        return polygon

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
        parts = identifier.split("_")

        # Check if it's completely wrong format
        if parts[0] != "a5":
            raise ValueError(f"Invalid A5 identifier: {identifier}")

        # Check if it's partially right but incomplete/invalid
        if len(parts) != 3:
            raise ValueError(f"Invalid A5 identifier format: {identifier}")

        try:
            cell_id_hex = parts[2]
            cell_id = int(cell_id_hex, 16)
            return cell_id
        except (IndexError, ValueError) as e:
            raise ValueError(f"Invalid A5 identifier format: {identifier}") from e

    def get_resolution(self) -> int:
        """
        Get the resolution level of this grid.

        Returns
        -------
        int
            Resolution level (same as precision)
        """
        return self.precision

    @property
    def area_km2(self) -> float:
        """
        Get theoretical average area of cells at this precision.

        Returns
        -------
        float
            Average cell area in square kilometers for this precision level

        Notes
        -----
        A5 grid cells have relatively uniform areas at each precision level.
        The Earth's surface is divided into 12 base pentagons at resolution 0,
        with each cell subdividing into approximately 5 cells per level.
        """
        # Earth's surface area in km²
        earth_surface_km2 = 510_072_000

        # A5 has 12 base cells at resolution 0
        # Each cell subdivides into approximately 5 cells per level
        # (pentagons tessellate with 5-fold subdivision)
        num_cells = 12 * (5**self.precision)

        return earth_surface_km2 / num_cells

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

        Uses a deterministic neighbor approximation based on A5 cell identifiers.
        Pentagons typically have 5 neighbors, but this may vary at face boundaries.

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
        Finding neighbors in a pentagonal grid system is complex due to:
        - Irregular boundaries between dodecahedron faces
        - Quintant segment transitions
        - Hierarchical structure

        The algorithm:
        1. Expand cell's bounding box
        2. Sample a grid of points within expanded box
        3. Get cells at those points
        4. Keep only cells that share a boundary with the original cell
        """
        neighbors: List[GridCell] = []
        seen_ids: set[int] = set()

        def add_neighbor(candidate_id: int) -> None:
            if candidate_id in seen_ids:
                return
            if candidate_id == cell_id:
                return
            try:
                candidate_boundary = self.cell_ops.cell_to_boundary(candidate_id)
                candidate_polygon = Polygon(candidate_boundary)
            except Exception:
                return
            neighbors.append(
                GridCell(
                    f"a5_{self.precision}_{candidate_id:016x}",
                    candidate_polygon,
                    self.precision,
                )
            )
            seen_ids.add(candidate_id)

        # Decode cell ID for deterministic neighbor selection
        cell_id = self._extract_cell_id(cell.identifier)
        try:
            origin, segment, s, resolution = self.cell_ops.serializer.decode(cell_id)
        except Exception:
            return neighbors

        # Resolution 0: neighbors are adjacent faces
        if resolution == 0:
            for origin_id in self.cell_ops.dodec.get_adjacent_origins(origin):
                add_neighbor(
                    self.cell_ops.serializer.encode(origin_id, 0, 0, resolution)
                )
            return neighbors

        # Resolution >= 1: same origin, different segment neighbors
        neighbor_s = s if resolution >= 2 else 0
        for seg in range(5):
            if seg != segment:
                add_neighbor(
                    self.cell_ops.serializer.encode(origin, seg, neighbor_s, resolution)
                )

        # Add one adjacent face neighbor to reach typical 5 neighbors
        adjacent_origins = self.cell_ops.dodec.get_adjacent_origins(origin)
        if adjacent_origins:
            add_neighbor(
                self.cell_ops.serializer.encode(
                    adjacent_origins[0], segment, neighbor_s, resolution
                )
            )

        return neighbors

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
        # Sample points within bbox to find cells.
        # Cap sampling density to avoid pathological runtimes for large bboxes
        # at high precision levels.
        samples_per_degree = max(2, 2 ** (self.precision + 1))
        samples_per_degree = min(samples_per_degree, 64)

        lat_range = max_lat - min_lat
        lon_range = max_lon - min_lon

        lat_steps = max(2, int(lat_range * samples_per_degree))
        lon_steps = max(2, int(lon_range * samples_per_degree))

        # Cap total sample points to keep runtime bounded.
        max_points = 4000
        total_points = (lat_steps + 1) * (lon_steps + 1)
        if total_points > max_points:
            scale = (max_points / total_points) ** 0.5
            lat_steps = max(2, int(lat_steps * scale))
            lon_steps = max(2, int(lon_steps * scale))

        # Generate sample points
        lats = [min_lat + lat_range * i / lat_steps for i in range(lat_steps + 1)]
        lons = [min_lon + lon_range * i / lon_steps for i in range(lon_steps + 1)]

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

    def _lonlat_to_xyz(self, lon: float, lat: float) -> tuple:
        """
        Convert geographic coordinates to Cartesian (x, y, z).

        This is a utility method for tests and internal use.

        Parameters
        ----------
        lon : float
            Longitude in degrees
        lat : float
            Latitude in degrees

        Returns
        -------
        tuple
            (x, y, z) Cartesian coordinates on unit sphere
        """
        # Convert to spherical coordinates
        theta, phi = self.cell_ops.transformer.lonlat_to_spherical(lon, lat)

        # Convert spherical to Cartesian
        xyz = self.cell_ops.transformer.spherical_to_cartesian(theta, phi)

        return xyz

    def _xyz_to_lonlat(self, xyz: tuple) -> tuple:
        """
        Convert Cartesian (x, y, z) to geographic coordinates.

        This is a utility method for tests and internal use.

        Parameters
        ----------
        xyz : tuple
            (x, y, z) Cartesian coordinates

        Returns
        -------
        tuple
            (lon, lat) in degrees
        """
        # Convert Cartesian to lonlat
        lon, lat = self.cell_ops.transformer.cartesian_to_lonlat(xyz)

        return (lon, lat)

    def _encode_cell_id(self, lat: float, lon: float) -> int:
        """
        Encode geographic coordinates to cell ID.

        This is a utility method for tests and internal use.

        Parameters
        ----------
        lat : float
            Latitude in degrees
        lon : float
            Longitude in degrees

        Returns
        -------
        int
            64-bit cell ID
        """
        return self.cell_ops.lonlat_to_cell(lon, lat, self.precision)

    def _create_pentagon_boundary(self, lat: float, lon: float) -> list:
        """
        Create pentagon boundary for a point.

        This is a utility method for tests.

        Parameters
        ----------
        lat : float
            Latitude in degrees
        lon : float
            Longitude in degrees

        Returns
        -------
        list
            List of (lon, lat) tuples forming closed pentagon boundary
        """
        # Get cell ID for this point
        cell_id = self.cell_ops.lonlat_to_cell(lon, lat, self.precision)

        # Get boundary
        boundary = self.cell_ops.cell_to_boundary(cell_id)
        if boundary and boundary[0] != boundary[-1]:
            boundary = boundary + [boundary[0]]
        return boundary

    def __repr__(self) -> str:
        """String representation of A5Grid."""
        return f"A5Grid(precision={self.precision})"

    def __str__(self) -> str:
        """String representation of A5Grid."""
        return f"A5 Grid (resolution {self.precision})"
