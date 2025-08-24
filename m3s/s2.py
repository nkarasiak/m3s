"""
S2 spatial grid implementation for M3S.

S2 is Google's spherical geometry library that provides hierarchical
decomposition of the sphere into cells. Each cell is uniquely identified
by a 64-bit S2CellId, with cells organized using the Hilbert curve for
optimal spatial locality.
"""

import warnings
from typing import List, Optional

import s2sphere
from shapely.geometry import Polygon

from .base import BaseGrid, GridCell


class S2Grid(BaseGrid):
    """
    S2 spatial grid implementation.

    Based on Google's S2 geometry library, this grid provides hierarchical
    decomposition of the sphere into cells. S2 uses a cube-to-sphere projection
    and the Hilbert curve to create a spatial index with excellent locality
    properties.

    Attributes
    ----------
    level : int
        S2 cell level (0-30), where higher levels provide smaller cells
    """

    def __init__(self, level: int):
        """
        Initialize S2 grid.

        Parameters
        ----------
        level : int
            S2 cell level (0-30)
            Level 0: ~85,000 km edge length
            Level 10: ~1,300 km edge length
            Level 20: ~20 m edge length
            Level 30: ~1 cm edge length
        """
        if not 0 <= level <= 30:
            raise ValueError("S2 level must be between 0 and 30")

        super().__init__(level)
        self.level = level

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
        total_cells = 6 * (4**self.level)

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
        # Use s2sphere for accurate S2 cell computation
        lat_lng = s2sphere.LatLng.from_degrees(lat, lon)
        cell_id = s2sphere.CellId.from_lat_lng(lat_lng).parent(self.level)
        cell = s2sphere.Cell(cell_id)

        polygon = self._create_cell_polygon(cell)
        identifier = cell_id.to_token()

        return GridCell(identifier, polygon, self.level)

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
            cell_id = s2sphere.CellId.from_token(identifier)
            cell = s2sphere.Cell(cell_id)
            polygon = self._create_cell_polygon(cell)

            return GridCell(identifier, polygon, cell_id.level())
        except Exception as e:
            raise ValueError(f"Invalid S2 cell token: {identifier}") from e

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
        """
        try:
            cell_id = s2sphere.CellId.from_token(cell.identifier)

            # Get edge neighbors (4 neighbors)
            neighbors = []
            for i in range(4):
                neighbor_id = cell_id.get_edge_neighbors()[i]
                if neighbor_id is not None:
                    neighbor_cell = s2sphere.Cell(neighbor_id)
                    neighbor_polygon = self._create_cell_polygon(neighbor_cell)
                    neighbor_token = neighbor_id.to_token()
                    neighbors.append(
                        GridCell(neighbor_token, neighbor_polygon, self.level)
                    )

            # Get vertex neighbors (4 additional neighbors at corners)
            for i in range(4):
                vertex_neighbors = cell_id.get_vertex_neighbors(i)
                for vertex_neighbor_id in vertex_neighbors:
                    if (
                        vertex_neighbor_id is not None
                        and vertex_neighbor_id.level() == self.level
                    ):
                        # Avoid duplicates
                        neighbor_token = vertex_neighbor_id.to_token()
                        if not any(n.identifier == neighbor_token for n in neighbors):
                            neighbor_cell = s2sphere.Cell(vertex_neighbor_id)
                            neighbor_polygon = self._create_cell_polygon(neighbor_cell)
                            neighbors.append(
                                GridCell(neighbor_token, neighbor_polygon, self.level)
                            )

            return neighbors
        except Exception as e:
            warnings.warn(f"Failed to get neighbors: {e}", stacklevel=2)
            return []

    def get_children(self, cell: GridCell) -> List[GridCell]:
        """
        Get child cells at the next level.

        Parameters
        ----------
        cell : GridCell
            Parent cell

        Returns
        -------
        List[GridCell]
            List of 4 child cells
        """
        if self.level >= 30:
            return []  # No children at maximum level

        try:
            cell_id = s2sphere.CellId.from_token(cell.identifier)
            children = []

            for i in range(4):
                child_id = cell_id.child(i)
                child_cell = s2sphere.Cell(child_id)
                child_polygon = self._create_cell_polygon(child_cell)
                child_token = child_id.to_token()
                children.append(GridCell(child_token, child_polygon, self.level + 1))

            return children
        except Exception as e:
            warnings.warn(f"Failed to get children: {e}", stacklevel=2)
            return []

    def get_parent(self, cell: GridCell) -> Optional[GridCell]:
        """
        Get parent cell at the previous level.

        Parameters
        ----------
        cell : GridCell
            Child cell

        Returns
        -------
        GridCell or None
            Parent cell, or None if already at level 0
        """
        if self.level <= 0:
            return None

        try:
            cell_id = s2sphere.CellId.from_token(cell.identifier)
            parent_id = cell_id.parent()
            parent_cell = s2sphere.Cell(parent_id)
            parent_polygon = self._create_cell_polygon(parent_cell)
            parent_token = parent_id.to_token()

            return GridCell(parent_token, parent_polygon, self.level - 1)
        except Exception as e:
            warnings.warn(f"Failed to get parent: {e}", stacklevel=2)
            return None

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
        """
        try:
            # Create S2 region from bounding box
            rect = s2sphere.LatLngRect(
                s2sphere.LatLng.from_degrees(min_lat, min_lon),
                s2sphere.LatLng.from_degrees(max_lat, max_lon),
            )

            # Get covering cells
            region_coverer = s2sphere.RegionCoverer()
            region_coverer.min_level = self.level
            region_coverer.max_level = self.level
            region_coverer.max_cells = 1000  # Limit number of cells

            covering = region_coverer.get_covering(rect)

            cells = []
            for cell_id in covering:
                cell = s2sphere.Cell(cell_id)
                polygon = self._create_cell_polygon(cell)
                token = cell_id.to_token()
                cells.append(GridCell(token, polygon, self.level))

            return cells
        except Exception as e:
            warnings.warn(
                f"Failed to get cells in bbox using s2sphere: {e}", stacklevel=2
            )
            return []

    def get_covering_cells(
        self, polygon: Polygon, max_cells: int = 100
    ) -> List[GridCell]:
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
        List[GridCell]
            List of cells covering the polygon
        """
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
            region_coverer.min_level = self.level
            region_coverer.max_level = self.level
            region_coverer.max_cells = max_cells

            covering = region_coverer.get_covering(s2_polygon)

            cells = []
            for cell_id in covering:
                cell = s2sphere.Cell(cell_id)
                cell_polygon = self._create_cell_polygon(cell)
                token = cell_id.to_token()
                cells.append(GridCell(token, cell_polygon, self.level))

            return cells
        except Exception as e:
            warnings.warn(f"Failed to get covering cells: {e}", stacklevel=2)
            # Fallback to bounding box
            bounds = polygon.bounds
            return self.get_cells_in_bbox(bounds[1], bounds[0], bounds[3], bounds[2])

    def __repr__(self):
        return f"S2Grid(level={self.level})"
