"""
S2 spatial grid implementation for M3S.

S2 is Google's spherical geometry library that provides hierarchical
decomposition of the sphere into cells. Each cell is uniquely identified
by a 64-bit S2CellId, with cells organized using the Hilbert curve for
optimal spatial locality.
"""

import warnings
from typing import override

import m3s_core
import s2sphere
from shapely.geometry import Polygon

from .base import BaseGrid, GridCell, cell_from_core


class S2Grid(BaseGrid):
    """
    S2 spatial grid implementation.

    Based on Google's S2 geometry library, this grid provides hierarchical
    decomposition of the sphere into cells. S2 uses a cube-to-sphere projection
    and the Hilbert curve to create a spatial index with excellent locality
    properties.

    Attributes
    ----------
    precision : int
        S2 cell precision (0-30), where higher values provide smaller cells
    """

    MIN_PRECISION = 0
    MAX_PRECISION = 30
    DEFAULT_PRECISION = 10

    def __init__(self, precision: int = 10):
        """
        Initialize S2 grid.

        Parameters
        ----------
        precision : int, optional
            S2 cell precision level (0-30), by default 10.
            Precision 0: ~85,000 km edge length
            Precision 10: ~1,300 km edge length
            Precision 20: ~20 m edge length
            Precision 30: ~1 cm edge length
        """
        if not self.MIN_PRECISION <= precision <= self.MAX_PRECISION:
            raise ValueError(
                f"S2 precision must be between {self.MIN_PRECISION} and "
                f"{self.MAX_PRECISION}"
            )

        super().__init__(precision)

    @property
    def area_km2(self) -> float:
        """
        Get the theoretical area of S2 cells at this level in square kilometers.

        Returns
        -------
        float
            Theoretical area in square kilometers for cells at this level
        """
        # S2 cells are roughly equal area due to spherical geometry
        # Earth's surface area: ~510 million km²
        earth_surface_km2 = 510_072_000.0

        # S2 has 6 root cells (one per cube face)
        # At each level, cells are divided into 4 children
        # Total cells at level L = 6 × 4^L
        total_cells = 6 * (4**self.precision)

        # Average area per cell
        return earth_surface_km2 / total_cells

    def _create_cell_polygon(self, cell) -> Polygon:
        """
        Create a Shapely polygon from an S2 cell.

        Parameters
        ----------
        cell : s2sphere.Cell
            S2 cell object

        Returns
        -------
        Polygon
            Shapely polygon representing the cell boundary
        """
        # Use s2sphere to get actual cell vertices
        vertices = []
        for i in range(4):
            vertex = cell.get_vertex(i)
            # vertex is already an S2Point, convert to LatLng
            lat_lng = s2sphere.LatLng.from_point(vertex)
            lat = lat_lng.lat().degrees
            lng = lat_lng.lng().degrees
            vertices.append((lng, lat))

        # Close the polygon
        vertices.append(vertices[0])
        return Polygon(vertices)

    @override
    def get_cell_from_point(self, lat: float, lon: float) -> GridCell:
        """
        Get the S2 cell containing the given point.

        Parameters
        ----------
        lat : float
            Latitude coordinate
        lon : float
            Longitude coordinate

        Returns
        -------
        GridCell
            The grid cell containing the specified point
        """
        return cell_from_core(m3s_core.s2_cell_from_point(lat, lon, self.precision))

    @override
    def get_cell_from_identifier(self, identifier: str) -> GridCell:
        """
        Get a grid cell from its S2 cell token.

        Parameters
        ----------
        identifier : str
            The S2 cell token (hexadecimal string)

        Returns
        -------
        GridCell
            The grid cell corresponding to the identifier
        """
        try:
            return cell_from_core(m3s_core.s2_cell_from_id(identifier))
        except Exception as e:
            raise ValueError(f"Invalid S2 cell token: {identifier}") from e

    @override
    def get_neighbors(self, cell: GridCell) -> list[GridCell]:
        """
        Get neighboring cells of the given cell.

        Parameters
        ----------
        cell : GridCell
            The cell for which to find neighbors

        Returns
        -------
        list[GridCell]
            List of neighboring grid cells
        """
        return [cell_from_core(n) for n in m3s_core.s2_neighbors(cell.identifier)]

    def get_children(self, cell: GridCell) -> list[GridCell]:
        """
        Get child cells at the next level.

        Parameters
        ----------
        cell : GridCell
            Parent cell

        Returns
        -------
        list[GridCell]
            List of 4 child cells
        """
        if self.precision >= self.MAX_PRECISION:
            return []  # No children at maximum level

        return [cell_from_core(c) for c in m3s_core.s2_children(cell.identifier)]

    def get_parent(self, cell: GridCell) -> GridCell | None:
        """
        Get parent cell at the previous level.

        Parameters
        ----------
        cell : GridCell
            Child cell

        Returns
        -------
        GridCell | None
            Parent cell, or None if already at level 0
        """
        if self.precision <= self.MIN_PRECISION:
            return None

        return cell_from_core(m3s_core.s2_parent(cell.identifier))

    @override
    def get_cells_in_bbox(
        self, min_lat: float, min_lon: float, max_lat: float, max_lon: float
    ) -> list[GridCell]:
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
        list[GridCell]
            List of grid cells that intersect the bounding box

        Notes
        -----
        Delegates to the shared core (``m3s_core.s2_cells_in_bbox``), which
        enumerates every level-``precision`` cell intersecting the rectangle —
        the same set ``s2sphere.RegionCoverer`` returns for a LatLngRect with
        ``min_level == max_level == precision`` (verified against s2sphere).
        """
        return [
            cell_from_core(c)
            for c in m3s_core.s2_cells_in_bbox(
                min_lat, min_lon, max_lat, max_lon, self.precision
            )
        ]

    def get_covering_cells(
        self, polygon: Polygon, max_cells: int = 100
    ) -> list[GridCell]:
        """
        Get S2 cells that cover the given polygon.

        Parameters
        ----------
        polygon : Polygon
            Shapely polygon to cover
        max_cells : int
            Maximum number of cells to return

        Returns
        -------
        list[GridCell]
            List of cells covering the polygon
        """
        if not hasattr(s2sphere, "Loop") or not hasattr(s2sphere, "Polygon"):
            return self._covering_from_bbox(polygon, max_cells)

        try:
            # Convert Shapely polygon to S2Polygon
            exterior_coords = list(polygon.exterior.coords)
            s2_points = []

            for lon, lat in exterior_coords[:-1]:  # Exclude last point (same as first)
                s2_point = s2sphere.LatLng.from_degrees(lat, lon).to_point()
                s2_points.append(s2_point)

            s2_loop = s2sphere.Loop(s2_points)
            s2_polygon = s2sphere.Polygon(s2_loop)

            # Get covering cells
            region_coverer = s2sphere.RegionCoverer()
            region_coverer.min_level = self.precision
            region_coverer.max_level = self.precision
            region_coverer.max_cells = max_cells

            covering = region_coverer.get_covering(s2_polygon)

            cells = []
            for cell_id in covering:
                cell = s2sphere.Cell(cell_id)
                cell_polygon = self._create_cell_polygon(cell)
                token = cell_id.to_token()
                cells.append(GridCell(token, cell_polygon, self.precision))

            return cells
        except Exception as e:
            warnings.warn(f"Failed to get covering cells: {e}", stacklevel=2)
            return self._covering_from_bbox(polygon, max_cells)

    def _covering_from_bbox(self, polygon: Polygon, max_cells: int) -> list[GridCell]:
        bounds = polygon.bounds
        cells = self.get_cells_in_bbox(bounds[1], bounds[0], bounds[3], bounds[2])
        if max_cells > 0 and len(cells) > max_cells:
            return cells[:max_cells]
        return cells

    def __repr__(self):
        return f"S2Grid(precision={self.precision})"
