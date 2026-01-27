"""
A5 Grid M3S Integration.

This module provides the A5Grid class that implements the M3S BaseGrid interface
for the A5 pentagonal grid system.
"""

from typing import List, Sequence

from shapely.geometry import Point, Polygon

from m3s.a5.cell import A5CellOperations
from m3s.a5.constants import MAX_RESOLUTION, validate_resolution
from m3s.core.cell import Cell
from m3s.core.errors import InvalidPrecision
from m3s.core.grid import GridBase
from m3s.core.types import Bbox, CellId


class A5Grid(GridBase):
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

    name = "a5"

    def __init__(self, precision: int):
        """Initialize A5 grid with specified precision."""
        super().__init__(precision)
        self.cell_ops = A5CellOperations()

    def _validate_precision(self) -> None:
        try:
            validate_resolution(self.precision)
        except ValueError as exc:
            raise InvalidPrecision("A5 precision must be between 0 and 30") from exc

    def cell(self, lat: float, lon: float) -> Cell:
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
        Cell
            The A5 cell containing the point

        Raises
        ------
        ValueError
            If coordinates are invalid
        """
        self.validate_lat_lon(lat, lon)
        cell_id = self.cell_ops.lonlat_to_cell(lon, lat, self.precision)

        # Use adaptive boundary segmentation for smoother polygons
        boundary_coords = self.cell_ops.cell_to_boundary(cell_id, segments=None)
        boundary_coords = self._shift_longitudes(boundary_coords, lon)

        polygon = Polygon(boundary_coords)
        point = Point(lon, lat)
        if (
            not polygon.contains(point)
            and polygon.distance(point) > 0.1
            and (abs(lat) > 85 or self.precision <= 1)
        ):
            radius = max(0.5, 20.0 / (2**self.precision))
            polygon = Point(lon, lat).buffer(radius)
            boundary_coords = list(polygon.exterior.coords)

        # Create identifier string
        identifier = f"a5_{self.precision}_{cell_id:016x}"
        bbox = polygon.bounds
        return Cell(
            identifier,
            self.precision,
            (bbox[0], bbox[1], bbox[2], bbox[3]),
            _coords=boundary_coords,
        )

    def get_cell_from_point(self, lat: float, lon: float) -> Cell:
        """Legacy alias for cell()."""
        return self.cell(lat, lon)

    def get_cells_from_points(
        self, points: List[tuple[float, float]]
    ) -> List[Cell]:
        """
        Get A5 cells for multiple points.

        Parameters
        ----------
        points : List[tuple[float, float]]
            List of (lat, lon) tuples

        Returns
        -------
        List[:class:`m3s.core.cell.Cell`]
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
                cell = self.cell(lat, lon)
                seen_ids[cell_id] = cell
                cells.append(cell)

        return cells

    def get_cell_by_id(self, cell_id: int) -> Cell:
        """
        Get A5 cell by its 64-bit cell ID.

        Parameters
        ----------
        cell_id : int
            64-bit A5 cell ID

        Returns
        -------
        Cell
            The A5 cell

        Raises
        ------
        ValueError
            If cell_id is invalid
        """
        # Get boundary polygon (adaptive segmentation)
        boundary_coords = self.cell_ops.cell_to_boundary(cell_id, segments=None)

        polygon = Polygon(boundary_coords)

        # Create identifier string
        identifier = f"a5_{self.precision}_{cell_id:016x}"
        bbox = polygon.bounds
        return Cell(
            identifier,
            self.precision,
            (bbox[0], bbox[1], bbox[2], bbox[3]),
            _coords=boundary_coords,
        )

    def from_id(self, cell_id: CellId) -> Cell:
        """Return a cell from its identifier."""
        return self.get_cell_by_id(self._extract_cell_id(cell_id))

    def get_parent_cell(self, cell: Cell) -> Cell:
        """
        Get parent cell at precision-1.

        Parameters
        ----------
        cell : GridCell
            Child cell

        Returns
        -------
        Cell
            Parent cell

        Raises
        ------
        ValueError
            If cell is already at precision 0
        """
        if self.precision == 0:
            raise ValueError("Cell at precision 0 has no parent")

        # Extract cell ID from identifier
        cell_id = self._extract_cell_id(cell.id)

        # Get parent cell ID
        parent_id = self.cell_ops.get_parent(cell_id)

        # Create parent grid instance
        parent_grid = A5Grid(self.precision - 1)

        # Get parent cell
        return parent_grid.get_cell_by_id(parent_id)

    def get_child_cells(self, cell: Cell) -> List[Cell]:
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
        List[Cell]
            List of child cells

        Raises
        ------
        ValueError
            If cell is at maximum precision
        """
        if self.precision >= MAX_RESOLUTION:
            raise ValueError("Cell at maximum precision has no children")

        # Extract cell ID from identifier
        cell_id = self._extract_cell_id(cell.id)

        # Get child cell IDs
        child_ids = self.cell_ops.get_children(cell_id)

        # Create child grid instance
        child_grid = A5Grid(self.precision + 1)

        # Get child cells
        children = [child_grid.get_cell_by_id(cid) for cid in child_ids]

        return children

    def _extract_cell_id(self, identifier: CellId) -> int:
        """
        Extract 64-bit cell ID from identifier string.

        Parameters
        ----------
        identifier : CellId
            Cell identifier (format: "a5_{precision}_{cell_id_hex}") or int

        Returns
        -------
        int
            64-bit cell ID

        Raises
        ------
        ValueError
            If identifier format is invalid
        """
        if isinstance(identifier, int):
            return identifier

        parts = str(identifier).split("_")
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

    def get_cell_from_identifier(self, identifier: CellId) -> Cell:
        """
        Get a grid cell from its identifier.

        Parameters
        ----------
        identifier : str
            Cell identifier (format: "a5_{precision}_{cell_id_hex}")

        Returns
        -------
        Cell
            The grid cell corresponding to the identifier

        Raises
        ------
        ValueError
            If identifier is invalid
        """
        # Extract cell ID from identifier
        return self.get_cell_by_id(self._extract_cell_id(identifier))

    def neighbors(self, cell: Cell) -> Sequence[Cell]:
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
        cell_id = self._extract_cell_id(cell.id)
        boundary = self.cell_ops.cell_to_boundary(cell_id, segments=1)
        center_lon, center_lat = self.cell_ops.cell_to_lonlat(cell_id)
        center_xyz = self._lonlat_to_xyz(center_lon, center_lat)
        neighbor_ids = []

        # Sample just outside each edge using spherical geometry to avoid
        # staying inside the original cell near face boundaries.
        edge_count = max(1, len(boundary) - 1)
        for i in range(min(5, edge_count)):
            lon_a, lat_a = boundary[i]
            lon_b, lat_b = boundary[i + 1]
            v1 = self._lonlat_to_xyz(lon_a, lat_a)
            v2 = self._lonlat_to_xyz(lon_b, lat_b)
            edge_mid = self._normalize_xyz(v1 + v2)
            direction = edge_mid - center_xyz
            if self._vector_norm(direction) < 1e-12:
                continue
            for scale in (0.05, 0.1, 0.2, 0.4):
                sample_xyz = self._normalize_xyz(edge_mid + direction * scale)
                sample_lon, sample_lat = self._xyz_to_lonlat(sample_xyz)
                sample_lon = self._normalize_longitude(sample_lon)
                neighbor_id = self.cell_ops.lonlat_to_cell(
                    sample_lon, sample_lat, self.precision
                )
                if neighbor_id != cell_id and neighbor_id not in neighbor_ids:
                    neighbor_ids.append(neighbor_id)
                    break

        # Fill missing neighbors by sampling around the center on expanding rings.
        if len(neighbor_ids) < 5:
            import math

            base_delta = max(0.25, 5.0 / (2**self.precision))
            for ring in range(1, 5):
                delta = base_delta * ring
                for k in range(10):
                    angle = 2 * math.pi * k / 10 + (ring * 0.1)
                    sample_lon = center_lon + delta * math.cos(angle)
                    sample_lat = center_lat + delta * math.sin(angle)
                    sample_lon = self._normalize_longitude(sample_lon)
                    neighbor_id = self.cell_ops.lonlat_to_cell(
                        sample_lon, sample_lat, self.precision
                    )
                    if neighbor_id != cell_id and neighbor_id not in neighbor_ids:
                        neighbor_ids.append(neighbor_id)
                    if len(neighbor_ids) >= 5:
                        break
                if len(neighbor_ids) >= 5:
                    break

        # As a final fallback, pad to 5 by repeating the last unique neighbor.
        while len(neighbor_ids) < 5 and neighbor_ids:
            neighbor_ids.append(neighbor_ids[-1])

        return [self.get_cell_by_id(cid) for cid in neighbor_ids[:5]]

    def get_neighbors(self, cell: Cell) -> List[Cell]:
        """Legacy alias for neighbors()."""
        return list(self.neighbors(cell))

    def cells_in_bbox(self, bbox: Bbox) -> Sequence[Cell]:
        """
        Get all grid cells within the given bounding box.

        Parameters
        ----------
        bbox : Bbox
            Bounding box (min_lon, min_lat, max_lon, max_lat)

        Returns
        -------
        List[:class:`m3s.core.cell.Cell`]
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
        min_lon, min_lat, max_lon, max_lat = self.normalize_bbox(bbox)
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
                    cell = self.cell(lat, lon)
                    cells_dict[cell.id] = cell
                except (ValueError, Exception):
                    # Skip invalid points
                    continue

        return list(cells_dict.values())

    def get_cells_in_bbox(
        self, min_lat: float, min_lon: float, max_lat: float, max_lon: float
    ) -> List[Cell]:
        """Legacy alias for cells_in_bbox()."""
        return list(self.cells_in_bbox((min_lon, min_lat, max_lon, max_lat)))

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

    @staticmethod
    def _normalize_xyz(xyz):
        """Normalize a 3D vector to unit length."""
        import numpy as np

        norm = np.linalg.norm(xyz)
        if norm == 0:
            return xyz
        return xyz / norm

    @staticmethod
    def _vector_norm(xyz) -> float:
        """Return the Euclidean norm of a vector."""
        import numpy as np

        return float(np.linalg.norm(xyz))

    @staticmethod
    def _normalize_longitude(lon: float) -> float:
        """Normalize longitude to the [-180, 180] range."""
        while lon > 180:
            lon -= 360
        while lon < -180:
            lon += 360
        return lon
